from nacl.signing import SigningKey
import base64


def sign_bytes(data: bytes, seed: bytes = None) -> dict:
    key = SigningKey(seed) if seed else SigningKey.generate()
    sig = key.sign(data).signature

    return {
        "algo": "ed25519",
        "pubkey": base64.b64encode(key.verify_key.encode()).decode(),
        "sig": base64.b64encode(sig).decode()
    }