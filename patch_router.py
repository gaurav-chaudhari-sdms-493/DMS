with open("backend/app/api/v1/router.py", "r") as f:
    content = f.read()

import re

# Fix imports
content = re.sub(
    r"<<<<<<< HEAD\nfrom \. import auth.*?\n=======\nfrom \. import auth.*?\n>>>>>>> origin/feature-kunal-DMS",
    r"from . import auth, documents, search, folders, chat, admin, health, connectors, email_webhook, scanner_webhook, facts, entities, records, governance, departments, export, i18n, templates, billing",
    content,
    flags=re.DOTALL
)

# Fix router includes
content = re.sub(
    r"<<<<<<< HEAD\napi_router\.include_router\(billing\.router.*?\n=======\napi_router\.include_router\(templates\.router\)\napi_router\.include_router\(billing\.router.*?\n>>>>>>> origin/feature-kunal-DMS",
    r"api_router.include_router(templates.router)\napi_router.include_router(billing.router, tags=['billing'])",
    content,
    flags=re.DOTALL
)

with open("backend/app/api/v1/router.py", "w") as f:
    f.write(content)
