# QR encode is always available
from .encode import (
    make_qr_uri,
    generate_ascii_qr,
    generate_png_qr,
)

# Optional decode backends
try:
    from .decode import (
        decode_ascii_payload,
        decode_image_qr,
        extract_uri_from_ascii,
        extract_uri_from_image,
    )
except Exception:  # optional dependency not installed
    decode_ascii_payload = None
    decode_image_qr = None
    extract_uri_from_ascii = None
    extract_uri_from_image = None