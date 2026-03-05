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


def sign_dex(dex_path, private_key_path, key_id="dev"):
    """
    Append a signature to an existing DEX artifact.
    """

    dex_path = Path(dex_path)
    private_key_path = Path(private_key_path)

    signing_key = SigningKey(private_key_path.read_bytes())
    verify_key = signing_key.verify_key

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
        "key_id": key_id,
        "algorithm": "ed25519",
        "created_at": _now(),
        "signature": base64.b64encode(signature).decode()
    })

    files["manifest.json"] = json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False
    ).encode("utf-8")

    files[f"signatures/{key_id}.pub"] = bytes(verify_key)

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

    subset_bytes = _serialize_subset(manifest)

    results = []

    for sig in manifest.get("signatures", []):

        key_id = sig["key_id"]
        signature = base64.b64decode(sig["signature"])

        pubkey = files.get(f"signatures/{key_id}.pub")

        if not pubkey:
            results.append((key_id, False))
            continue

        verify_key = VerifyKey(pubkey)

        try:
            verify_key.verify(subset_bytes, signature)
            results.append((key_id, True))
        except Exception:
            results.append((key_id, False))

    return results