# src/string_audit/qr/decode.py
import re
from .dfp import parse_dfp_uri
from PIL import Image
from pyzbar.pyzbar import decode

def extract_uri_from_image(path: str) -> str:
    img = Image.open(path)
    decoded = decode(img)

    if not decoded:
        raise ValueError("No QR code detected")

    data = decoded[0].data.decode("utf-8")

    if not data.startswith("dennis://"):
        raise ValueError("Not a Dennis QR")

    return data

def decode_ascii_payload(text: str) -> str:
    """
    Extract DFP URI from ASCII payload.
    Accepts:
      - raw dfp:// string
      - pasted ASCII QR blocks (future)
    """
    text = text.strip()

    # Minimal v1 implementation:
    if text.startswith("dfp://"):
        return parse_dfp_uri(text)

    raise ValueError("No DFP payload found in ASCII input")


def decode_image_qr(path: str) -> str:
    """
    Placeholder for image decoding.
    Will use pyzbar later.
    """
    raise NotImplementedError(
        "Image QR decoding not implemented yet. "
        "Will be added with optional pyzbar dependency."
    )

def extract_uri_from_ascii(text: str) -> str:
    """
    Extracts DFP URI from ASCII QR payload.

    Works by searching for dennis:// pattern.
    """
    match = re.search(r"(dennis://[^\s]+)", text)
    if not match:
        raise ValueError("No DFP URI found in ASCII payload")
    return match.group(1)