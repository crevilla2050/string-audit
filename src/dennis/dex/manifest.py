"""
DEX Manifest Builder and Signature Utilities
Dennis v1 Artifact Format
"""

from datetime import datetime, timezone


# ------------------------------------------------------------
# Time utilities
# ------------------------------------------------------------

def now_iso():
    """
    Return ISO-8601 UTC timestamp suitable for manifests.
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ------------------------------------------------------------
# Manifest Builder
# ------------------------------------------------------------

def build_manifest(payload_hash_value, payload_type, execution=None, created_by="dennis"):
    """
    Build a base DEX manifest structure.

    payload_hash_value : hex SHA-256 digest
    payload_type       : string describing payload format
    execution          : optional execution object
    created_by         : software identifier
    """

    return {
        "meta": {
            "format": "dex",
            "version": 1,
            "created_at": now_iso(),
            "created_by": created_by,
        },
        "payload": {
            "type": payload_type,
            "hash": {
                "algorithm": "sha256",
                "value": payload_hash_value,
            },
        },
        "execution": execution or {},
        "signatures": [],
    }


# ------------------------------------------------------------
# Semantic Subset (what gets signed)
# ------------------------------------------------------------

def semantic_subset(manifest):
    """
    Extract the canonical subset that signatures bind.
    """

    payload = manifest["payload"]

    return {
        "payload_hash_algorithm": payload["hash"]["algorithm"],
        "payload_hash_value": payload["hash"]["value"],
        "payload_type": payload["type"],
        "execution": manifest.get("execution", {}),
    }


# ------------------------------------------------------------
# Signature Handling
# ------------------------------------------------------------

def attach_signature(manifest, signature_entry):
    """
    Append a signature entry to the manifest history.
    """

    manifest.setdefault("signatures", []).append(signature_entry)


def create_signature_entry(key_id, algorithm, signature_value):
    """
    Create a signature entry structure.
    """

    return {
        "key_id": key_id,
        "algorithm": algorithm,
        "created_at": now_iso(),
        "signature": signature_value,
    }


# ------------------------------------------------------------
# Signature Verification
# ------------------------------------------------------------

def verify_signatures(manifest, verifier):
    """
    Verify all signatures using provided verifier function.

    verifier(subset, signature_entry) -> bool
    """

    subset = semantic_subset(manifest)

    results = []

    for sig in manifest.get("signatures", []):
        try:
            ok = verifier(subset, sig)
            results.append((sig, ok))
        except Exception:
            results.append((sig, False))

    return results