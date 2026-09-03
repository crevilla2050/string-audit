"""
Dennis Provenance Store

Persistent project-level provenance stored in:

    .dennis/provenance.json

The .dennis directory is part of Dennis project context and may be
preserved inside a DEX payload.
"""

import json
from pathlib import Path
from typing import Any

from dennis.dex.provenance import (
    PROVENANCE_VERSION,
    attach_provenance_hash,
    verify_provenance,
)


PROVENANCE_DIRECTORY = ".dennis"
PROVENANCE_FILENAME = "provenance.json"


def provenance_path(root: Path) -> Path:
    """Return the canonical provenance path for a project."""

    return root / PROVENANCE_DIRECTORY / PROVENANCE_FILENAME


def load_provenance(root: Path) -> dict[str, Any] | None:
    """
    Load and verify project provenance.

    Returns:
        Provenance dictionary if present and valid.
        None if provenance.json does not exist.

    Raises:
        ValueError if provenance exists but is invalid or tampered.
    """

    path = provenance_path(root)

    if not path.exists():
        return None

    try:
        provenance = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"Unable to read provenance: {path}"
        ) from exc

    if not isinstance(provenance, dict):
        raise ValueError("Provenance must be a JSON object")

    if not verify_provenance(provenance):
        raise ValueError(
            "Provenance integrity check failed"
        )

    return provenance


def save_provenance(
    root: Path,
    provenance: dict[str, Any],
) -> Path:
    """
    Persist verified provenance into .dennis/provenance.json.

    The provenance hash is recalculated before writing.
    """

    directory = root / PROVENANCE_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)

    result = attach_provenance_hash(provenance)

    path = directory / PROVENANCE_FILENAME

    path.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    return path


def create_root_provenance(
    payload_hash: str,
    created_at: str,
    created_by: str = "dennis",
) -> dict[str, Any]:
    """
    Create provenance for a root artifact.
    """

    provenance = {
        "provenance_version": PROVENANCE_VERSION,
        "history": [
            {
                "payload_hash": payload_hash,
                "type": "root",
                "created_at": created_at,
                "created_by": created_by,
            }
        ],
    }

    return attach_provenance_hash(provenance)