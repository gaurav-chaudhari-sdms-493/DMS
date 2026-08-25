from fastapi import APIRouter, HTTPException
from app.database import AsyncSessionLocal
from app.services.i18n_service import get_translations, SUPPORTED_LOCALES

router = APIRouter()


@router.get('/i18n/{locale}')
async def get_locale_translations(locale: str):
    """T95 — public (no auth): the login/signup/forgot-password pages
    need translations before a user is signed in."""
    if locale not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=404, detail=f"Unsupported locale: {locale}")
    async with AsyncSessionLocal() as db:
        return await get_translations(db, locale)
