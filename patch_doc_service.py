with open("backend/app/services/document_service.py", "r") as f:
    content = f.read()

import re
content = re.sub(
    r"<<<<<<< HEAD\n        quality_flag=q_flag,\n        quality_warnings=q_warnings,\n=======\n        possible_duplicate_candidates=doc\.possible_duplicate_candidates,\n>>>>>>> origin/feature-kunal-DMS",
    r"        quality_flag=q_flag,\n        quality_warnings=q_warnings,\n        possible_duplicate_candidates=doc.possible_duplicate_candidates,",
    content
)

with open("backend/app/services/document_service.py", "w") as f:
    f.write(content)
