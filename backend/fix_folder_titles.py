import asyncio
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal as async_session_maker
from app.models.document import Document
from app.models.folder import Folder


async def get_or_create_folder(db: AsyncSession, name: str, parent_id, tenant_id, cache: dict):
    key = (parent_id, name)
    if key in cache:
        return cache[key]

    stmt = select(Folder).where(
        Folder.tenant_id == tenant_id,
        Folder.name == name,
        Folder.parent_id == parent_id,
    )
    result = await db.execute(stmt)
    folder = result.scalar_one_or_none()
    if folder is None:
        folder = Folder(
            id=uuid.uuid4(),
            name=name,
            parent_id=parent_id,
            tenant_id=tenant_id,
        )
        db.add(folder)
        await db.flush()

    cache[key] = folder.id
    return folder.id


async def main():
    async with async_session_maker() as db:
        stmt = select(Document).where(Document.title.like("%/%"))
        result = await db.execute(stmt)
        documents = result.scalars().all()

        print(f"Found {len(documents)} documents with a slash in the title")

        cache_by_tenant = {}
        fixed = 0

        for doc in documents:
            segments = doc.title.split("/")
            filename = segments[-1].strip()
            path_segments = [s.strip() for s in segments[:-1] if s.strip()]

            if not filename:
                print(f"  SKIP {doc.id}: empty filename after split ({doc.title!r})")
                continue

            cache = cache_by_tenant.setdefault(doc.tenant_id, {})

            parent_id = None
            for seg in path_segments:
                parent_id = await get_or_create_folder(db, seg, parent_id, doc.tenant_id, cache)

            old_title = doc.title
            doc.title = filename
            doc.folder_id = parent_id
            fixed += 1
            print(f"  FIXED {doc.id}: {old_title!r} -> title={filename!r}, folder_id={parent_id}")

        await db.commit()
        print(f"\nDone. Fixed {fixed} documents.")


if __name__ == "__main__":
    asyncio.run(main())
