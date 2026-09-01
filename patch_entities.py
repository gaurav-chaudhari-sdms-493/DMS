with open("frontend/app/entities/page.tsx", "r") as f:
    content = f.read()

import re
content = re.sub(
    r"<<<<<<< HEAD\n.*?=======\n(.*?)\n>>>>>>> origin/feature-kunal-DMS",
    r"\1",
    content,
    flags=re.DOTALL
)

with open("frontend/app/entities/page.tsx", "w") as f:
    f.write(content)
