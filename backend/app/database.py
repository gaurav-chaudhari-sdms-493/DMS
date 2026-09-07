import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.postgres_url,
    echo=settings.app_env == 'development',
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# D-2 security review, 2026-09-07 — `engine`/`AsyncSessionLocal` above
# connect as `docsearch`, a genuine Postgres superuser (POSTGRES_USER in
# docker-compose.yml), and superusers unconditionally bypass Row-Level
# Security regardless of how carefully a policy is written — confirmed
# live: `FORCE ROW LEVEL SECURITY` on 17 tenant-scoped tables was doing
# nothing (D2_tenant_isolation_security_review.md, Finding 1).
#
# `app_engine`/`AppSessionLocal` is a SEPARATE connection pool authenticating
# as the restricted `dms_app` role instead (NOSUPERUSER NOBYPASSRLS,
# created by migration 0046) — this is what get_db/get_tenant_db below
# actually use, so every real FastAPI request goes through a connection RLS
# can actually enforce, not one that ignores it. Deliberately NOT used for
# the test suite, Alembic migrations, or worker.py's background tasks
# (ingestion pipeline, the cross-tenant trash-retention sweep, the
# folder/SFTP/email connectors) — those already have a different, audited
# trust boundary (see the review doc) and some of them (the retention
# sweep) legitimately need the broader access a single HTTP request never
# should have.
if settings.app_postgres_url:
    app_engine = create_async_engine(
        settings.app_postgres_url,
        echo=settings.app_env == 'development',
        pool_size=10,
        max_overflow=20,
    )
else:
    logger.warning(
        "APP_POSTGRES_URL is not set -- FastAPI requests are falling back to the "
        "same superuser connection as everything else, so Row-Level Security "
        "provides no real protection (see D2_tenant_isolation_security_review.md). "
        "Set APP_POSTGRES_URL to the restricted `dms_app` role from migration 0046 "
        "to close this gap."
    )
    app_engine = engine

AppSessionLocal = async_sessionmaker(
    app_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass

async def _reset_session_tenant_context(session: AsyncSession) -> None:
    """D-2 fix — the session-scoped `set_config(..., false)` used below (see
    get_tenant_db, establish_tenant_context, lookup_user_by_email) survives
    an in-request `db.commit()`, which real service code does mid-function
    more than once (upload_document, sign_up — found live: both broke
    under `is_local=true`, the transaction-scoped alternative, the instant
    something after their own commit needed the context again). The
    tradeoff is this MUST be reset before the underlying connection goes
    back to the pool, or one request's tenant leaks into the next unrelated
    one that happens to reuse it -- every get_db()/get_tenant_db() exit
    path calls this, regardless of whether this particular request ever
    set anything, so cleanup is centralized instead of dependent on every
    caller remembering to."""
    try:
        await session.execute(text(
            "SELECT set_config('app.current_tenant_id', '', false), "
            "set_config('app.login_lookup_email', '', false)"
        ))
        await session.commit()
    except Exception:
        # Best-effort: a connection that can't even run a RESET is broken
        # and won't be reused by the pool anyway, so there's no leak risk.
        pass

async def get_db():
    async with AppSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await _reset_session_tenant_context(session)
            await session.close()

async def get_db_with_tenant(tenant_id: str | None = None):
    async with AppSessionLocal() as session:
        try:
            if tenant_id:
                await session.execute(
                    text("SELECT set_config('app.current_tenant_id', :t, false)"),
                    {"t": str(tenant_id)}
                )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await _reset_session_tenant_context(session)
            await session.close()
