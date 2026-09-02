from typing import Tuple

# Common prompt injection patterns (case-insensitive)
INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "ignore the instructions above",
    "override system prompt",
    "you are now a",
    "jailbreak",
    "ignore above",
    "forget what I said",
    "ignore rules",
    "bypass constraints",
    "system rules override"
]

def check_prompt_injection(query: str) -> Tuple[bool, str]:
    """Check if a search query contains potential prompt injection attempts."""
    if not query:
        return False, ""
        
    query_lower = query.lower()
    for keyword in INJECTION_KEYWORDS:
        if keyword in query_lower:
            return True, f"Potential prompt injection detected: matching keyword '{keyword}'"
    return False, ""

def validate_input_query(query: str) -> Tuple[bool, str, str]:
    """
    Validates a search query for safety and injection attempts.
    Returns: (is_safe, error_message, scrubbed_query) — "scrubbed_query" is
    now just the original query (no PII scrubbing); the name is kept so
    every call site's unpacking still lines up.
    """
    is_injection, msg = check_prompt_injection(query)
    if is_injection:
        return False, msg, query

    return True, "", query
