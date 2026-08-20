"""SFTP connector.

Polls a remote SFTP directory for new files and ingests each one through
the shared connector entry point (connector_ingest_service.ingest_bytes),
same pattern as the watched-folder adapter — including the size+mtime
stability guard, so a file mid-transfer is never ingested truncated.

paramiko is a blocking library, so every SFTP call runs inside a thread
executor rather than directly on the event loop (the BGE-M3 health-check
bug earlier in this session was exactly this mistake with a different
library — applying that lesson here up front).

Demo scope: single fixed SFTP server/credentials/remote dir, connects
fresh each poll cycle rather than holding a persistent connection.
"""
import asyncio
import hashlib
import logging
import mimetypes
import stat
import time
from typing import Optional

import paramiko

from ..config import settings
from ..database import AsyncSessionLocal
from .connector_ingest_service import ingest_bytes, get_connector_actor, already_ingested

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 8
STABILITY_GRACE_SECONDS = 2 * POLL_INTERVAL_SECONDS
PROCESSED_SUBDIR = "processed"
FAILED_SUBDIR = "failed"

_pending_sizes: dict[str, int] = {}


def _connect():
    transport = paramiko.Transport((settings.sftp_host, settings.sftp_port))
    transport.connect(username=settings.sftp_username, password=settings.sftp_password)
    return paramiko.SFTPClient.from_transport(transport), transport


def _ensure_remote_dir(sftp, path: str):
    try:
        sftp.stat(path)
    except FileNotFoundError:
        sftp.mkdir(path)


def _list_and_download_stable_blocking() -> dict[str, bytes]:
    """One connection: list the remote dir, download any file whose size/mtime
    have stabilized since the last poll. Returns {filename: content_bytes}."""
    sftp, transport = _connect()
    try:
        base = settings.sftp_remote_dir
        _ensure_remote_dir(sftp, f"{base}/{PROCESSED_SUBDIR}")
        _ensure_remote_dir(sftp, f"{base}/{FAILED_SUBDIR}")

        entries = sftp.listdir_attr(base)
        seen_names = set()
        stable: dict[str, bytes] = {}
        now = time.time()

        for entry in entries:
            if not stat.S_ISREG(entry.st_mode):
                continue
            name = entry.filename
            seen_names.add(name)
            size = entry.st_size
            mtime_age = now - entry.st_mtime
            last_seen = _pending_sizes.get(name)

            if last_seen == size and mtime_age >= STABILITY_GRACE_SECONDS:
                with sftp.open(f"{base}/{name}", "rb") as f:
                    stable[name] = f.read()
                del _pending_sizes[name]
            else:
                _pending_sizes[name] = size
                logger.info(
                    "SFTP: '%s' not yet stable (%d bytes, mtime %.1fs ago), waiting",
                    name, size, mtime_age,
                )

        for stale_name in list(_pending_sizes):
            if stale_name not in seen_names:
                del _pending_sizes[stale_name]  # file vanished before stabilizing

        return stable
    finally:
        sftp.close()
        transport.close()


def _move_remote_blocking(moves: dict[str, str]):
    """One connection for all moves this poll cycle. moves: {filename: destination_subdir}."""
    if not moves:
        return
    sftp, transport = _connect()
    try:
        base = settings.sftp_remote_dir
        for name, subdir in moves.items():
            try:
                sftp.rename(f"{base}/{name}", f"{base}/{subdir}/{name}")
            except Exception as e:
                logger.error("SFTP: failed to move '%s' to %s/: %s", name, subdir, e)
    finally:
        sftp.close()
        transport.close()


async def poll_sftp_once() -> int:
    """Poll the SFTP server once. Returns the count of files ingested."""
    if not settings.sftp_enabled:
        return 0

    loop = asyncio.get_running_loop()
    try:
        stable_files = await loop.run_in_executor(None, _list_and_download_stable_blocking)
    except Exception as e:
        logger.error("SFTP: poll cycle failed to list/download: %s", e)
        return 0

    if not stable_files:
        return 0

    ingested = 0
    moves: dict[str, str] = {}
    async with AsyncSessionLocal() as db:
        tenant_id, _ = await get_connector_actor(db)

        for filename, content in stable_files.items():
            file_hash = hashlib.sha256(content).hexdigest()

            if await already_ingested(db, tenant_id, file_hash):
                logger.info("SFTP: '%s' already ingested (hash match), skipping", filename)
                moves[filename] = PROCESSED_SUBDIR
                continue

            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            try:
                resp = await ingest_bytes(content, filename, db, content_type=content_type)
                logger.info("SFTP: ingested '%s' as document %s", filename, resp.document_id)
                moves[filename] = PROCESSED_SUBDIR
                ingested += 1
            except Exception as e:
                logger.error("SFTP: failed to ingest '%s': %s", filename, e)
                moves[filename] = FAILED_SUBDIR

    await loop.run_in_executor(None, _move_remote_blocking, moves)
    return ingested


async def sftp_poll_loop():
    if not settings.sftp_enabled:
        logger.info("SFTP connector disabled (SFTP_ENABLED=false)")
        return

    logger.info(
        "SFTP connector started, watching %s@%s:%s%s every %ds",
        settings.sftp_username, settings.sftp_host, settings.sftp_port,
        settings.sftp_remote_dir, POLL_INTERVAL_SECONDS,
    )
    while True:
        try:
            await poll_sftp_once()
        except Exception as e:
            logger.error("SFTP poll cycle failed: %s", e)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
