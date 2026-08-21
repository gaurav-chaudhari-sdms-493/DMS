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
        "email": {
            "enabled": settings.email_enabled,
            "address": settings.email_address,
            "smtp_host": settings.email_external_smtp_host,
            "smtp_port": settings.email_external_smtp_port,
            "note": "Send an email with a file attached to this address (any "
                    "subject/body) using an SMTP client pointed at the host/port "
                    "above — the attachment appears in your DMS Drive automatically "
                    "within about 10-15 seconds. Demo mailbox, not a real internet "
                    "email account.",
        },
        "watched_folder": {
            "note": "Only available on this server's own local disk, not from "
                    "another machine — use the SFTP connector above to share "
                    "files from a different computer.",
        },
    }
