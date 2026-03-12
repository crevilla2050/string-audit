"""
DEX Artifact Importer
Dennis v1

Safe loader for .dex artifacts.
"""

import tarfile
import gzip
import json
import io
from pathlib import Path

from dennis.core.hash import canonical_hash
from dennis.dex.validate import validate_manifest


ALLOWED_FILES = {
    "manifest.json",
}


def _safe_member_name(name: str):
    """
    Prevent path traversal attacks.
    """

    p = Path(name)

    if p.is_absolute():
        raise ValueError(f"Invalid absolute path in archive: {name}")

    if ".." in p.parts:
        raise ValueError(f"Path traversal detected: {name}")

    return name


def _validate_structure(members):
    """
    Ensure expected archive layout.
    """

    files = {m.name for m in members}

    if "manifest.json" not in files:
        raise ValueError("DEX missing manifest.json")

    payload_files = [f for f in files if f.startswith("payload/")]

    if len(payload_files) != 1:
        raise ValueError("DEX must contain exactly one payload file")

    return payload_files[0]


def import_dex(path):
    """
    Inspect and verify a DEX artifact.

    Returns:
        manifest, payload_bytes
    """

    path = Path(path)

    with gzip.open(path, "rb") as gz:
        tar_bytes = gz.read()

    tar_buffer = io.BytesIO(tar_bytes)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:

        members = tar.getmembers()

        if len(members) > 10:
            raise ValueError("Archive suspiciously large")

        for m in members:
            _safe_member_name(m.name)

        payload_name = None

        for m in members:
            if m.name.startswith("payload/") and m.isfile():
                payload_name = m.name
                break

        if payload_name is None:
            raise ValueError("payload file missing")

        manifest_file = tar.extractfile("manifest.json")

        if manifest_file is None:
            raise ValueError("manifest.json could not be read")

        manifest = json.load(manifest_file)
        
        validate_manifest(manifest)
        payload_file = tar.extractfile(payload_name)

        if payload_file is None:
            raise ValueError("payload could not be read")

        payload_bytes = payload_file.read()

    # --------------------------------------------------------
    # Verify payload hash
    # --------------------------------------------------------

    payload_hash_expected = manifest["payload"]["hash"]["value"]

    payload_hash_actual = canonical_hash(json.loads(payload_bytes))

    print("EXPECTED:", payload_hash_expected)
    print("ACTUAL:", payload_hash_actual)
    print("PAYLOAD:", payload_bytes[:200])

    if payload_hash_actual != payload_hash_expected:
        raise ValueError("Payload hash mismatch")

    return manifest, payload_bytes