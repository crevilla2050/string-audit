import re

URL_PATTERN = re.compile(
    r'^(https?|ftp|mailto|http)://',
    re.IGNORECASE
)

def is_url(text: str) -> bool:
    return bool(URL_PATTERN.match(text.strip()))