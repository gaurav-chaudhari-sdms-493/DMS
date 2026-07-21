import asyncio
from app.database import engine, Base
from app.models import *  # Import all models to ensure they are registered with Base

async def init_db():
    async with engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(init_db())