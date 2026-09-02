"""T95 — i18n: sys_dg_translations table, users.locale

Backlog: "Localisation — EN + MR, translations table, Noto Sans
Devanagari, Marathi digit conversion, language switcher."

sys_dg_translations is a DB-backed catalog (key, locale) -> value, served
to the frontend via GET /api/v1/i18n/{locale} rather than bundled as
static JSON, so a translation can be corrected without a redeploy.

Seed scope is deliberately bounded, not the whole app: auth pages (login/
signup/forgot-password), the global drive header, and common action
words shared across many screens — the surfaces someone can reach before
and immediately after signing in. The other ~900+ hardcoded English
strings elsewhere in the frontend are unchanged; frontend/lib/i18n.tsx's
t() falls back to the English text passed inline wherever no translation
key was wired up, so nothing renders blank or a raw key.

Marathi text below was drafted, not reviewed by a native speaker or a
government Marathi-language authority — flag for review before this
reaches real users, same caveat as T30's marginalia convention and T26's
spread-join field mapping.

Revision ID: 0032_i18n_translations
Revises: 0031_template_layout_spread
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0032_i18n_translations'
down_revision: Union[str, None] = '0031_template_layout_spread'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# key -> (english, marathi)
SEED_TRANSLATIONS = {
    'auth.login.title': ('Sign in', 'साइन इन करा'),
    'auth.login.email_label': ('Email', 'ईमेल'),
    'auth.login.password_label': ('Password', 'पासवर्ड'),
    'auth.login.submit': ('Sign in', 'साइन इन करा'),
    'auth.login.forgot_password': ('Forgot password?', 'पासवर्ड विसरलात?'),
    'auth.login.no_account': ("Don't have an account?", 'खाते नाही?'),
    'auth.login.signup_link': ('Sign up', 'साइन अप करा'),

    'auth.signup.title': ('Create your account', 'तुमचे खाते तयार करा'),
    'auth.signup.full_name_label': ('Full name', 'पूर्ण नाव'),
    'auth.signup.email_label': ('Email', 'ईमेल'),
    'auth.signup.password_label': ('Password', 'पासवर्ड'),
    'auth.signup.submit': ('Create Account', 'खाते तयार करा'),
    'auth.signup.have_account': ('Already have an account?', 'आधीच खाते आहे?'),
    'auth.signup.login_link': ('Sign in', 'साइन इन करा'),

    'auth.forgot.title': ('Reset your password', 'तुमचा पासवर्ड रीसेट करा'),
    'auth.forgot.email_label': ('Email', 'ईमेल'),
    'auth.forgot.submit': ('Send reset link', 'रीसेट लिंक पाठवा'),
    'auth.forgot.back_to_login': ('Back to sign in', 'साइन इनवर परत जा'),

    'header.search_placeholder': ('Search anything with Stark AI...', 'स्टार्क AI सह काहीही शोधा...'),
    'header.account_menu': ('Account', 'खाते'),
    'header.profile_analytics': ('Profile & Analytics', 'प्रोफाइल आणि विश्लेषण'),
    'header.verification_workbench': ('Verification Workbench', 'पडताळणी कार्यक्षेत्र'),
    'header.completeness_dashboard': ('Completeness Dashboard', 'पूर्णता डॅशबोर्ड'),
    'header.entity_360': ('Entity 360', 'एंटिटी 360'),
    'header.logout': ('Log Out', 'लॉग आउट करा'),
    'header.search_settings': ('Search Settings', 'शोध सेटिंग्ज'),
    'header.reranker_strategy': ('Reranker strategy', 'रीरँकर रणनीती'),
    'header.ai_summary': ('AI Summary generation', 'AI सारांश निर्मिती'),
    'header.language': ('Language', 'भाषा'),

    'common.new_folder': ('New folder', 'नवीन फोल्डर'),
    'common.upload': ('Upload', 'अपलोड करा'),
    'common.save': ('Save', 'जतन करा'),
    'common.cancel': ('Cancel', 'रद्द करा'),
    'common.delete': ('Delete', 'हटवा'),
    'common.confirm': ('Confirm', 'पुष्टी करा'),
    'common.loading': ('Loading...', 'लोड होत आहे...'),
    'common.search': ('Search', 'शोधा'),
    'common.close': ('Close', 'बंद करा'),
    'common.create': ('Create', 'तयार करा'),
    'common.rename': ('Rename', 'पुनर्नामित करा'),
    'common.move': ('Move', 'हलवा'),
    'common.download': ('Download', 'डाउनलोड करा'),
    'common.share': ('Share', 'शेअर करा'),
    'common.no_results': ('No results found', 'कोणतेही निकाल आढळले नाहीत'),
    'common.back': ('Back', 'मागे'),
    'common.next': ('Next', 'पुढे'),
    'common.edit': ('Edit', 'संपादित करा'),
    'common.view': ('View', 'पाहा'),
}


def upgrade() -> None:
    op.add_column(
        'iam_dg_users',
        sa.Column('locale', sa.String(), nullable=False, server_default='en'),
    )
    op.create_check_constraint(
        'ck_iam_dg_users_locale',
        'iam_dg_users',
        "locale IN ('en', 'mr')",
    )

    op.create_table(
        'sys_dg_translations',
        sa.Column('locale', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('locale', 'key', name='pk_sys_dg_translations'),
    )

    table = sa.table(
        'sys_dg_translations',
        sa.column('locale', sa.String()),
        sa.column('key', sa.String()),
        sa.column('value', sa.Text()),
    )
    rows = []
    for key, (en, mr) in SEED_TRANSLATIONS.items():
        rows.append({'locale': 'en', 'key': key, 'value': en})
        rows.append({'locale': 'mr', 'key': key, 'value': mr})
    op.bulk_insert(table, rows)


def downgrade() -> None:
    op.drop_table('sys_dg_translations')
    op.drop_constraint('ck_iam_dg_users_locale', 'iam_dg_users', type_='check')
    op.drop_column('iam_dg_users', 'locale')
