from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from typing import Optional, Any
from app.models.audit_log import AuditLog

async def log_action(
    db: AsyncSession,
    actor_id: Optional[uuid.UUID],
    tenant_id: uuid.UUID,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[uuid.UUID] = None,
    ip_address: Optional[str] = None,
    details: Optional[Any] = None
) -> AuditLog:
    log = AuditLog(
        actor_tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        details=details
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log
