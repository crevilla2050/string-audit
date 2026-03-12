from nacl.signing import SigningKey
from nacl.secret import SecretBox
from nacl.pwhash import argon2id
from nacl.utils import random
from pathlib import Path
import getpass
import os

def generate_keypair(private_path=Path("dennis.key"), public_path=Path("dennis.pub")):

    password = getpass.getpass("Enter passphrase: ")
    confirm = getpass.getpass("Confirm passphrase: ")

    if password != confirm:
        raise RuntimeError("Passphrases do not match")

    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key

    private_bytes = signing_key.encode()
    public_bytes = verify_key.encode()

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

    public_path.write_bytes(public_bytes)

    print("\nPrivate key →", private_path)
    print("Public key  →", public_path)