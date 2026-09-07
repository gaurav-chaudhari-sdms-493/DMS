"""T95 — Comprehensive Marathi UI Translations Coverage

Backlog: "Localisation — EN + MR, translations table, Noto Sans
Devanagari, Marathi digit conversion, language switcher."

Expands sys_dg_translations with full coverage across Workbench,
Drive sidebar/header, Entity 360, Completeness dashboard,
document preview / extracted facts, and common action dialogs.

Revision ID: 0048_marathi_translations
Revises: 0047_metadata_item_regions
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0048_marathi_translations'
down_revision: Union[str, None] = '0047_metadata_item_regions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# key -> (english, marathi)
ADDITIONAL_TRANSLATIONS = {
    # Drive Sidebar & Views
    'drive.nav.home': ('Home', 'मुख्यपृष्ठ'),
    'drive.nav.chat': ('AI Chat', 'AI चॅट'),
    'drive.nav.my_drive': ('My Drive', 'माझे ड्राइव्ह'),
    'drive.nav.starred': ('Starred', 'तारांकित'),
    'drive.nav.trash': ('Bin', 'कचरा पेटी (Bin)'),
    'drive.nav.new': ('New', 'नवीन'),
    'drive.nav.new_folder': ('New folder', 'नवीन फोल्डर'),
    'drive.nav.file_upload': ('File upload', 'फाइल अपलोड'),
    'drive.nav.connect_device': ('Connect a device', 'डिव्हाइस कनेक्ट करा'),
    'drive.storage.title': ('Storage', 'स्टोरेज'),
    'drive.storage.used': ('used', 'वापरले'),
    'drive.search.placeholder_ai': ('Ask AI anything about your DMS documents...', 'तुमच्या DMS दस्तऐवजांबद्दल AI ला काहीही विचारा...'),
    'drive.search.placeholder_standard': ('Search in DMS...', 'DMS मध्ये शोधा...'),
    'drive.search.ai_toggle': ('AI', 'AI'),
    'drive.view.switch_to_list': ('Switch to List view', 'यादी दृश्यावर स्विच करा'),
    'drive.view.switch_to_grid': ('Switch to Grid view', 'ग्रीड दृश्यावर स्विच करा'),

    # Workbench
    'workbench.title': ('Verification Workbench', 'पडताळणी कार्यक्षेत्र'),
    'workbench.tab.needs_review': ('Needs Review', 'पुनरावलोकन आवश्यक'),
    'workbench.tab.needs_review_desc': ('Every field waiting on a human decision, sorted worst-confidence first — not only low-scoring ones.', 'प्रत्येक फील्ड जे मानवी निर्णयाची वाट पाहत आहे, सर्वात कमी विश्वासापासून क्रमवारी लावली आहे.'),
    'workbench.tab.handwritten': ('Handwritten', 'हस्तलिखित'),
    'workbench.tab.handwritten_desc': ('Fields the system read from handwriting rather than print. Excludes margin notes — see "Marginalia".', 'सिस्टमने मुद्रित मजकुराऐवजी हस्तलिखितातून वाचलेले फील्ड्स.'),
    'workbench.tab.marginalia': ('Marginalia', 'मार्जिन नोट्स (टीपा)'),
    'workbench.tab.marginalia_desc': ('Handwritten notes found outside any known field on the page (margin notes, stamps, annotations).', 'पृष्ठावरील कोणत्याही ज्ञात फील्डबाहेर आढळलेल्या हस्तलिखित नोंदी (मार्जिन नोट्स, शिक्के, टिप्पण्या).'),
    'workbench.tab.join_mismatches': ('Join Mismatches', 'जोड विसंगती'),
    'workbench.tab.join_mismatches_desc': ("A two-page entry the system couldn't reliably match left-to-right — needs a human to pair the halves.", 'दोन पृष्ठांची नोंद जी डावीकडून उजवीकडे जुळवता आली नाही — मानवी पडताळणी आवश्यक.'),
    'workbench.tab.continuation_unclear': ('Continuation Unclear', 'सातत्य अस्पष्ट'),
    'workbench.tab.continuation_unclear_desc': ("A page pair the system couldn't confidently classify as the same table continuing, a side-by-side spread, or unrelated. Your answer here applies automatically to every future document with this same page shape.", 'पृष्ठ जोडी ज्याचे वर्गीकरण अस्पष्ट आहे — तेच सारणी सुरू आहे, दोन-पृष्ठ स्प्रेड आहे किंवा असंबंधित आहे.'),
    'workbench.sentinel.marginalia': ('Handwritten margin note', 'हस्तलिखित मार्जिन टीप'),
    'workbench.sentinel.join_mismatch': ("Table join couldn't be matched", 'सारणी जोड जुळवता आला नाही'),
    'workbench.sentinel.stitch_ambiguous': ('Table continuation unclear', 'सारणी सातत्य अस्पष्ट'),
    'workbench.btn.claim': ('Claim', 'स्वीकारा (Claim)'),
    'workbench.btn.release': ('Release', 'मुक्त करा (Release)'),
    'workbench.btn.confirm': ('Confirm (Verified)', 'पुष्टी करा (प्रमाणित)'),
    'workbench.btn.edit_save': ('Edit & Save', 'संपादित करा आणि जतन करा'),
    'workbench.btn.dismiss': ('Dismiss', 'नाकारा (Dismiss)'),
    'workbench.btn.revert': ('Revert to Machine', 'मूळ स्थितीत आणा'),
    'workbench.btn.view_source': ('View Source Region', 'मूळ स्रोत क्षेत्र पाहा'),
    'workbench.btn.batch_confirm': ('Batch Confirm Claimed', 'स्वीकारलेल्यांची एकत्रित पुष्टी करा'),
    'workbench.btn.claim_next': ('Claim Next 10', 'पुढील १० स्वीकारा'),
    'workbench.btn.refresh': ('Refresh Queue', 'रांग रीफ्रेश करा'),
    'workbench.label.filter_folder': ('Filter by folder:', 'फोल्डरनुसार फिल्टर करा:'),
    'workbench.label.all_folders': ('All Folders', 'सर्व फोल्डर्स'),
    'workbench.label.sort_by': ('Sort by:', 'यानुसार क्रमवारी लावा:'),
    'workbench.sort.lowest_confidence': ('Lowest Confidence', 'सर्वात कमी विश्वास'),
    'workbench.sort.highest_confidence': ('Highest Confidence', 'सर्वात जास्त विश्वास'),
    'workbench.sort.newest': ('Newest First', 'नवीनतम प्रथम'),
    'workbench.sort.oldest': ('Oldest First', 'जुने प्रथम'),
    'workbench.label.field': ('Field', 'फील्ड'),
    'workbench.label.extracted_value': ('Extracted Value', 'काढलेले मूल्य'),
    'workbench.label.confidence': ('Confidence', 'विश्वासार्हता'),
    'workbench.label.document': ('Document', 'दस्तऐवज'),
    'workbench.label.status': ('Status', 'स्थिती'),
    'workbench.label.actions': ('Actions', 'क्रिया'),
    'workbench.label.keyboard_shortcuts': ('Keyboard Shortcuts', 'कीबोर्ड शॉर्टकट'),
    'workbench.empty_queue': ('No items in this queue', 'या रांगेत कोणतीही बाब नाही'),
    'workbench.queue_all_caught_up': ('All caught up! There are no pending items in this category.', 'सर्व काम पूर्ण झाले! या श्रेणीत प्रलंबित नोंदी नाहीत.'),
    'workbench.deskew.deskewed': ('Straightened (Deskewed)', 'सरळ केलेले (Deskewed)'),
    'workbench.deskew.original': ('Original Scan', 'मूळ स्कॅन'),
    'workbench.deskew.skew_badge': ('Skew', 'तिरपेपणा'),

    # Entity 360
    'entities.title': ('Entity 360', 'एंटिटी ३६०'),
    'entities.search_placeholder': ('Search entity by name or ID...', 'नावाने किंवा आयडीने एंटिटी शोधा...'),
    'entities.overview': ('Entity Overview', 'एंटिटी आढावा'),
    'entities.records': ('Associated Records', 'संबंधित रेकॉर्ड्स'),
    'entities.linked_entities': ('Linked Entities', 'जोडलेल्या एंटिटीज'),
    'entities.linked_facts': ('Linked Facts', 'जोडलेले तथ्य (Facts)'),
    'entities.amendment_history': ('Amendment History', 'दुरुस्ती इतिहास'),
    'entities.status.auto_linked': ('Auto-linked', 'स्वयं-जोडलेले'),
    'entities.status.needs_confirmation': ('Needs confirmation', 'पुष्टीकरण आवश्यक'),
    'entities.status.verified': ('Verified', 'प्रमाणित'),
    'entities.status.reverted': ('Reverted', 'पूर्ववत केलेले'),
    'entities.btn.confirm_edge': ('Confirm Link', 'जोडणीची पुष्टी करा'),
    'entities.btn.revert_edge': ('Revert Link', 'जोडणी पूर्ववत करा'),
    'entities.no_entities_found': ('No entities found', 'कोणतीही एंटिटी आढळली नाही'),
    'entities.select_entity_prompt': ('Select an entity to view relationships and records', 'संबंध आणि रेकॉर्ड पाहण्यासाठी एंटिटी निवडा'),

    # Completeness Dashboard
    'completeness.title': ('Completeness Dashboard', 'पूर्णता डॅशबोर्ड'),
    'completeness.corpus_folder': ('Corpus Folder', 'कॉर्पस फोल्डर'),
    'completeness.load_dashboard': ('Load Dashboard', 'डॅशबोर्ड लोड करा'),
    'completeness.select_folder': ('Select Folder', 'फोल्डर निवडा'),
    'completeness.metrics.total_docs': ('Total Documents', 'एकूण दस्तऐवज'),
    'completeness.metrics.total_pages': ('Total Pages', 'एकूण पृष्ठे'),
    'completeness.metrics.failed_pages': ('Failed Pages', 'अयशस्वी पृष्ठे'),
    'completeness.metrics.ocr_data_loss': ('OCR Data Loss', 'OCR डेटा हानी'),
    'completeness.metrics.verified_facts': ('Verified Facts', 'प्रमाणित तथ्य'),
    'completeness.metrics.unverified_facts': ('Unverified Facts', 'अप्रमाणित तथ्य'),
    'completeness.metrics.missing_fields': ('Missing Required Fields', 'आवश्यक फील्ड गहाळ'),
    'completeness.drilldown.title': ('Drilldown Details', 'सखोल तपशील'),
    'completeness.drilldown.no_issues': ('No issues found in this category', 'या श्रेणीत कोणतीही समस्या आढळली नाही'),

    # Document Preview & Facts
    'preview.extracted_facts': ('Extracted Facts', 'काढलेले तथ्य (Extracted Facts)'),
    'preview.table_view': ('Table View', 'सारणी दृश्य'),
    'preview.list_view': ('List View', 'यादी दृश्य'),
    'preview.ask_ai': ('Ask AI', 'AI ला विचारा'),
    'preview.confidence': ('Confidence', 'विश्वासार्हता'),
    'preview.page': ('Page', 'पृष्ठ'),
    'preview.verified': ('Verified', 'प्रमाणित'),
    'preview.unverified': ('Unverified', 'अप्रमाणित'),
    'preview.save_edit': ('Save Edit', 'बदल जतन करा'),
    'preview.cancel_edit': ('Cancel', 'रद्द करा'),
    'preview.stitch_notice': ('Cross-page stitch resolved', 'पृष्ठ-सातत्य जोडले गेले'),

    # Common
    'common.ok': ('OK', 'ठीक आहे'),
    'common.yes': ('Yes', 'होय'),
    'common.no': ('No', 'नाही'),
    'common.error': ('Error', 'त्रुटी'),
    'common.success': ('Success', 'यशस्वी'),
    'common.warning': ('Warning', 'चेतावणी'),
    'common.actions': ('Actions', 'क्रिया'),
    'common.status': ('Status', 'स्थिती'),
    'common.filter': ('Filter', 'फिल्टर'),
    'common.sort': ('Sort', 'क्रमवारी'),
    'common.refresh': ('Refresh', 'रीफ्रेश करा'),
    'common.apply': ('Apply', 'लागू करा'),
    'common.reset': ('Reset', 'रीसेट करा'),
    'common.clear': ('Clear', 'साफ करा'),
    'common.offline_notice': ('You are currently offline. Changes will sync when reconnected.', 'तुम्ही सध्या ऑफलाइन आहात. पुन्हा कनेक्ट झाल्यावर बदल सिंक होतील.'),
}


def upgrade() -> None:
    table = sa.table(
        'sys_dg_translations',
        sa.column('locale', sa.String()),
        sa.column('key', sa.String()),
        sa.column('value', sa.Text()),
    )
    rows = []
    for key, (en, mr) in ADDITIONAL_TRANSLATIONS.items():
        rows.append({'locale': 'en', 'key': key, 'value': en})
        rows.append({'locale': 'mr', 'key': key, 'value': mr})
    
    bind = op.get_bind()
    for row in rows:
        bind.execute(
            sa.text(
                "INSERT INTO sys_dg_translations (locale, key, value) "
                "VALUES (:locale, :key, :value) "
                "ON CONFLICT (locale, key) DO UPDATE SET value = EXCLUDED.value"
            ),
            row,
        )


def downgrade() -> None:
    bind = op.get_bind()
    for key in ADDITIONAL_TRANSLATIONS.keys():
        bind.execute(
            sa.text("DELETE FROM sys_dg_translations WHERE key = :key"),
            {"key": key},
        )
