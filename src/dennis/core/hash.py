import json
import hashlib
from typing import Any


def _canonical_json(obj: Any) -> bytes:
    """
    Deterministic JSON serialization.

    Guarantees:
    - Sorted keys
    - No whitespace differences
    - Stable hashing across platforms
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def canonical_hash(obj: Any) -> str:
    """
    Compute deterministic SHA-256 hash of a Python object.

    This is the core identity primitive of Dennis.
    """
    return hashlib.sha256(_canonical_json(obj)).hexdigest()

from pathlib import Path

def sha256_file(path: Path) -> str:
    """
    Compute SHA-256 hash of a file.

    Used for workspace integrity checks when applying plans.
    """

    h = hashlib.sha256()

    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)

    return h.hexdigest()