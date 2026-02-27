# src/string_audit/qr/encode.py

import segno
from .dfp import build_dfp_uri

from io import StringIO


def make_qr_uri(plan_hash: str) -> str:
    """
    Build canonical Dennis QR URI.
    """
    plan_hash = plan_hash.replace("sha256:", "").strip()
    return f"dennis://plan/{plan_hash}"


def generate_ascii_qr(plan_hash: str) -> str:
    """
    Deterministic ASCII QR.
    Works across all segno versions.
    """
    uri = build_dfp_uri(plan_hash)
    qr = segno.make(uri)

    buf = StringIO()
    qr.terminal(out=buf, compact=True)
    return buf.getvalue()


def generate_png_qr(plan_hash: str, path: str) -> None:
    """
    Generate PNG QR file.
    """
    uri = build_dfp_uri(plan_hash)
    qr = segno.make(uri)
    qr.save(path, scale=6, border=2)