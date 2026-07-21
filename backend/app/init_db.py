import asyncio
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

from app.database import engine, Base
# Import all models to ensure they are registered with Base
from app.models.audit_log import AuditLog
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.metadata_item import MetadataItem
from app.models.permission import Permission
from app.models.tenant import Tenant
from app.models.user import User


async def init_db():
    async with engine.begin() as conn:
        # Drop the public schema with cascade to remove all objects
        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        # Re-create the public schema
        await conn.execute(text("CREATE SCHEMA public;"))
        # Enable the vector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        # Seed default tenant and user for development endpoints
        await conn.execute(text("""
            INSERT INTO tenants (id, name, created_at)
            VALUES ('00000000-0000-0000-0000-000000000000', 'Default Tenant', NOW())
            ON CONFLICT (id) DO NOTHING;
        """))
        await conn.execute(text("""
            INSERT INTO users (id, tenant_id, email, full_name, hashed_password, role, created_at)
            VALUES ('00000000-0000-0000-0000-000000000000', '00000000-0000-0000-0000-000000000000', 'default@example.com', 'Default User', 'hashedpassword', 'user', NOW())
            ON CONFLICT (id) DO NOTHING;
        """))

if __name__ == "__main__":
    asyncio.run(init_db())