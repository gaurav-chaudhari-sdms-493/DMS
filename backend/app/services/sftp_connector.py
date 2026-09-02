"""SFTP connector.

Polls a remote SFTP directory (recursively) for new files and ingests each
one through the shared connector entry point (connector_ingest_service.ingest_bytes),
same pattern as the watched-folder adapter — including the size+mtime
stability guard, so a file mid-transfer is never ingested truncated. A
file's subfolder path relative to the remote root is mirrored as a real,
identically-nested DMS folder (connector_ingest_service.get_or_create_folder_path),
same as the local watched-folder connector.

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

import paramiko

from ..config import settings
from ..database import AsyncSessionLocal
from .connector_ingest_service import ingest_bytes, get_connector_actor, already_ingested, get_or_create_folder_path

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 8
STABILITY_GRACE_SECONDS = 2 * POLL_INTERVAL_SECONDS
PROCESSED_SUBDIR = "processed"
FAILED_SUBDIR = "failed"

# Top-level control folders that are never treated as user subfolders to scan into.
RESERVED_DIR_NAMES = {PROCESSED_SUBDIR, FAILED_SUBDIR}

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


def _ensure_remote_path_chain(sftp, base_dir: str, segments: list[str]) -> str:
    """mkdir -p equivalent for SFTP, walking one level at a time from a known-existing base_dir."""
    current = base_dir
    for seg in segments:
        current = f"{current}/{seg}"
        _ensure_remote_dir(sftp, current)
    return current


def _walk_remote(sftp, base: str, rel_prefix: str = ""):
    """Recursively list all regular files under base/rel_prefix, skipping the
    top-level processed/ and failed/ control dirs. Yields (rel_path, SFTPAttributes)."""
    current_dir = f"{base}/{rel_prefix}" if rel_prefix else base
    for entry in sftp.listdir_attr(current_dir):
        name = entry.filename
        if not rel_prefix and name in RESERVED_DIR_NAMES:
            continue
        rel = f"{rel_prefix}/{name}" if rel_prefix else name
        if stat.S_ISDIR(entry.st_mode):
            yield from _walk_remote(sftp, base, rel)
        elif stat.S_ISREG(entry.st_mode):
            yield rel, entry


def _list_and_download_stable_blocking() -> dict[str, bytes]:
    """One connection: recursively list the remote tree, download any file whose
    size/mtime have stabilized since the last poll. Returns {relative_path: content_bytes}."""
    sftp, transport = _connect()
    try:
        base = settings.sftp_remote_dir
        _ensure_remote_dir(sftp, f"{base}/{PROCESSED_SUBDIR}")
        _ensure_remote_dir(sftp, f"{base}/{FAILED_SUBDIR}")

        entries = list(_walk_remote(sftp, base))
        seen_rel = set()
        stable: dict[str, bytes] = {}
        now = time.time()

        for rel, entry in entries:
            seen_rel.add(rel)
            size = entry.st_size
            mtime_age = now - entry.st_mtime
            last_seen = _pending_sizes.get(rel)

            if last_seen == size and mtime_age >= STABILITY_GRACE_SECONDS:
                with sftp.open(f"{base}/{rel}", "rb") as f:
                    stable[rel] = f.read()
                del _pending_sizes[rel]
            else:
                _pending_sizes[rel] = size
                logger.info(
                    "SFTP: '%s' not yet stable (%d bytes, mtime %.1fs ago), waiting",
                    rel, size, mtime_age,
                )

        for stale_rel in list(_pending_sizes):
            if stale_rel not in seen_rel:
                del _pending_sizes[stale_rel]  # file vanished before stabilizing

        return stable
    finally:
        sftp.close()
        transport.close()


def _move_remote_blocking(moves: dict[str, str]):
    """One connection for all moves this poll cycle. moves: {relative_path: destination_subdir},
    recreating the same subfolder chain under processed/ or failed/."""
    if not moves:
        return
    sftp, transport = _connect()
    try:
        base = settings.sftp_remote_dir
        for rel, subdir in moves.items():
            try:
                parts = rel.split("/")
                filename = parts[-1]
                subfolder_segments = parts[:-1]
                dest_dir = _ensure_remote_path_chain(sftp, f"{base}/{subdir}", subfolder_segments)
                sftp.rename(f"{base}/{rel}", f"{dest_dir}/{filename}")
            except Exception as e:
                logger.error("SFTP: failed to move '%s' to %s/: %s", rel, subdir, e)
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
        folder_cache: dict = {}

        for rel, content in stable_files.items():
            parts = rel.split("/")
            filename = parts[-1]
            subfolder_segments = parts[:-1]
            file_hash = hashlib.sha256(content).hexdigest()

            if await already_ingested(db, tenant_id, file_hash):
                logger.info("SFTP: '%s' already ingested (hash match), skipping", rel)
                moves[rel] = PROCESSED_SUBDIR
                continue

            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            try:
                folder_id = await get_or_create_folder_path(db, tenant_id, subfolder_segments, folder_cache) \
                    if subfolder_segments else None
                resp = await ingest_bytes(content, filename, db, content_type=content_type, folder_id=folder_id)
                logger.info("SFTP: ingested '%s' as document %s", rel, resp.document_id)
                moves[rel] = PROCESSED_SUBDIR
                ingested += 1
            except Exception as e:
                logger.error("SFTP: failed to ingest '%s': %s", rel, e)
                moves[rel] = FAILED_SUBDIR

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


class SFTPConnector:
    """T40 — Connector-protocol wrapper around this module's functions."""

    name = "sftp"

    async def poll_once(self) -> int:
        return await poll_sftp_once()

    async def run_loop(self) -> None:
        await sftp_poll_loop()
