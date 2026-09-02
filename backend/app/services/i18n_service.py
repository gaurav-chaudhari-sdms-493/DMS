from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict

from app.models.translation import Translation

SUPPORTED_LOCALES = ("en", "mr")


async def get_translations(db: AsyncSession, locale: str) -> Dict[str, str]:
    stmt = select(Translation.key, Translation.value).where(Translation.locale == locale)
    res = await db.execute(stmt)
    return {key: value for key, value in res.all()}
