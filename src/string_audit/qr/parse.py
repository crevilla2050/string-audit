from urllib.parse import urlparse, parse_qs


def parse_dfp_uri(uri: str) -> dict:
    """
    Returns structured data from DFP URI.
    """
    parsed = urlparse(uri)
    qs = parse_qs(parsed.query)

    return {
        "scheme": parsed.scheme,
        "host": parsed.netloc,
        "path": parsed.path,
        "hash": qs.get("hash", [None])[0],
        "version": qs.get("v", ["1"])[0],
    }