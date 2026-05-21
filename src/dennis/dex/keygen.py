from pathlib import Path
import getpass
import os
import json
from datetime import datetime, timezone
from dennis.dex.generate_keypair_raw import generate_keypair_raw, write_key_files

def ts():
    """
    Return a filesystem-safe UTC timestamp.

    Format:
    YYYY-MM-DDTHH-MM-SS
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

def prompt(msg, required=True):
    while True:
        try:
            val = input(msg).strip()
        except KeyboardInterrupt:
            print("\n\n[Aborted] Key generation cancelled by user.\n")
            return None

        if val or not required:
            return val

        print("This field is required.")

def generate_keypair(private_path=None, public_path=None):

    if private_path is None and public_path is None:
        keys_dir = Path.home() / ".dennis" / "keys"
        keys_dir.mkdir(parents=True, exist_ok=True)

        # Temporary placeholders (real names assigned after key generation)
        private_path = None
        public_path = None


        print("\n[Dennis] Key Generation\n")
    elif private_path is None or public_path is None:
        raise RuntimeError("Both private_path and public_path must be provided together")

    # --------------------------------------------------------
    # Identity input (UNCHANGED)
    # --------------------------------------------------------

    name = prompt("Name: ")
    if name is None:
        return

    email = prompt("Email: ")
    if email is None:
        return

    org = prompt("Organization (optional): ", required=False)
    if org is None:
        return

    max_attempts = 3
    password = None

    for attempt in range(1, max_attempts + 1):
        try:
            password = getpass.getpass("Enter passphrase: ")
            confirm = getpass.getpass("Confirm passphrase: ")
        except KeyboardInterrupt:
            print("\n\n[Aborted] Key generation cancelled by user.\n")
            return

        if password == confirm:
            break

        print(f"\n[Error] Passphrases do not match (attempt {attempt}/{max_attempts})")

        if attempt < max_attempts:
            print("Please try again.\n")
        else:
            print("\n[Aborted] Maximum attempts reached. Key generation cancelled.\n")
            return

    # --------------------------------------------------------
    # NEW: call core function
    # --------------------------------------------------------

    result = generate_keypair_raw(
        name=name,
        email=email,
        org=org,
        passphrase=password
    )

    # --------------------------------------------------------
    # Generate dynamic filenames (based on key_id + timestamp)
    # --------------------------------------------------------

    key_prefix = result["key_id"][:6]
    timestamp = ts()  # you already have this helper

    filename_base = f"{key_prefix}_{timestamp}"

    keys_dir = Path.home() / ".dennis" / "keys"

    private_path = keys_dir / f"{filename_base}.key"
    public_path = keys_dir / f"{filename_base}.pub"

    from dennis.forge.config import load_config, save_config

    cfg = load_config()
    cfg.setdefault("identity", {})
    cfg["identity"]["active"] = filename_base
    save_config(cfg)

    # --------------------------------------------------------
    # Write private key (NEW FORMAT)
    # --------------------------------------------------------

    write_key_files(private_path, public_path, result)

    # --------------------------------------------------------
    # Output (UNCHANGED)
    # --------------------------------------------------------

    print("\n[Dennis] Key generated:")
    print(f"  ID: {result['key_id']}")
    print(f"  Name: {result['identity']['name']}")
    print(f"  Email: {result['identity']['email']}")
    if result['identity']['org']:
        print(f"  Org: {result['identity']['org']}")
    print(f"\n  Private key → {private_path}")
    print(f"  Public key  → {public_path}")

