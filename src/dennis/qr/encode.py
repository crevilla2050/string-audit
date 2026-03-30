# src/dennis/qr/encode.py

import segno
from .dfp import build_dfp_uri

from io import StringIO
import re

HASH_RE = re.compile(r"^[a-f0-9]{64}$")

DEFAULT_FORGE = "https://forge.dennis.dev"

def make_qr_uri(plan_hash: str, registry: str | None = None) -> str:
    """
    Build canonical Dennis artifact URL for QR sharing.
    """
    plan_hash = plan_hash.replace("sha256:", "").strip()

    if registry is None:
        registry = DEFAULT_FORGE

    registry = registry.rstrip("/")

    return f"http://dennis.local/artifact/{plan_hash}"
    
    #return f"{registry}/artifact/{plan_hash}"


def generate_ascii_qr(plan_hash: str, registry: str | None = None) -> str:
    uri = make_qr_uri(plan_hash, registry=registry)
    qr = segno.make(uri)

    buf = StringIO()
    qr.terminal(out=buf, compact=True)

    return buf.getvalue()


def generate_png_qr(plan_hash: str, path: str) -> None:
    """
    Generate PNG QR file.
    """
    uri = make_qr_uri(plan_hash)
    qr = segno.make(uri)
    qr.save(path, scale=6, border=2)