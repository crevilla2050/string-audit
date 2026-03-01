# core/rehydrate.py
from datetime import datetime
from .sort import sort_changes


def rehydrate_from_csv(changes):
    """
    Reconstruct a minimal plan structure from CSV changes.

    This function is intentionally NON-canonical.
    It produces a projection-level plan that must be
    canonicalized by forge.canonical layers.
    
    This function must remain entropy-free.
    Do not inject timestamps or version fields here.
    Canonical layers handle identity.
    """

    return {
        "meta": {
            # Canonicalizer will fill these deterministically
            "generated_at": None,
            "source": "csv",
        },
        "changes": sort_changes(changes),
    }