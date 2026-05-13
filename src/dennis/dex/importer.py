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
    Ensure expected archive layout (v1 + v2 compatible).
    """

    files = {m.name for m in members}

    if "manifest.json" not in files:
        raise ValueError("DEX missing manifest.json")

    # ----------------------------------------
    # Detect payload/plan.json
    # ----------------------------------------

    if "payload/plan.json" not in files:
        raise ValueError("DEX missing payload/plan.json")

    # ----------------------------------------
    # Detect mode
    # ----------------------------------------

    has_files = any(f.startswith("payload/files/") for f in files)

    if has_files:
        return "state", "payload/plan.json"

    return "plan", "payload/plan.json"


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

        for m in members:
            _safe_member_name(m.name)

        mode, payload_name = _validate_structure(members)
        
        # if mode == "state":
        #     print("[Dennis] DEX mode: STATE (files + plan)")
        # else:
        #     print("[Dennis] DEX mode: PLAN (legacy)")


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

    # print("EXPECTED:", payload_hash_expected)
    # print("ACTUAL:", payload_hash_actual)
    # print("PAYLOAD:", payload_bytes[:200])

    if payload_hash_actual != payload_hash_expected:
        raise ValueError("Payload hash mismatch")

    return manifest, payload_bytes

def is_xdex(path):
    try:
        with open(path, "rb") as f:
            magic = f.read(5)
            return magic == b"XDEX1"
    except Exception:
        return False
    

def load_xdex(path):
    import hashlib
    from nacl.pwhash import argon2id

    path = Path(path)

    with open(path, "rb") as f:
        magic = f.read(5)

        if magic != b"XDEX1":
            raise SystemExit("Invalid XDEX file")

        header_hash = f.read(32)
        salt = f.read(argon2id.SALTBYTES)

        expected = hashlib.sha256(magic + salt).digest()

        if header_hash != expected:
            raise SystemExit("XDEX header is INVALID. The file may be corrupted or tampered with.")

    return {
        "type": "xdex",
        "encrypted": True,
        "header_valid": True,
        "path": str(path)
    }