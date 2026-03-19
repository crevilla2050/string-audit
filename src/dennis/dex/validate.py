"""
DEX Manifest Validation
Dennis v1
"""

import json
from pathlib import Path
from importlib import resources

import jsonschema

import gzip
import tarfile
import io
import base64
import hashlib

from dennis.dex.manifest import verify_signatures, semantic_subset
from dennis.core.hash import canonical_hash

XDEX_MAGIC = b"XDEX1"
HEADER_HASH_SIZE = 32


def load_schema():
    """
    Load the DEX manifest JSON schema.
    """

    with resources.files("dennis.schemas").joinpath("dex.manifest.schema.json").open("r") as f:
        return json.load(f)


def validate_manifest(manifest):
    """
    Validate a manifest dictionary against schema.
    """

    schema = load_schema()

    jsonschema.validate(
        instance=manifest,
        schema=schema
    )


def validate_manifest_file(path):
    """
    Validate a manifest file from disk.
    """

    path = Path(path)
    manifest = json.loads(path.read_text())
    validate_manifest(manifest)

    return True

# ------------------------------------------------------------
# DEX Loader
# ------------------------------------------------------------

def _load_xdex(path: Path):
    """
    Load and validate XDEX header, then decrypt payload.
    """

    from dennis.dex.crypto import decrypt_xdex

    with open(path, "rb") as f:
        magic = f.read(len(XDEX_MAGIC))

        if magic != XDEX_MAGIC:
            return None  # not XDEX

        header_hash = f.read(HEADER_HASH_SIZE)
        salt = f.read(16)

        expected = hashlib.sha256(magic + salt).digest()

        if header_hash != expected:
            raise SystemExit("Invalid XDEX header (tampered or corrupted)")

    # If header is valid → decrypt
    decrypted_path = decrypt_xdex(path)

    return decrypted_path

def _load_dex(path: Path):
    import gzip
    import tarfile
    import io
    import json

    with gzip.open(path, "rb") as gz:
        tar_bytes = gz.read()

    tar_buffer = io.BytesIO(tar_bytes)

    files = {}

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        for m in tar.getmembers():
            f = tar.extractfile(m)
            if f:
                files[m.name] = f.read()

    manifest = json.loads(files["manifest.json"])

    return manifest, files

# ------------------------------------------------------------
# External Keys
# ------------------------------------------------------------

def _load_external_keys(signature_files):
    keys = {}

    if not signature_files:
        return keys

    for file in signature_files:
        p = Path(file)

        if not p.exists():
            raise SystemExit(f"Signature file not found: {p}")

        key_id = p.stem  # dev.pub → dev
        keys[key_id] = p.read_bytes()

    return keys


# ------------------------------------------------------------
# Embedded Key Discovery
# ------------------------------------------------------------

def _find_embedded_key(files, key_id):
    for name, data in files.items():
        if name.endswith(".pub") and key_id in name:
            return data
    return None


# ------------------------------------------------------------
# Verifier Builder
# ------------------------------------------------------------

def _build_verifier(files, external_keys=None):
    from nacl.signing import VerifyKey

    external_keys = external_keys or {}

    def verifier(subset, sig):
        key_id = sig["key_id"]

        # Priority 1: external
        pubkey = external_keys.get(key_id)

        # Fallback: embedded
        if not pubkey:
            pubkey = _find_embedded_key(files, key_id)

        if not pubkey:
            return False

        try:
            verify_key = VerifyKey(pubkey)
            signature = base64.b64decode(sig["signature"])

            # compute first
            subset_bytes = json.dumps(
                subset,
                sort_keys=True,
                separators=(",", ":")
            ).encode()

            verify_key.verify(subset_bytes, signature)

            return True

        except Exception:
            return False

    return verifier


# ------------------------------------------------------------
# Provenance (minimal for 0.7.0)
# ------------------------------------------------------------

def _validate_provenance_chain(provenance):
    if not isinstance(provenance, list):
        return False

    for step in provenance:
        if not isinstance(step, dict):
            return False

        required = ["step", "actor", "action", "timestamp"]
        for r in required:
            if r not in step:
                return False

    return True



# ------------------------------------------------------------
# MAIN VALIDATOR
# ------------------------------------------------------------

def validate_dex_file(path: str, signature_files=None):

    path = Path(path)

    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    # --------------------------------------------------
    # Detect XDEX
    # --------------------------------------------------

    xdex_result = _load_xdex(path)

    if xdex_result:
        path = Path(xdex_result)

    manifest, files = _load_dex(path)

    results = {}

    payload_bytes = files.get("payload/plan.json")

    if payload_bytes:
        actual_hash = canonical_hash(json.loads(payload_bytes))
        declared_hash = manifest.get("payload", {}).get("hash", {}).get("value")

        results["payload_integrity"] = (actual_hash == declared_hash)
    else:
        results["payload_integrity"] = False

    if results.get("payload_integrity"):
        print("[OK] Payload integrity verified")
    else:
        print("[FAIL] Payload integrity mismatch")

    # --------------------------------------------------
    # 1. Schema
    # --------------------------------------------------
    try:
        validate_manifest(manifest)
        results["schema"] = True
    except Exception:
        results["schema"] = False

    # --------------------------------------------------
    # 2. Signatures
    # --------------------------------------------------
    external_keys = _load_external_keys(signature_files)
    verifier = _build_verifier(files, external_keys)

    sig_results = verify_signatures(manifest, verifier)
    results["signatures"] = sig_results

    # --------------------------------------------------
    # 3. Provenance
    # --------------------------------------------------
    provenance = manifest.get("provenance", [])
    results["provenance"] = _validate_provenance_chain(provenance)
    results["provenance_steps"] = len(provenance)
    
    # --------------------------------------------------
    # 4. Identity
    # --------------------------------------------------
    results["payload_hash"] = manifest.get("payload", {}).get("hash", {}).get("value")
    results["container"] = "dex"
    results["provenance_hash"] = canonical_hash(provenance)
    results["container"] = "xdex"
    results["header_valid"] = True
    return results