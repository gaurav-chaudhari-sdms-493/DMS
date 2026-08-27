from fastapi import APIRouter, Depends

from app.config import settings
from app.deps import require_tenant_access
from app.schemas.auth import TokenPayload

router = APIRouter(prefix="/connectors", tags=["Connectors"])


@router.get("/info")
async def get_connector_info(current_user: TokenPayload = Depends(require_tenant_access)):
    """Connection details for the non-HTTP ingestion channels, so a user can hand
    them to another machine without needing to ask an engineer for credentials."""
    return {
        "sftp": {
            "enabled": settings.sftp_enabled,
            "host": settings.sftp_external_host,
            "port": settings.sftp_external_port,
            "username": settings.sftp_username,
            "password": settings.sftp_password,
            "remote_dir": settings.sftp_remote_dir,
            "note": "Both machines must be on the same network. Drop a file into "
                    "this folder from any SFTP client and it appears in your DMS "
                    "Drive automatically within 20-30 seconds.",
        },
        "email_webhook": {
            "enabled": settings.email_webhook_enabled,
            "endpoint": "/api/v1/connectors/email-inbound",
            "note": "Cloudflare Email Routing + Cloudflare Worker inbound email webhook. "
                    "Receives emails delivered to Cloudflare Email Routing and ingests attachments automatically.",
        },
        "email_imap_legacy": {
            "enabled": settings.email_enabled,
            "address": settings.email_address,
            "smtp_host": settings.email_external_smtp_host,
            "smtp_port": settings.email_external_smtp_port,
            "note": "Legacy IMAP polling connector (for local dev/testing with GreenMail).",
        },
        "watched_folder": {
            "note": "Only available on this server's own local disk, not from "
                    "another machine — use the SFTP connector above to share "
                    "files from a different computer.",
        },
        "scanner": {
            "enabled": settings.scanner_enabled,
            "inbound_endpoint": "/api/v1/connectors/scan-inbound",
            "status_endpoint": "/api/v1/connectors/scanner/status",
            "inbox_dir": settings.scanner_inbox_dir,
            "default_dpi": settings.scanner_default_dpi,
            "max_upload_size_mb": settings.scanner_max_upload_size_mb,
            "poll_interval_seconds": settings.scanner_poll_interval_seconds,
            "note": "TWAIN & Network-Scan integration (T44). Accepts direct scan uploads via "
                    "POST /api/v1/connectors/scan-inbound (with DPI, color mode, device metadata) "
                    "and polls network office scanners (MFPs) scanning to /app/scanner_inbox. "
                    "Auto-maps scans into 'Scanned Documents' folder and converts multi-page TIFFs to PDF/A.",
        },
    }
