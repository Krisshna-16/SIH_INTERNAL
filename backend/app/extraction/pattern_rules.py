import re
from typing import List, Tuple

# Regex patterns
# Indian & International phone formats (e.g., +91 9876543210, 9876543210, +1-800-555-0199, 011-23456789)
PHONE_REGEX = re.compile(
    r'(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\(?\d{2,5}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}\b'
)

EMAIL_REGEX = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
)

URL_REGEX = re.compile(
    r'\b(?:https?://|www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?\b'
)

IP_REGEX = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
)


def normalize_phone(phone_str: str) -> str:
    """Normalizes phone number string into clean standard format."""
    digits = re.sub(r'[^\d+]', '', phone_str)
    if digits.startswith('+'):
        return digits
    if len(digits) == 10:
        return f"+91{digits}"
    if digits.startswith('0') and len(digits) == 11:
        return f"+91{digits[1:]}"
    return digits


def extract_regex_patterns(text: str) -> List[Tuple[str, str, str, float]]:
    """
    Extracts structured pattern entities using deterministic regex rules.
    
    Returns a list of tuples: (entity_type, raw_value, normalized_value, confidence)
    Confidence Scores:
    - High confidence (0.95 - 0.98) is assigned because regex pattern matches 
      for structured formats (emails, phones, URLs, IPs) are highly deterministic.
    """
    results = []

    # 1. Emails
    for match in EMAIL_REGEX.finditer(text):
        val = match.group(0).strip()
        results.append(("EMAIL", val, val.lower(), 0.98, "regex_email"))

    # 2. URLs
    for match in URL_REGEX.finditer(text):
        val = match.group(0).strip()
        results.append(("URL", val, val, 0.96, "regex_url"))

    # 3. IP Addresses
    for match in IP_REGEX.finditer(text):
        val = match.group(0).strip()
        results.append(("IP_ADDRESS", val, val, 0.97, "regex_ip"))

    # 4. Phones (ignoring matches that are substrings of URLs or IP addresses)
    for match in PHONE_REGEX.finditer(text):
        val = match.group(0).strip()
        # Filter out short digit strings or date strings like 2024-03-12
        clean_digits = re.sub(r'\D', '', val)
        if len(clean_digits) >= 7 and not val.startswith(('19', '20')) and not any(v in val for _, v, _, _, _ in results if _ == "IP_ADDRESS"):
            norm_val = normalize_phone(val)
            results.append(("PHONE", val, norm_val, 0.95, "regex_phone"))

    return results
