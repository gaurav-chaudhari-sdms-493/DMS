# T44 — Scanner Connector Setup & Integration Guide (TWAIN & Network Scanners)

This guide documents the setup, architecture, and testing procedures for the **Scanner Connector (Task T44)** in the FastAPI Document Management System (DMS).

---

## 1. Architecture Overview

The Scanner Connector allows operators digitizing physical paper archives (such as Waqf registers and 7/12 land records) to scan documents directly into the DMS.

```
[Physical Scanner / WebTWAIN Agent] ──(HTTP POST + Metadata)──> [POST /api/v1/connectors/scan-inbound]
                                                                        │
[Office MFP Network Scanner] ───(SMB/FTP Folder Drop)───────> [/app/scanner_inbox]
                                                                        │
                                                                        v
                                                   [process_scanned_bytes (TIFF -> PDF/A)]
                                                                        │
                                                                        v
                                                    [connector_ingest_service.ingest_bytes]
                                                                        │
                                                                 ┌──────┴──────┐
                                                                 ▼             ▼
                                                             [MinIO S3]   [Postgres DB]
```

---

## 2. Ingestion Paths

### Path A: Direct Scan Upload API (`POST /api/v1/connectors/scan-inbound`)
Designed for desktop scanner software, WebTWAIN agents, and browser scan buttons.

- **URL**: `POST /api/v1/connectors/scan-inbound`
- **Supported Content Types**: `multipart/form-data` or `application/json` (Base64).
- **Authentication**: `X-Webhook-Secret` or `X-Scanner-Secret` header, or JWT Bearer Token.
- **Max Upload Size**: 50MB per file (`scanner_max_upload_size_mb`). Exceeding this limit returns HTTP `413 Payload Too Large`.
- **Supported Formats**: JPEG, PNG, TIFF (single and multi-page), PDF.
- **Scan Metadata**: Accepts `scanner_model`, `dpi`, `color_mode`, and `operator_notes`.

### Path B: Network Scanner Inbox Poller (`scanner_poll_loop`)
Designed for office MFP scanners (Xerox, Canon, Fujitsu) scanning to network folders via SMB/FTP.

- **Inbox Root**: `/app/scanner_inbox`
- **Poll Interval**: 15 seconds (`scanner_poll_interval_seconds`).
- **File Stability Check**: Files are ingested only after size matches across poll cycles and mtime is quiet.
- **Lifecycle & Moving Strategy**:
  - Successfully ingested files (and duplicate hash matches) are moved to:
    `/app/scanner_inbox/processed/{YYYY-MM-DD}/`
  - Ingestion errors/failures are moved to:
    `/app/scanner_inbox/failed/{YYYY-MM-DD}/`
- **Multi-Tenant Subfolder Resolution**:
  If a scanned file is dropped into `/app/scanner_inbox/{user_email}/scan.pdf`, the poller inspects the subfolder name and automatically resolves that specific user's `(tenant_id, user_id)`. Files placed directly in the inbox root fall back to `DEFAULT_CONNECTOR_EMAIL`.

---

## 3. Image Processing & PDF/A Output Specifications

> [!NOTE]
> **TIFF → PDF/A Output Specification**: Multi-page TIFF scans are automatically converted into an archivable PDF document (`_scanned.pdf`) containing full-resolution RGB/CMYK image frames. The original raw TIFF file is retained alongside in MinIO storage.

---

## 4. Configuration Reference

In `backend/.env` or `backend/app/config.py`:

```env
SCANNER_ENABLED=true
SCANNER_INBOX_DIR=/app/scanner_inbox
SCANNER_DEFAULT_DPI=300
SCANNER_POLL_INTERVAL_SECONDS=15
SCANNER_MAX_UPLOAD_SIZE_MB=50
SCANNER_WEBHOOK_SECRET=your_secure_scanner_secret
```

---

## 5. Testing & Hardware Simulation

### Option A: Hardware Simulator CLI (`send_scanner_test.py`)
Simulate a hardware scanner digitizing a physical document:

```bash
# 1. Send generated sample scan
python3 send_scanner_test.py

# 2. Send specific test document
python3 send_scanner_test.py demo_assets/Citizen_Complaint_Main_St.pdf
```

### Option B: Automated Unit & Integration Tests
Run the test suite:

```bash
python3 -m pytest backend/tests/test_scanner_connector.py
```
