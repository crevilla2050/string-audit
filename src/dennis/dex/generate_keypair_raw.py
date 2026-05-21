from nacl.signing import SigningKey
from nacl.secret import SecretBox
from nacl.pwhash import argon2id
from nacl.utils import random
from base64 import b64encode
from datetime import datetime, timezone

from dennis.core.hash import canonical_hash

import os
import json

def now():
    return datetime.now(timezone.utc).isoformat()


def generate_keypair_raw(name: str, email: str, org: str | None, passphrase: str):
    # --------------------------------------------------------
    # 1. Generate keypair
    # --------------------------------------------------------
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key

    private_bytes = signing_key.encode()
    public_bytes = verify_key.encode()

    # --------------------------------------------------------
    # 2. Encrypt private key
    # --------------------------------------------------------
    salt = random(argon2id.SALTBYTES)

    derived_key = argon2id.kdf(
        SecretBox.KEY_SIZE,
        passphrase.encode(),
        salt,
        opslimit=argon2id.OPSLIMIT_MODERATE,
        memlimit=argon2id.MEMLIMIT_MODERATE
    )

    box = SecretBox(derived_key)
    encrypted = box.encrypt(private_bytes)

    # --------------------------------------------------------
    # 3. Build identity
    # --------------------------------------------------------
    public_b64 = b64encode(public_bytes).decode("utf-8")

    identity = {
        "name": name,
        "email": email,
        "org": org,
        "public_key": public_b64,
        "created_at": now()
    }

    key_id = canonical_hash(public_b64)[:16]
    identity["id"] = key_id

    # --------------------------------------------------------
    # 4. Return everything (NO I/O)
    # --------------------------------------------------------
    return {
        "key_id": key_id,
        "public_key_b64": public_b64,
        "private_bytes": private_bytes,
        "salt": salt,
        "encrypted_private": encrypted,
        "identity": identity
    }

def write_key_files(private_path, public_path, result):
    # --------------------------------------------------------
    # Write private key (UNCHANGED FORMAT)
    # --------------------------------------------------------
    with open(private_path, "wb") as f:
        f.write(b"DENNIS-KEY-V1\n")
        f.write(result["salt"])
        f.write(result["encrypted_private"])

    os.chmod(private_path, 0o600)

    # --------------------------------------------------------
    # Write public key (UNCHANGED FORMAT)
    # --------------------------------------------------------
    public_path.write_text(
        json.dumps(result["identity"], indent=2),
        encoding="utf-8"
    )