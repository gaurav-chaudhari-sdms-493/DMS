# Scanner Integration — Scan-to-Network-Folder Setup Guide

**T44.** DMS does not speak TWAIN or WIA (the local desktop scanning protocols) directly — a web backend has no way to. The supported route is the one nearly every office scanner and MFP already has built in: **"Scan to Network Folder"** (sometimes labelled "Scan to SMB", "Scan to FTP", or "Scan to CIFS" depending on the vendor). Point that feature at a folder, and DMS's existing watched-folder connector picks up every file automatically — the same mechanism already used for a real, already-in-use local sync folder (see `watched_folder_connector.py`'s own docstring).

No TWAIN driver, no local agent, no new code path. This is documentation and a live test, not a new integration.

---

## Architecture Overview

```
[Scanner / MFP] --(SMB / FTP "Scan to Folder")--> [Network share]
                                                          |
                                             (bind-mounted into the container)
                                                          v
                                        [watched_folder_connector.py — polls every 5s]
                                                          |
                                          (connector_ingest_service.ingest_bytes)
                                                          v
                                              [Hash dedup & MinIO & DB & async ingestion]
```

A file is only ingested once it stops changing — its size must match the previous poll AND its modified-time must be quiet for at least `STABILITY_GRACE_SECONDS` (10s today). This is what makes an in-progress scan transfer safe: a half-written file is simply not picked up yet, not corrupted into a document.

---

## 1. Scanner-Side Setup

Every MFP vendor's menu wording differs slightly, but the shape is the same:

1. On the scanner's admin panel, create a new **Scan Destination** of type **Network Folder** (SMB/CIFS) or **FTP**.
2. Point it at a share this DMS deployment can mount — e.g. `\\dms-host\scans` or an FTP path.
3. If the scanner supports per-department or per-user subfolders (many do), configure those now — DMS mirrors that folder structure exactly. A scan dropped into `Registry/2026-09/` on the share becomes a real, identically-nested `Registry / 2026-09` folder in DMS, not a flattened pile of files.
4. Set the output format to PDF (or whatever this deployment's `ALLOWED_UPLOAD_EXTENSIONS` covers — see `backend/app/config.py`).

## 2. Backend Configuration

The watched sources are declared in code today (`WATCH_SOURCES` in `backend/app/services/watched_folder_connector.py`) — this is demo/single-deployment scope by design; a UI to add/remove watch paths per tenant is tracked separately as T40–T42, not part of this task.

To wire in a real scanner share, follow the same pattern the existing `stark_drive` entry already demonstrates (a real, already-in-use folder, kept separate from the connector's own bookkeeping):

```python
WatchSource(
    name="scanner",
    watch_dir=Path("/app/scanner_inbox"),
    processed_dir=Path("/app/_state/scanner/processed"),
    failed_dir=Path("/app/_state/scanner/failed"),
),
```

Then mount the real share into that path in `docker-compose.yml`, next to the backend service's existing volumes:

```yaml
volumes:
  - ./backend:/app
  - /mnt/scanner-share:/app/scanner_inbox   # the real network share, mounted read-write
```

Redeploy (`docker compose up -d --build backend worker`) and the connector starts polling it every 5 seconds — no other change needed.

## 3. End-to-End Testing

**Simulate a scan** by dropping a file into the watched directory exactly as a real scanner would:

```bash
cp sample_registry_page.pdf ./connector_inbox/watched_folder/
```

Within two poll cycles (~10-15s), the backend log shows:

```
INFO ... Watched folder [default]: ingested 'sample_registry_page.pdf' as document <uuid>
```

The file moves out of the watch directory into `processed/`, and the document appears in DMS under the connector's configured tenant.

**Test the subfolder-mirroring behaviour** the same way a departmental scan setup would exercise it:

```bash
mkdir -p ./connector_inbox/watched_folder/Registry/2026-09
cp sample_registry_page.pdf ./connector_inbox/watched_folder/Registry/2026-09/
```

Confirm a `Registry` folder containing a `2026-09` subfolder appears in DMS, with the document inside it.

**Test the duplicate-scan case** (a jam, a re-scan, a retry) by dropping the identical file a second time — it's skipped as a duplicate (matched by content hash, not filename) and still moved out of the watch directory, never left sitting there.

Automated coverage for all of this lives in `backend/tests/test_watched_folder_connector.py`.

---

## Known Limitations

- **Latency**: up to ~15 seconds between a scan landing on the share and it appearing in DMS (5s poll interval + 10s stability grace). Not real-time — acceptable for a batch scanning workflow, not for a "scan and immediately open" one.
- **Fixed watch sources**: adding a new scanner share today means a code change + redeploy, not a self-service UI action. Tracked as T40–T42, out of scope for this task.
- **No TWAIN/WIA**: a scanner that can only push directly to a desktop application (no network-folder output at all) is not supported by this route. Confirm any scanner hardware being purchased for this deployment actually offers "Scan to Network Folder" before relying on this integration.
- **Single fixed connector identity**: every file ingested through a watched source lands under one configured tenant/user (`DEFAULT_CONNECTOR_EMAIL` in `connector_ingest_service.py`), the same limitation the SFTP and email-in connectors already have. Not scanner-specific.
