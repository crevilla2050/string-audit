"""
Dennis Canonical Hash v1 Implementation

This module implements the executable form of:
docs/specs/canonical_hash_v1.md

It defines the canonical identity of a plan.
Do not modify lightly.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any


# -----------------------------
# String normalization
# -----------------------------

def _normalize_strings(obj: Any) -> Any:
    """
    Recursively normalize all strings to NFC.

    This prevents cross-platform Unicode drift.
    """
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)

    if isinstance(obj, list):
        return [_normalize_strings(x) for x in obj]

    if isinstance(obj, dict):
        return {k: _normalize_strings(v) for k, v in obj.items()}

    return obj


# -----------------------------
# Canonical serialization
# -----------------------------

def canonical_json_bytes(obj: Any) -> bytes:
    """
    Convert an object into canonical JSON bytes.

    Rules:
    - UTF-8 encoding
    - Sorted keys
    - No whitespace
    - NFC string normalization
    - No trailing newline
    """
    normalized = _normalize_strings(obj)

    # separators=(',', ':') removes spaces
    s = json.dumps(
        normalized,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    # Explicit UTF-8 encoding
    return s.encode("utf-8")


# -----------------------------
# Hash helpers
# -----------------------------

def canonical_hash(obj: Any) -> str:
    """
    Compute SHA-256 hash of canonical JSON representation.
    Returns lowercase hex string.
    """
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def canonical_hash_bytes(data: bytes) -> str:
    """
    Hash already-canonicalized bytes.
    """
    return hashlib.sha256(data).hexdigest()


# -----------------------------
# Verification helper
# -----------------------------

def verify_canonical(obj: Any, expected_hash: str) -> bool:
    """
    Verify that an object matches an expected canonical hash.
    """
    return canonical_hash(obj) == expected_hash