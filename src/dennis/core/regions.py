from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import re
import secrets
import string


REGION_VERSION = 2

OPEN_MARKER = "{[#"
CLOSE_MARKER = "#]}"

REGION_STATES = {
    "ORIGINAL",
    "MODIFIED",
    "REVISION",
    "REQUIRED",
    "ELLIOT_NESS",
    "IGNORE"
}

_REGION_ID_ALPHABET = string.ascii_uppercase + string.digits

# Example:
# {[#ORIGINAL_F6N:"Hello world"#]}
_STATE_PATTERN = "|".join(
    re.escape(state)
    for state in sorted(
        REGION_STATES,
        key=len,
        reverse=True,
    )
)

REGION_PATTERN = re.compile(
    rf'\{{\[#({_STATE_PATTERN})_([A-Z0-9]{{3}}):'
    rf'"(.*?)"'
    rf'#\]\}}',
    re.DOTALL,
)


@dataclass(frozen=True)
class Region:
    id: str
    file: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    state: str
    original: str
    modified: str | None
    hash: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RegionError:
    file: str
    line: int
    column: int
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


def _region_hash(original: str) -> str:
    return hashlib.sha256(
        original.encode("utf-8")
    ).hexdigest()


def generate_region_id() -> str:
    """
    Generate a three-character alphanumeric region identifier.

    The identifier is an identity discriminator, not a document
    location and must therefore never depend on line or column.
    """
    return "".join(
        secrets.choice(_REGION_ID_ALPHABET)
        for _ in range(3)
    )


def _position_from_offset(
    text: str,
    offset: int,
) -> tuple[int, int]:

    line = text.count("\n", 0, offset) + 1

    last_newline = text.rfind("\n", 0, offset)

    if last_newline == -1:
        column = offset + 1
    else:
        column = offset - last_newline

    return line, column


def _escape_region_text(text: str) -> str:
    """
    Escape the minimal characters required by the region representation.

    The first implementation deliberately keeps this simple.
    """
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _unescape_region_text(text: str) -> str:
    return (
        text
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )


def _validate_regions(
    text: str,
    path: Path,
) -> list[RegionError]:

    errors: list[RegionError] = []

    open_positions = [
        match.start()
        for match in re.finditer(
            re.escape(OPEN_MARKER),
            text,
        )
    ]

    close_positions = [
        match.start()
        for match in re.finditer(
            re.escape(CLOSE_MARKER),
            text,
        )
    ]

    for close_offset in close_positions:

        preceding_opens = [
            pos
            for pos in open_positions
            if pos < close_offset
        ]

        if not preceding_opens:

            line, column = _position_from_offset(
                text,
                close_offset,
            )

            errors.append(
                RegionError(
                    file=str(path),
                    line=line,
                    column=column,
                    message=(
                        "closing region marker "
                        "without opening marker"
                    ),
                )
            )

    for open_offset in open_positions:

        close_offset = text.find(
            CLOSE_MARKER,
            open_offset + len(OPEN_MARKER),
        )

        if close_offset == -1:
            continue

        content = text[
            open_offset + len(OPEN_MARKER):
            close_offset
        ]

        if not content:

            line, column = _position_from_offset(
                text,
                open_offset,
            )

            errors.append(
                RegionError(
                    file=str(path),
                    line=line,
                    column=column,
                    message="empty region",
                )
            )

    return errors


def detect_regions(
    path: Path,
    text: str,
) -> tuple[list[Region], list[RegionError]]:

    """
    Detect Dennis regions.

    The region engine deliberately does not interpret the
    document format surrounding a region.
    """

    errors = _validate_regions(
        text,
        path,
    )

    regions: list[Region] = []

    for match in REGION_PATTERN.finditer(text):

        state = match.group(1)
        region_id = match.group(2)

        encoded_text = match.group(3)

        original = _unescape_region_text(
            encoded_text
        )

        if not original:
            continue

        start = match.start()
        end = match.end()

        start_line, start_column = (
            _position_from_offset(
                text,
                start,
            )
        )

        end_line, end_column = (
            _position_from_offset(
                text,
                end,
            )
        )

        modified = (
            original
            if state == "MODIFIED"
            else None
        )

        regions.append(
            Region(
                id=region_id,
                file=str(path),
                start_line=start_line,
                start_column=start_column,
                end_line=end_line,
                end_column=end_column,
                state=state,
                original=original,
                modified=modified,
                hash=_region_hash(original),
            )
        )

    return regions, errors


def format_region(
    text: str,
    *,
    state: str = "ORIGINAL",
    region_id: str | None = None,
) -> str:

    if state not in REGION_STATES:
        raise ValueError(
            f"invalid region state: {state}"
        )

    if region_id is None:
        region_id = generate_region_id()

    if not re.fullmatch(
        r"[A-Z0-9]{3}",
        region_id,
    ):
        raise ValueError(
            "region_id must contain exactly "
            "three alphanumeric characters"
        )

    escaped = _escape_region_text(text)

    return (
        f'{OPEN_MARKER}'
        f'{state}_{region_id}:"{escaped}"'
        f'{CLOSE_MARKER}'
    )


def regionize_text(
    text: str,
    regions: list[tuple[int, int]],
) -> str:

    if not regions:
        return text

    ordered = sorted(regions)

    previous_end = -1

    for start, end in ordered:

        if (
            start < 0
            or end < start
            or end > len(text)
        ):
            raise ValueError(
                "invalid region range"
            )

        if start < previous_end:
            raise ValueError(
                "overlapping regions"
            )

        previous_end = end

    result = text

    for start, end in reversed(ordered):

        region_text = text[start:end]

        result = (
            result[:start]
            + format_region(region_text)
            + result[end:]
        )

    return result


def regions_to_dict(
    path: Path,
    regions: list[Region],
) -> dict:

    return {
        "version": REGION_VERSION,
        "file": str(path),
        "regions": [
            region.to_dict()
            for region in regions
        ],
    }


def write_regions_json(
    output: Path,
    files: dict[str, list[Region]],
) -> None:

    payload = {
        "version": REGION_VERSION,
        "files": [
            {
                "file": filename,
                "regions": [
                    region.to_dict()
                    for region in regions
                ],
            }
            for filename, regions
            in sorted(files.items())
        ],
    }

    output.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )