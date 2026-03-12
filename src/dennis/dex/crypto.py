"""
XDEX Encryption Support
Dennis v1

Implements encrypted artifact containers.

Design goals:
- simple
- auditable
- deterministic format
- no external dependencies beyond PyNaCl
"""

import os
import getpass
from pathlib import Path

from nacl.secret import SecretBox
from nacl.pwhash import argon2id


MAGIC = b"XDEX1"
SALT_SIZE = argon2id.SALTBYTES


# --------------------------------------------------------
# Password prompt
# --------------------------------------------------------

def prompt_password(confirm=False) -> bytes:

    pwd = getpass.getpass("Enter passphrase: ")

    if confirm:
        pwd2 = getpass.getpass("Confirm passphrase: ")

        if pwd != pwd2:
            raise ValueError("Passphrases do not match")

    if not pwd:
        raise ValueError("Empty password not allowed")

    return pwd.encode()


# --------------------------------------------------------
# Encrypt artifact
# --------------------------------------------------------

def encrypt_dex(dex_path, out_path=None):

    dex_path = Path(dex_path)

    if not dex_path.exists():
        raise SystemExit(f"Artifact not found: {dex_path}")

    if dex_path.suffix != ".dex":
        raise SystemExit("Expected a .dex artifact")

    password = prompt_password(confirm=True)

    data = dex_path.read_bytes()

    salt = os.urandom(SALT_SIZE)

    key = argon2id.kdf(
        SecretBox.KEY_SIZE,
        password,
        salt
    )

    box = SecretBox(key)

    encrypted = box.encrypt(data)

    if out_path is None:
        out_path = dex_path.with_suffix(".xdex")

    out_path = Path(out_path)

    with open(out_path, "wb") as f:

        f.write(MAGIC)
        f.write(salt)
        f.write(encrypted)

    return out_path


# --------------------------------------------------------
# Decrypt artifact
# --------------------------------------------------------

def decrypt_xdex(xdex_path, out_path=None):

    xdex_path = Path(xdex_path)

    if not xdex_path.exists():
        raise SystemExit(f"Artifact not found: {xdex_path}")

    password = prompt_password()

    with open(xdex_path, "rb") as f:

        magic = f.read(len(MAGIC))

        if magic != MAGIC:
            raise SystemExit("Invalid XDEX file")

        salt = f.read(SALT_SIZE)

        ciphertext = f.read()

    key = argon2id.kdf(
        SecretBox.KEY_SIZE,
        password,
        salt
    )

    box = SecretBox(key)

    try:
        decrypted = box.decrypt(ciphertext)
    except Exception:
        raise SystemExit("Decryption failed (wrong password or corrupted file)")

    if out_path is None:
        out_path = xdex_path.with_suffix(".dex")

    out_path = Path(out_path)

    with open(out_path, "wb") as f:
        f.write(decrypted)

    return out_path