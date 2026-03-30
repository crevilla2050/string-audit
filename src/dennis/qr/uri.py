# src/string_audit/qr/uri.py
from urllib.parse import urlparse

class DFPURIError(ValueError):
    pass


def parse_dfp_uri(uri: str) -> str:
    """
    Parse dfp://v1/forge/<hash> and return hash.
    """
    if not uri.startswith("dfp://"):
        raise DFPURIError("Not a DFP URI")

    parsed = urlparse(uri)

    # dfp://v1/forge/<hash>
    parts = parsed.path.strip("/").split("/")

    if parsed.netloc != "v1":
        raise DFPURIError("Unsupported DFP version")

    if len(parts) != 2 or parts[0] != "forge":
        raise DFPURIError("Invalid DFP URI format")

    plan_hash = parts[1]

    if len(plan_hash) != 64:
        raise DFPURIError("Invalid SHA-256 hash")

    return plan_hash