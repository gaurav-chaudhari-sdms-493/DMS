with open("backend/app/schemas/document.py", "r") as f:
    content = f.read()

import re
content = re.sub(
    r"<<<<<<< HEAD\n    quality_flag: Optional\[str\] = None\n    quality_warnings: List\[str\] = Field\(default_factory=list\)\n=======\n    possible_duplicate_candidates: Optional\[List\[Dict\[str, Any\]\]\] = None\n>>>>>>> origin/feature-kunal-DMS",
    r"    quality_flag: Optional[str] = None\n    quality_warnings: List[str] = Field(default_factory=list)\n    possible_duplicate_candidates: Optional[List[Dict[str, Any]]] = None",
    content
)

with open("backend/app/schemas/document.py", "w") as f:
    f.write(content)
