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

def build_manifest(
    payload_hash_value,
    payload_type,
    execution=None,
    created_by="dennis",
    lineage=None
):
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
        "lineage": lineage or {
            "lineage_id": None,
            "parent": None,
            "type": "detached",
        },
        "execution": execution or {},
        "signatures": [],
    }

def build_root_lineage(payload_hash):
    """
    Create lineage block for ROOT artifact.
    """
    return {
        "lineage_id": payload_hash,
        "parent": None,
        "type": "root",
    }

def build_derived_lineage(parent_manifest, payload_hash):
    """
    Inherit lineage from parent artifact.

    CRITICAL:
    - lineage_id must be preserved from root
    - parent must point to immediate previous artifact
    """

    parent_lineage = parent_manifest.get("lineage", {})

    parent_hash = parent_manifest.get("payload", {}).get("hash", {}).get("value")

    lineage_id = parent_lineage.get("lineage_id")

    if not lineage_id:
        raise ValueError("Parent lineage missing lineage_id")

    return {
        "lineage_id": lineage_id,   # ✅ FIXED
        "parent": parent_hash,
        "type": "derived",
    }

def build_detached_lineage():
    """
    Explicit detached lineage (no history).
    """
    return {
        "lineage_id": None,
        "parent": None,
        "type": "detached",
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
        "lineage": manifest.get("lineage", {}),
    }


def validate_lineage_structure(manifest):
    """
    Basic structural validation of lineage block.
    """

    lineage = manifest.get("lineage")

    if not lineage:
        raise ValueError("Missing lineage block")

    ltype = lineage.get("type")

    if ltype not in ("root", "derived", "detached"):
        raise ValueError(f"Invalid lineage type: {ltype}")

    if ltype == "root":
        if lineage.get("parent") is not None:
            raise ValueError("Root must not have parent")

        if not lineage.get("lineage_id"):
            raise ValueError("Root must define lineage_id")

    if ltype == "derived":
        if not lineage.get("parent"):
            raise ValueError("Derived must have parent")

        if not lineage.get("lineage_id"):
            raise ValueError("Derived must have lineage_id")

    if ltype == "detached":
        if lineage.get("lineage_id") is not None:
            raise ValueError("Detached must not define lineage_id")


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