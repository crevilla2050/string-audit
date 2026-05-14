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
    import hashlib

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

        # ----------------------------------------
        # Header hash (mucho strong!)
        # ----------------------------------------
        header_hash = hashlib.sha256(MAGIC + salt).digest()

        f.write(MAGIC)
        f.write(header_hash)
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

        header_hash = f.read(32)
        salt = f.read(SALT_SIZE)

        # ----------------------------------------
        # Validate header integrity
        # ----------------------------------------
        import hashlib

        expected_hash = hashlib.sha256(MAGIC + salt).digest()

        if header_hash != expected_hash:
            raise SystemExit("Corrupted XDEX header")

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


def sign_bytes(private_key_path: Path, data: bytes) -> bytes:
    """
    Sign arbitrary bytes using a Dennis private key.
    Returns raw signature bytes.
    """
    import getpass
    from nacl.secret import SecretBox
    from nacl.pwhash import argon2id
    from nacl.signing import SigningKey

    with open(private_key_path, "rb") as f:
        header = f.readline()

        if header != b"DENNIS-KEY-V1\n":
            raise ValueError("Unsupported key format")

        salt = f.read(argon2id.SALTBYTES)
        encrypted = f.read()

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

    return signing_key.sign(data).signature