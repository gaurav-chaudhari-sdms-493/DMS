import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Change import
    content = content.replace('import { useI18n } from "@/components/common/I18nProvider";', 'import { useI18n } from "@/lib/i18n";')
    content = content.replace('import { LanguageToggle } from "@/components/common/LanguageToggle";', 'import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";')
    content = content.replace('<LanguageToggle />', '<LanguageSwitcher />')

    # Replace t("key") with t("key", "Fallback")
    replacements = {
        't("workbench.back")': 't("workbench.back", "Back to Drive")',
        't("workbench.title")': 't("workbench.title", "Verification Workbench")',
        't("workbench.queue")': 't("workbench.queue", "Queue")',
        't("workbench.selected_fact")': 't("workbench.selected_fact", "Selected fact")',
        't("workbench.bulk_confirm")': 't("workbench.bulk_confirm", "Bulk confirm (T54)")',
        't("workbench.bulk_edit")': 't("workbench.bulk_edit", "Bulk edit (T80)")',
        't("entity.title")': 't("entity.title", "Entity 360")',
        't("entity.node_id_placeholder")': 't("entity.node_id_placeholder", "Entity node ID")',
        't("entity.load")': 't("entity.load", "Load")',
        't("entity.attributes")': 't("entity.attributes", "Attributes")',
        't("entity.records")': 't("entity.records", "Records")',
        't("entity.linked_entities")': 't("entity.linked_entities", "Linked entities")',
        't("entity.linked_facts")': 't("entity.linked_facts", "Linked facts")',
        't("entity.view_history")': 't("entity.view_history", "View history")',
    }

    for k, v in replacements.items():
        content = content.replace(k, v)

    with open(filepath, 'w') as f:
        f.write(content)

fix_file('frontend/app/workbench/page.tsx')
fix_file('frontend/app/entities/page.tsx')
