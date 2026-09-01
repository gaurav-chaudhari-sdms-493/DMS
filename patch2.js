const fs = require('fs');
let content = fs.readFileSync('frontend/app/entities/page.tsx', 'utf8');

content = content.replace(
  'import RegionHighlightViewer from "@/components/drive/RegionHighlightViewer";',
  'import RegionViewer from "@/components/common/RegionViewer";\nimport { useI18n } from "@/components/common/I18nProvider";\nimport { LanguageToggle } from "@/components/common/LanguageToggle";'
);

content = content.replace(
  '<RegionHighlightViewer factId={viewingFactId} />',
  '<RegionViewer factId={viewingFactId} />'
);

fs.writeFileSync('frontend/app/entities/page.tsx', content);
