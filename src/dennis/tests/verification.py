import sqlite3
from dennis.core.keys import DB_PATH
from dennis.dex.sign import verify_dex


def is_key_trusted(key_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "SELECT 1 FROM trusted_keys WHERE key_id = ?",
        (key_id,)
    )

    result = cur.fetchone()
    conn.close()

    return result is not None


def analyze_signatures(artifact):
    """
    Analyze signatures for:
    - validity (cryptographic)
    - trust (local DB)
    - acceptance (policy)

    Returns a structured dict.
    """

    results = verify_dex(artifact)

    if not results:
        return {
            "verified": False,
            "accepted": False,
            "policy": "strict",
            "signatures": 0,
            "valid_signatures": 0,
            "invalid_signatures": 0,
            "trusted_signatures": 0,
            "details": [],
            "errors": ["No signatures present"],
            "message": "✖ No signatures found"
        }

    enriched = []

    for key_id, is_valid in results:
        trusted = is_key_trusted(key_id)

        enriched.append({
            "key_id": key_id,
            "valid": is_valid,
            "trusted": trusted
        })

    total = len(enriched)
    valid_count = sum(1 for s in enriched if s["valid"])
    invalid_count = total - valid_count
    trusted_valid_count = sum(1 for s in enriched if s["valid"] and s["trusted"])

    has_valid = valid_count > 0
    has_trusted = trusted_valid_count > 0

    accepted = has_valid and has_trusted

    return {
        "verified": has_valid,
        "accepted": accepted,
        "policy": "strict",
        "signatures": total,
        "valid_signatures": valid_count,
        "invalid_signatures": invalid_count,
        "trusted_signatures": trusted_valid_count,
        "details": enriched,
        "errors": [],
        "message": (
            f"✔ Accepted ({trusted_valid_count}/{valid_count} trusted signatures)"
            if accepted else
            "✖ Not accepted (no trusted signatures)"
        )
    }