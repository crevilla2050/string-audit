from pathlib import Path
import sqlite3
import json
from datetime import datetime, timezone

from dennis.core.hash import canonical_hash
from dennis.dex.sign import sign_dex

DB_PATH = Path.home() / ".dennis_keys.db"
# ------------------------------------------------------------
# DB INIT
# ------------------------------------------------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()


    cur.execute("""
    CREATE TABLE IF NOT EXISTS trusted_keys (
        key_id TEXT PRIMARY KEY,
        public_key TEXT,
        is_root INTEGER,
        approved_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS key_signatures (
        signer_key_id TEXT,
        signed_key_id TEXT,
        signature TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def load_public_key(pub_path: Path) -> str:
    return pub_path.read_text().strip()

def key_id_from_pub(pub: str) -> str:
    return canonical_hash(pub)[:16]

def now():
    return datetime.now(timezone.utc).isoformat()

def is_trusted(key_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()


    cur.execute("SELECT 1 FROM trusted_keys WHERE key_id=?", (key_id,))
    row = cur.fetchone()

    conn.close()
    return row is not None


# ------------------------------------------------------------
# BOOTSTRAP
# ------------------------------------------------------------

def bootstrap_key(pub_path: Path):
    init_db()


    pub = load_public_key(pub_path)
    key_id = key_id_from_pub(pub)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO trusted_keys
        (key_id, public_key, is_root, approved_at)
        VALUES (?, ?, ?, ?)
    """, (key_id, pub, 1, now()))

    conn.commit()
    conn.close()

    print(f"[Dennis] Root key registered: {key_id}")


# ------------------------------------------------------------
# APPROVE
# ------------------------------------------------------------

def approve_key(new_pub_path: Path, signer_key_path: Path):
    init_db()


    # load keys
    new_pub = load_public_key(new_pub_path)
    signer_pub = load_public_key(signer_key_path.with_suffix(".pub"))

    new_id = key_id_from_pub(new_pub)
    signer_id = key_id_from_pub(signer_pub)

    if not is_trusted(signer_id):
        raise SystemExit(f"Signer key not trusted: {signer_id}")

    # sign new key
    signature = sign_dex(signer_key_path, new_pub.encode("utf-8"))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # store trusted key
    cur.execute("""
        INSERT OR REPLACE INTO trusted_keys
        (key_id, public_key, is_root, approved_at)
        VALUES (?, ?, ?, ?)
    """, (new_id, new_pub, 0, now()))

    # store signature
    cur.execute("""
        INSERT INTO key_signatures
        (signer_key_id, signed_key_id, signature, created_at)
        VALUES (?, ?, ?, ?)
    """, (signer_id, new_id, signature.hex(), now()))

    conn.commit()
    conn.close()

    print(f"[Dennis] Key approved: {new_id} (signed by {signer_id})")


    # ------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------

def list_keys():
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT key_id, is_root, approved_at FROM trusted_keys")

    rows = cur.fetchall()
    conn.close()

    print("\n[Dennis] Trusted keys:\n")

    for key_id, is_root, approved_at in rows:
        role = "ROOT" if is_root else "USER"
        print(f"{key_id}  [{role}]  {approved_at}")

    print()

