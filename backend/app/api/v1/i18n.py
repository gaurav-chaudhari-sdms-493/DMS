from fastapi import APIRouter, HTTPException
from app.database import AsyncSessionLocal
from app.services.i18n_service import get_translations, SUPPORTED_LOCALES

router = APIRouter()

HARDCODED_TRANSLATIONS = {
    "en": {
        "workbench.title": "Verification Workbench",
        "workbench.back": "Back to Drive",
        "entity.title": "Entity 360",
        "entity.records": "Records",
        "entity.linked_entities": "Linked entities",
        "entity.linked_facts": "Linked facts",
        "entity.load": "Load",
        "entity.view_history": "View history",
        "workbench.queue": "Queue",
        "workbench.selected_fact": "Selected fact",
        "workbench.bulk_confirm": "Bulk confirm (T54)",
        "workbench.bulk_edit": "Bulk edit (T80)",
        "nav.logout": "Logout",
        "entity.attributes": "Attributes",
        "entity.node_id_placeholder": "Entity node ID",
    },
    "mr": {
        "workbench.title": "पडताळणी कार्यस्थळ",
        "workbench.back": "मागे जा",
        "entity.title": "एंटिटी ३६०",
        "entity.records": "नोंदी",
        "entity.linked_entities": "जोडलेल्या एंटिटी",
        "entity.linked_facts": "जोडलेले तथ्य",
        "entity.load": "लोड करा",
        "entity.view_history": "इतिहास पहा",
        "workbench.queue": "रांग",
        "workbench.selected_fact": "निवडलेले तथ्य",
        "workbench.bulk_confirm": "एकत्रित पुष्टी (T54)",
        "workbench.bulk_edit": "एकत्रित संपादन (T80)",
        "nav.logout": "लॉग आउट",
        "entity.attributes": "वैशिष्ट्ये",
        "entity.node_id_placeholder": "एंटिटी नोड आयडी",
    }
}

@router.get('/i18n/{locale}')
async def get_locale_translations(locale: str):
    if locale not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=404, detail=f"Unsupported locale: {locale}")
    
    # Get DB translations
    async with AsyncSessionLocal() as db:
        db_translations = await get_translations(db, locale)
        
    # Merge hardcoded translations with DB translations (DB takes precedence)
    final_translations = HARDCODED_TRANSLATIONS.get(locale, {}).copy()
    final_translations.update(db_translations)
    
    return final_translations
