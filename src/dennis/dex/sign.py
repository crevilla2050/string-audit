"""
DEX Signature Support
Dennis v1
"""

import json
import base64
import os
import tarfile
import gzip
import io
import hashlib
from pathlib import Path
from datetime import datetime, timezone

from nacl.signing import SigningKey, VerifyKey

from dennis.dex.manifest import semantic_subset
from dennis.core.hash import canonical_hash

def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _serialize_subset(manifest):
    """
    Deterministic serialization of semantic subset.
    """
    subset = semantic_subset(manifest)

    return json.dumps(
        subset,
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")


def _tarinfo(name, data):
    ti = tarfile.TarInfo(name)
    ti.size = len(data)
    ti.mtime = 0
    ti.uid = 0
    ti.gid = 0
    ti.mode = 0o644
    return ti

def sign_dex(dex_path, private_key_path, key_id=None):
    """
    Append a signature to an existing DEX artifact.
    """
    import getpass
    from nacl.secret import SecretBox
    from nacl.pwhash import argon2id

    with open(private_key_path, "rb") as f:
        header = f.readline()

        if header != b"DENNIS-KEY-V1\n":
            raise ValueError("Unsupported key format")

        salt = f.read(argon2id.SALTBYTES)
        encrypted = f.read()
    
    dex_path = Path(dex_path)
    private_key_path = Path(private_key_path)

    password = getpass.getpass("Enter passphrase: ")

    key = argon2id.kdf(
        SecretBox.KEY_SIZE,
        password.encode(),
        salt,
        opslimit=argon2id.OPSLIMIT_MODERATE,
        memlimit=argon2id.MEMLIMIT_MODERATE,
    )

    box = SecretBox(key)

    try:
        private_bytes = box.decrypt(encrypted)
    except Exception:
        raise SystemExit("Invalid passphrase or corrupted key file.")

    signing_key = SigningKey(private_bytes)
    verify_key = signing_key.verify_key

    # --------------------------------------------------------
    # Derive canonical identity
    # --------------------------------------------------------

    public_key_bytes = verify_key.encode()
    derived_key_id = hashlib.sha256(public_key_bytes).hexdigest()[:16]

    declared_key_id = key_id  # may come from --key-id

    # --------------------------------------------------------
    # Detect mismatch (non-blocking)
    # --------------------------------------------------------

    if declared_key_id and declared_key_id != derived_key_id:
        print("\n[Dennis] WARNING: key_id does not match derived identity")
        print(f"[Dennis] Declared: {declared_key_id}")
        print(f"[Dennis] Derived:  {derived_key_id}\n")

    # --------------------------------------------------------
    # Final key_id decision (preserve user intent)
    # --------------------------------------------------------

    final_key_id = declared_key_id or derived_key_id

    # --------------------------------------------------------
    # Visibility (always)
    # --------------------------------------------------------

    print(f"[Dennis] Signing with identity: {derived_key_id}")

    # ------------------------------
    # Load existing DEX
    # ------------------------------

    if not os.path.exists(dex_path):
        raise SystemExit(f"DEX artifact not found: {dex_path}")

    with gzip.open(dex_path, "rb") as gz:
        tar_bytes = gz.read()

    tar_buffer = io.BytesIO(tar_bytes)

    files = {}

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        for m in tar.getmembers():
            f = tar.extractfile(m)
            if f:
                files[m.name] = f.read()

    manifest = json.loads(files["manifest.json"])

    # ------------------------------
    # Sign semantic subset
    # ------------------------------

    data = _serialize_subset(manifest)

    signature = signing_key.sign(data).signature

    manifest.setdefault("signatures", []).append({
        "key_id": final_key_id,
        "algorithm": "ed25519",
        "created_at": _now(),
        "signature": base64.b64encode(signature).decode(),
        "derived_key_id": derived_key_id
    })

    files["manifest.json"] = json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False
    ).encode("utf-8")

    # --------------------------------------------------------
    # Store public key under FINAL key_id (critical fix)
    # --------------------------------------------------------

    files[f"signatures/{final_key_id}.pub"] = public_key_bytes

    # ------------------------------
    # Rebuild deterministic tar
    # ------------------------------

    tar_buffer = io.BytesIO()

    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:

        for name in sorted(files):
            data = files[name]
            ti = _tarinfo(name, data)
            tar.addfile(ti, io.BytesIO(data))

    # ------------------------------
    # Recompress
    # ------------------------------

    with open(dex_path, "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", compresslevel=9, mtime=0) as gz:
            gz.write(tar_buffer.getvalue())

    print(f"[Dennis] Artifact signed with key '{final_key_id}'")
    print(f"[Dennis] New artifact: {dex_path}")

def verify_manifest_signatures(manifest, files):
    """
    Verify signatures in-memory for inspect/validation flows.

    Preferred verification target:
      - payload.hash (as UTF-8 bytes)

    Backward compatibility:
      - semantic subset bytes, for previously signed artifacts.
    """
    payload_hash = (
        manifest.get("payload", {})
        .get("hash", {})
        .get("value", "")
    )
    payload_hash_bytes = payload_hash.encode("utf-8")
    subset_bytes = _serialize_subset(manifest)

    details = []

    for sig in manifest.get("signatures", []):
        key_id = sig.get("key_id")
        signature_b64 = sig.get("signature")
        pubkey = files.get(f"signatures/{key_id}.pub")

        entry = {
            "key_id": key_id,
            "valid": False,
        }

        if not signature_b64:
            entry["error"] = "missing signature"
            details.append(entry)
            continue

        if not pubkey:
            entry["error"] = "missing public key"
            details.append(entry)
            continue

        try:
            signature = base64.b64decode(signature_b64)
            verify_key = VerifyKey(pubkey)

            verified_via = None

            if payload_hash:
                try:
                    verify_key.verify(payload_hash_bytes, signature)
                    verification_method = "ed25519_payload_hash"
                except Exception:
                    verification_method = None

            if verification_method is None:
                try:
                    verify_key.verify(subset_bytes, signature)
                    verification_method = "ed25519_semantic_subset"
                except Exception:
                    verification_method = None

            if verification_method is None:
                entry["error"] = "signature mismatch"
            else:
                entry["valid"] = True
                entry["verification_method"] = verification_method

        except Exception as e:
            entry["error"] = str(e)

        details.append(entry)

    return details


def verify_dex(dex_path):
    """
    Verify all signatures in a DEX artifact.
    """

    dex_path = Path(dex_path)

    with gzip.open(dex_path, "rb") as gz:
        tar_bytes = gz.read()

    tar_buffer = io.BytesIO(tar_bytes)

    files = {}

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        for m in tar.getmembers():
            f = tar.extractfile(m)
            if f:
                files[m.name] = f.read()

    manifest = json.loads(files["manifest.json"])

    details = verify_manifest_signatures(manifest, files)

    results = [(d.get("key_id"), d.get("valid", False)) for d in details]

    return results
