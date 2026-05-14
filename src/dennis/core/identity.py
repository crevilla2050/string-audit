def derive_key_id_from_public_key_bytes(public_key_bytes: bytes) -> str:
    import hashlib
    return hashlib.sha256(public_key_bytes).hexdigest()[:16]