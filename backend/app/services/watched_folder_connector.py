"""Watched folder connector.

Polls a local directory for new files and ingests each one through the
shared connector entry point (connector_ingest_service.ingest_bytes),
same as the FTP/SFTP and email-in adapters will. Handled files are moved
into a `processed/` subfolder so a re-poll never reprocesses them, with a
file-hash check against document_versions as a second, DB-backed guard.

Demo scope: single fixed watch directory, fixed poll interval, runs as a
background task in the backend process. Production scope (per-tenant
watch paths, configurable connectors, retry/alerting) is backlog T40-T42.
"""
import asyncio
import hashlib
import logging
import mimetypes
import time
from pathlib import Path

from ..database import AsyncSessionLocal
from .connector_ingest_service import ingest_bytes, get_connector_actor, already_ingested

logger = logging.getLogger(__name__)

WATCH_DIR = Path("/app/watched_inbox")
PROCESSED_DIR = WATCH_DIR / "processed"
FAILED_DIR = WATCH_DIR / "failed"
POLL_INTERVAL_SECONDS = 5

# A file is only ingested once its size matches what we saw on the previous
# poll AND its mtime hasn't been touched for at least STABILITY_GRACE_SECONDS.
# Size-match alone isn't enough: a writer that pauses mid-write (slow copy,
# network transfer) can look "unchanged" across two poll boundaries that both
# land inside the pause, well before the write actually finishes. Requiring
# a longer mtime-quiet period closes that gap. Module-level so state persists
# across poll cycles.
STABILITY_GRACE_SECONDS = 2 * POLL_INTERVAL_SECONDS
_pending_sizes: dict[str, int] = {}


async def poll_watched_folder_once() -> int:
    """Scan the watch directory once. Returns the count of files ingested."""
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FAILED_DIR.mkdir(parents=True, exist_ok=True)

    candidates = [p for p in WATCH_DIR.iterdir() if p.is_file()]
    if not candidates:
        return 0

    seen_names = {p.name for p in candidates}
    for stale_name in list(_pending_sizes):
        if stale_name not in seen_names:
            del _pending_sizes[stale_name]  # file vanished before stabilizing; drop tracking

    stable_paths = []
    for path in candidates:
        stat = path.stat()
        size = stat.st_size
        mtime_age = time.time() - stat.st_mtime
        last_seen = _pending_sizes.get(path.name)

        if last_seen == size and mtime_age >= STABILITY_GRACE_SECONDS:
            stable_paths.append(path)
            del _pending_sizes[path.name]
        else:
            _pending_sizes[path.name] = size
            logger.info(
                "Watched folder: '%s' not yet stable (%d bytes, mtime %.1fs ago), waiting",
                path.name, size, mtime_age,
            )

    if not stable_paths:
        return 0

    ingested = 0
    async with AsyncSessionLocal() as db:
        tenant_id, _ = await get_connector_actor(db)

        for path in stable_paths:
            content = path.read_bytes()
            file_hash = hashlib.sha256(content).hexdigest()

            if await already_ingested(db, tenant_id, file_hash):
                logger.info("Watched folder: '%s' already ingested (hash match), skipping", path.name)
                path.rename(PROCESSED_DIR / path.name)
                continue

            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            try:
                resp = await ingest_bytes(content, path.name, db, content_type=content_type)
                logger.info("Watched folder: ingested '%s' as document %s", path.name, resp.document_id)
                path.rename(PROCESSED_DIR / path.name)
                ingested += 1
            except Exception as e:
                logger.error("Watched folder: failed to ingest '%s': %s", path.name, e)
                path.rename(FAILED_DIR / path.name)

    return ingested


async def watch_folder_loop():
    logger.info("Watched folder connector started, watching %s every %ds", WATCH_DIR, POLL_INTERVAL_SECONDS)
    while True:
        try:
            await poll_watched_folder_once()
        except Exception as e:
            logger.error("Watched folder poll cycle failed: %s", e)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
