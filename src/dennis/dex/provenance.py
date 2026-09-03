"""
DEX Provenance Utilities
Dennis v1 Artifact Format
"""

from typing import Any

from dennis.core.hash import canonical_hash


PROVENANCE_VERSION = 1
PROVENANCE_HASH_FIELD = "provenance_hash"


def compute_provenance_hash(provenance: dict[str, Any]) -> str:
    """
    Compute the deterministic SHA-256 hash of provenance content.

    The provenance_hash field is excluded from the input so that
    the hash does not become self-referential.
    """

    unsigned = dict(provenance)
    unsigned.pop(PROVENANCE_HASH_FIELD, None)

    return canonical_hash(unsigned)


def attach_provenance_hash(
    provenance: dict[str, Any],
) -> dict[str, Any]:
    """
    Return a copy of provenance with its integrity hash attached.

    The input dictionary is not modified.
    """

    result = dict(provenance)
    result[PROVENANCE_HASH_FIELD] = compute_provenance_hash(result)

    return result


def verify_provenance(provenance: dict[str, Any]) -> bool:
    """
    Verify the integrity hash embedded in a provenance object.
    """

    expected = provenance.get(PROVENANCE_HASH_FIELD)

    if not isinstance(expected, str) or not expected:
        return False

    return expected == compute_provenance_hash(provenance)


def append_provenance(
    provenance: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Append an event to provenance history and recalculate its hash.

    The input dictionary is not modified.
    """

    result = dict(provenance)

    history = list(result.get("history", []))
    history.append(dict(event))

    result["history"] = history
    result["provenance_version"] = PROVENANCE_VERSION

    return attach_provenance_hash(result)