# src/string_audit/filters/url_filter.py

def is_url(text: str) -> bool:
    if not text:
        return False

    return text.startswith((
        "http://",
        "https://",
        "ftp://"
    ))


def filter_url(mapping: dict) -> dict:
    return {
        k: v for k, v in mapping.items()
        if not is_url(v)
    }