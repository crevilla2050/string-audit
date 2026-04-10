from nacl.signing import SigningKey
from nacl.secret import SecretBox
from nacl.pwhash import argon2id
from nacl.utils import random
from pathlib import Path
import getpass
import os
import json
from datetime import datetime, timezone
from base64 import b64encode

from dennis.core.hash import canonical_hash

def now():
    return datetime.now(timezone.utc).isoformat()

def prompt(msg, required=True):
    while True:
        val = input(msg).strip()
        if val or not required:
            return val

        print("This field is required.")

def ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

def generate_keypair(private_path=None, public_path=None):

    if private_path is None or public_path is None:
        timestamp = ts()
        private_path = Path(f"dennis-{timestamp}.key")
        public_path = Path(f"dennis-{timestamp}.pub")
        print("\n[Dennis] Key Generation\n")

    # --------------------------------------------------------
    # Identity input
    # --------------------------------------------------------
        
    name = prompt("Name: ")
    email = prompt("Email: ")
    org = prompt("Organization (optional): ", required=False)

    password = getpass.getpass("Enter passphrase: ")
    confirm = getpass.getpass("Confirm passphrase: ")

    if password != confirm:
        raise RuntimeError("Passphrases do not match")

    # --------------------------------------------------------
    # Generate keys
    # --------------------------------------------------------

    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key

    private_bytes = signing_key.encode()
    public_bytes = verify_key.encode()

    # --------------------------------------------------------
    # Encrypt private key (UNCHANGED)
    # --------------------------------------------------------

    salt = random(argon2id.SALTBYTES)

    key = argon2id.kdf(
        SecretBox.KEY_SIZE,
        password.encode(),
        salt,
        opslimit=argon2id.OPSLIMIT_MODERATE,
        memlimit=argon2id.MEMLIMIT_MODERATE
    )

    box = SecretBox(key)
    encrypted = box.encrypt(private_bytes)

    with open(private_path, "wb") as f:
        f.write(b"DENNIS-KEY-V1\n")
        f.write(salt)
        f.write(encrypted)

    os.chmod(private_path, 0o600)

    # --------------------------------------------------------
    # Build identity (NEW)
    # --------------------------------------------------------

    identity = {
        "name": name,
        "email": email,
        "org": org,
        "public_key": b64encode(public_bytes).decode("utf-8"),
        "created_at": now()
    }

    # canonical identity for ID
    identity_json = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )

    key_id = canonical_hash(identity_json)[:16]
    identity["id"] = key_id

    # --------------------------------------------------------
    # Save public key (NEW FORMAT)
    # --------------------------------------------------------

    public_path.write_text(
        json.dumps(identity, indent=2),
        encoding="utf-8"
    )

    print("\n[Dennis] Key generated:")
    print(f"  ID: {key_id}")
    print(f"  Name: {name}")
    print(f"  Email: {email}")
    if org:
        print(f"  Org: {org}")
    print(f"\n  Private key → {private_path}")
    print(f"  Public key  → {public_path}")
