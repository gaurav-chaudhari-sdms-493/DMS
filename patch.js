const fs = require('fs');
let content = fs.readFileSync('frontend/app/entities/page.tsx', 'utf8');

// 1. Add imports
content = content.replace(
  'import RegionViewer from "@/components/common/RegionViewer";',
  'import RegionViewer from "@/components/common/RegionViewer";\nimport { useI18n } from "@/components/common/I18nProvider";\nimport { LanguageToggle } from "@/components/common/LanguageToggle";'
);

// 2. Add useI18n
content = content.replace(
  'export default function Entity360Page() {\n  const [nodeId, setNodeId] = useState("");',
  'export default function Entity360Page() {\n  const { t } = useI18n();\n  const [nodeId, setNodeId] = useState("");'
);

// 3. Header toggle and strings
content = content.replace(
  '<span>Back to Drive</span>',
  '<span>{t("workbench.back")}</span>'
);
content = content.replace(
  '<Network className="w-5 h-5 text-[#0b57d0]" />\n            Entity 360\n          </h1>\n        </div>\n      </header>',
  '<Network className="w-5 h-5 text-[#0b57d0]" />\n            {t("entity.title")}\n          </h1>\n        </div>\n        <div className="flex items-center gap-4 text-xs text-[#747775]">\n          <LanguageToggle />\n        </div>\n      </header>'
);

// 4. Other translations
content = content.replace('placeholder="Entity node ID"', 'placeholder={t("entity.node_id_placeholder")}');
content = content.replace('>Load</Button>', '>{t("entity.load")}</Button>');
content = content.replace('<h3 className="text-xs font-bold text-[#747775] uppercase tracking-wider mb-3">Attributes</h3>', '<h3 className="text-xs font-bold text-[#747775] uppercase tracking-wider mb-3">{t("entity.attributes")}</h3>');
content = content.replace('<h3 className="text-sm font-bold mb-4">Records ({data.records.length})</h3>', '<h3 className="text-sm font-bold mb-4">{t("entity.records")} ({data.records.length})</h3>');
content = content.replace('<h3 className="text-sm font-bold mb-4">Linked entities ({data.linked_entities.length})</h3>', '<h3 className="text-sm font-bold mb-4">{t("entity.linked_entities")} ({data.linked_entities.length})</h3>');
content = content.replace('<h3 className="text-sm font-bold mb-4">Linked facts ({data.linked_facts.length})</h3>', '<h3 className="text-sm font-bold mb-4">{t("entity.linked_facts")} ({data.linked_facts.length})</h3>');
content = content.replace('> View history', '> {t("entity.view_history")}');

fs.writeFileSync('frontend/app/entities/page.tsx', content);
