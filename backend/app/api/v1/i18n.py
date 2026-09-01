from fastapi import APIRouter

router = APIRouter(prefix="/i18n", tags=["i18n"])

translations = {
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

@router.get("/{locale}")
async def get_i18n(locale: str):
    return translations.get(locale, translations["en"])
