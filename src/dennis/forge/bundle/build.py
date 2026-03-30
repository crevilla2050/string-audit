# dennis/forge/bundle/build.py

from datetime import datetime, timezone
from dennis.forge.hash.canonical import canonical_hash
from dennis.qr.encode import make_qr_uri


def build_bundle(plan: dict, include_qr=False, sign_key=None) -> dict:
    h = canonical_hash(plan)

    bundle = {
        "version": "1.0",
        "type": "dennis-forge-bundle",
        "meta": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tool": "dennis"
        },
        "plan": plan,
        "hash": f"sha256:{h}",
    }

    # 🔹 QR transport
    if include_qr:
        bundle["transport"] = {
            "qr_uri": make_qr_uri(h)
        }

    # 🔹 Signing hook (optional for now)
    if sign_key:
        from .sign import sign_bundle  # lazy import
        bundle["signature"] = sign_bundle(bundle, sign_key)

    return bundle