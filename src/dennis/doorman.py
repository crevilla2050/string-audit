from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DecodeResult:
    accepted: bool
    text: str | None
    encoding: str | None
    reason: str | None


def decode_text(data: bytes) -> DecodeResult:
    """
    Decode a byte sequence into text.

    The core currently recognizes UTF-8 and UTF BOMs.
    Additional encodings can be supplied later through
    plugins without changing the document parsers.
    """

    if b"\x00" in data:
        return DecodeResult(
            accepted=False,
            text=None,
            encoding=None,
            reason="binary",
        )

    # UTF-8 BOM
    if data.startswith(b"\xef\xbb\xbf"):
        try:
            return DecodeResult(
                accepted=True,
                text=data.decode("utf-8-sig"),
                encoding="utf-8-sig",
                reason=None,
            )
        except UnicodeDecodeError:
            pass

    # UTF-16 BOMs
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        for encoding in ("utf-16",):
            try:
                return DecodeResult(
                    accepted=True,
                    text=data.decode(encoding),
                    encoding=encoding,
                    reason=None,
                )
            except UnicodeDecodeError:
                pass

    # Normal UTF-8
    try:
        return DecodeResult(
            accepted=True,
            text=data.decode("utf-8"),
            encoding="utf-8",
            reason=None,
        )
    except UnicodeDecodeError:
        return DecodeResult(
            accepted=False,
            text=None,
            encoding=None,
            reason="unsupported_encoding",
        )
