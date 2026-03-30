# src/string_audit/qr/render.py

import qrcode
from pathlib import Path

from string_audit.utils.time import iso_timestamp_filename

def render_ascii_matrix(data: str):
    qr = qrcode.QRCode(border=1)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.get_matrix()


def ascii_from_matrix(matrix):
    black = "██"
    white = "  "
    return "\n".join(
        "".join(black if cell else white for cell in row)
        for row in matrix
    )


def generate_qr_bundle(uri: str, out_dir: Path):
    """
    Generates timestamped QR artifacts.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = iso_timestamp_filename()
    base = out_dir / f"dennis-qr-{ts}"

    # Matrix
    qr = qrcode.QRCode(border=1)
    qr.add_data(uri)
    qr.make(fit=True)
    matrix = qr.get_matrix()

    black = "██"
    white = "  "
    ascii_qr = "\n".join(
        "".join(black if cell else white for cell in row)
        for row in matrix
    )

    # Terminal
    print(ascii_qr)

    # TXT
    txt_path = base.with_suffix(".txt")
    txt_path.write_text(ascii_qr + "\n")

    # PNG
    png_path = base.with_suffix(".png")
    img = qrcode.make(uri)
    img.save(png_path)

    return txt_path, png_path

def render_ascii_qr(data: str) -> None:
    """
    Print QR to terminal.
    """
    qr = qrcode.QRCode(border=1)
    qr.add_data(data)
    qr.make(fit=True)

    matrix = qr.get_matrix()

    # ANSI block rendering
    black = "██"
    white = "  "

    for row in matrix:
        print("".join(black if cell else white for cell in row))


def save_png_qr(data: str, path: str) -> None:
    """
    Save QR as PNG.
    """
    img = qrcode.make(data)
    img.save(path)