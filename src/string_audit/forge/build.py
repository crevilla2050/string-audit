from datetime import datetime, timezone
from string_audit.forge.hash.canonical import canonical_hash
from string_audit.qr.encode import make_qr_uri


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

    if include_qr:
        bundle["transport"] = {
            "qr_uri": make_qr_uri(h)
        }

    # Signature comes later (Brick 3)
    if sign_key:
        bundle["signature"] = sign_bundle(bundle, sign_key)

    return bundle