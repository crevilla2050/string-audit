"""Pinned Trust Root records; download never constitutes trust."""
from __future__ import annotations
import base64, hashlib, json, sqlite3
from dataclasses import dataclass
from pathlib import Path
import rfc8785
from nacl.signing import VerifyKey

RECORD_TYPE = "ILP-TRUST-ROOT"
VERSION = "1.0"

class TrustRootError(ValueError): pass

def _load(data: bytes) -> dict:
    try: value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise TrustRootError("Invalid Trust Root JSON.") from exc
    if not isinstance(value, dict) or set(value) != {"record_type","version","key_id","public_key","previous_key_id","previous_signature"}:
        raise TrustRootError("Invalid Trust Root members.")
    if value["record_type"] != RECORD_TYPE or value["version"] != VERSION: raise TrustRootError("Unsupported Trust Root version.")
    if not isinstance(value["key_id"], str) or not value["key_id"]: raise TrustRootError("Invalid Trust Root key identifier.")
    try:
        key = base64.b64decode(value["public_key"], validate=True)
        if len(key) != 32: raise ValueError
    except Exception as exc: raise TrustRootError("Invalid Trust Root public key.") from exc
    return value

def fingerprint(data: bytes) -> str: return hashlib.sha256(data).hexdigest()

def _signed(record: dict) -> bytes:
    return rfc8785.dumps({k:v for k,v in record.items() if k != "previous_signature"})

def pin_bootstrap(data: bytes, expected_fingerprint: str, db_path: Path) -> dict:
    if fingerprint(data) != expected_fingerprint.lower(): raise TrustRootError("Trust Root fingerprint mismatch.")
    record = _load(data)
    if record["previous_key_id"] is not None or record["previous_signature"] is not None: raise TrustRootError("Bootstrap record must not claim rotation.")
    _store(db_path, record, active=True)
    return record

def rotate(data: bytes, db_path: Path) -> dict:
    record = _load(data)
    previous = record["previous_key_id"]
    if not isinstance(previous, str) or not isinstance(record["previous_signature"], str): raise TrustRootError("Rotation proof required.")
    with sqlite3.connect(db_path) as db:
        row = db.execute("SELECT public_key FROM trust_roots WHERE key_id=? AND active=1", (previous,)).fetchone()
    if row is None: raise TrustRootError("Previous active Trust Root is not pinned.")
    try: VerifyKey(base64.b64decode(row[0])).verify(_signed(record), base64.urlsafe_b64decode(record["previous_signature"] + "=" * (-len(record["previous_signature"])%4)))
    except Exception as exc: raise TrustRootError("Trust Root rotation signature invalid.") from exc
    _store(db_path, record, active=True, deactivate=previous)
    return record

def _store(path: Path, record: dict, active: bool, deactivate: str|None=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS trust_roots (key_id TEXT PRIMARY KEY, public_key TEXT NOT NULL, record TEXT NOT NULL, fingerprint TEXT NOT NULL, active INTEGER NOT NULL)")
        if deactivate: db.execute("UPDATE trust_roots SET active=0 WHERE key_id=?", (deactivate,))
        db.execute("INSERT OR REPLACE INTO trust_roots VALUES (?,?,?,?,?)", (record["key_id"], record["public_key"], json.dumps(record,sort_keys=True), fingerprint(rfc8785.dumps(record)), int(active)))

def inspect(data: bytes) -> dict:
    record=_load(data); return {"key_id":record["key_id"],"fingerprint":fingerprint(data),"rotation":record["previous_key_id"] is not None}
