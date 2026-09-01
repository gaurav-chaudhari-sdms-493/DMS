with open("frontend/app/workbench/page.tsx", "r") as f:
    content = f.read()

import re
content = re.sub(
    r"<<<<<<< HEAD\nimport RegionViewer from \"@/components/common/RegionViewer\";\nimport \{ useI18n \} from \"@/lib/i18n\";\nimport \{ LanguageSwitcher \} from \"@/components/common/LanguageSwitcher\";\n=======\nimport RegionHighlightViewer from \"@/components/drive/RegionHighlightViewer\";\nimport type \{ FolderTreeNode \} from \"@/types\";\n\nfunction flattenFolders\(nodes: FolderTreeNode\[\], depth = 0\): \{ id: string; name: string; depth: number \}\[\] \{\n  const out: \{ id: string; name: string; depth: number \}\[\] = \[\];\n  for \(const n of nodes\) \{\n    out\.push\(\{ id: n\.id, name: n\.name, depth \}\);\n    const kids = n\.subfolders \|\| n\.children \|\| \[\];\n    if \(kids\.length\) out\.push\(\.\.\.flattenFolders\(kids, depth \+ 1\)\);\n  \}\n  return out;\n\}\n>>>>>>> origin/feature-kunal-DMS",
    r"""import RegionViewer from "@/components/common/RegionViewer";
import { useI18n } from "@/lib/i18n";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import type { FolderTreeNode } from "@/types";

function flattenFolders(nodes: FolderTreeNode[], depth = 0): { id: string; name: string; depth: number }[] {
  const out: { id: string; name: string; depth: number }[] = [];
  for (const n of nodes) {
    out.push({ id: n.id, name: n.name, depth });
    const kids = n.subfolders || n.children || [];
    if (kids.length) out.push(...flattenFolders(kids, depth + 1));
  }
  return out;
}""",
    content,
    flags=re.DOTALL
)

with open("frontend/app/workbench/page.tsx", "w") as f:
    f.write(content)
