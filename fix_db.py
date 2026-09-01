import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/dms"

async def fix():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        print("Downgrading tables...")
        for table in ['sys_dg_retention_classes', 'doc_dg_templates', 'doc_dg_document_versions', 'doc_dg_metadata_items']:
            try:
                await conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}"))
                await conn.execute(text(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY"))
                await conn.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
                await conn.execute(text(f"DROP INDEX IF EXISTS idx_{table}_tenant_id"))
                await conn.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS fk_{table}_tenant"))
                await conn.execute(text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS tenant_id"))
                print(f"Downgraded {table}")
            except Exception as e:
                print(f"Error on {table}: {e}")
        
        print("Updating alembic_version...")
        await conn.execute(text("UPDATE alembic_version SET version_num = '0031_template_layout_spread'"))
        
fix_coroutine = fix()
asyncio.run(fix_coroutine)
