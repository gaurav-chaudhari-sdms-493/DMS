import re
from typing import Tuple

# Regular expressions for PII detection
PII_PATTERNS = {
    "email": r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b",
    "phone": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b"
}

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

def clean_pii(text: str) -> str:
    """Scrub sensitive PII (emails, phones, credit cards, SSNs) from text."""
    if not text:
        return text
    
    cleaned = text
    for pii_type, pattern in PII_PATTERNS.items():
        cleaned = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", cleaned)
    return cleaned

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
    Returns: (is_safe, error_message, scrubbed_query)
    """
    # 1. Check prompt injection
    is_injection, msg = check_prompt_injection(query)
    if is_injection:
        return False, msg, query
        
    # 2. Scrub PII from input
    scrubbed = clean_pii(query)
    
    return True, "", scrubbed

def validate_output_summary(summary: str) -> str:
    """
    Validates the generated AI Summary.
    Scrubs any leaked PII to protect user privacy.
    """
    return clean_pii(summary)
