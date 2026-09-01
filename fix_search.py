import re

with open('backend/app/services/search_service.py', 'r') as f:
    content = f.read()

resolved = re.sub(
    r'<<<<<<< ours\nfrom app.services.config_service import get_int, get_float, get_str\n=======\nfrom app.services.config_service import get_int, get_float\nfrom app.services.search_glossary_service import expand_query_terms\n>>>>>>> theirs',
    'from app.services.config_service import get_int, get_float, get_str\nfrom app.services.search_glossary_service import expand_query_terms',
    content
)

with open('backend/app/services/search_service.py', 'w') as f:
    f.write(resolved)
