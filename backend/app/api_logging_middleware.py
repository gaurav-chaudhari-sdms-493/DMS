import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.database import AsyncSessionLocal
from app.models.api_log import ApiLog

logger = logging.getLogger(__name__)


class ApiLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every API request to the api_logs table."""

    # Paths to skip logging (health checks, static files, docs)
    SKIP_PREFIXES = ("/api/docs", "/api/redoc", "/openapi.json", "/_next", "/static", "/favicon")

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip non-API and docs paths
        if any(path.startswith(prefix) for prefix in self.SKIP_PREFIXES):
            return await call_next(request)

        start_time = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Extract user/tenant from Authorization header (best-effort, non-blocking)
        user_id = None
        tenant_id = None
        try:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                from app.services.auth_service import verify_token
                payload = verify_token(token)
                user_id = uuid.UUID(payload.sub)
                tenant_id = uuid.UUID(payload.tenant_id)
        except Exception:
            pass

        # Get IP address
        ip_address = None
        try:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                ip_address = forwarded.split(",")[0].strip()
            elif request.client:
                ip_address = request.client.host
        except Exception:
            pass

        user_agent = request.headers.get("user-agent", "")[:500] if request.headers.get("user-agent") else None

        # Write log entry asynchronously (fire-and-forget, don't block response)
        try:
            async with AsyncSessionLocal() as session:
                log_entry = ApiLog(
                    method=request.method,
                    path=path,
                    status_code=response.status_code,
                    response_time_ms=round(elapsed_ms, 2),
                    user_id=user_id,
                    tenant_id=tenant_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                session.add(log_entry)
                await session.commit()
        except Exception as e:
            logger.warning(f"Failed to log API call: {e}")

        return response
