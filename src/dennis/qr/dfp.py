# src/dennis/qr/dfp.py

import re

DFP_PREFIX = "dfp://v1/forge/"
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def build_dfp_uri(plan_hash: str) -> str:
    """Create canonical DFP URI."""
    if not SHA256_RE.match(plan_hash):
        raise ValueError("Invalid SHA-256 hash")
    return f"{DFP_PREFIX}{plan_hash}"


def parse_dfp_uri(uri: str) -> str:
    """Extract hash from a DFP URI."""
    if not uri.startswith(DFP_PREFIX):
        raise ValueError("Not a DFP v1 forge URI")

    plan_hash = uri[len(DFP_PREFIX):]

    if not SHA256_RE.match(plan_hash):
        raise ValueError("Malformed DFP hash")

    return plan_hash