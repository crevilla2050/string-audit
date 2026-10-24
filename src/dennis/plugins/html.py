"""Conservative HTML string extraction for Dennis.

This module deliberately does not rewrite HTML.  It extracts eligible text and
user-facing attribute values into a deterministic JSON-friendly structure while
retaining their exact source spans.  Offsets are zero-based Python string
(character) offsets; line and column numbers are one-based.
"""

from __future__ import annotations

import argparse
import html as html_entities
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

PLUGIN_NAME = "html-string-extractor"
SUPPORTED_EXTENSIONS = (".html", ".htm")

# Only these attributes are considered user-facing.  `value` is handled
# separately because it is meaningful for submit/button inputs only.
USER_FACING_ATTRIBUTES = frozenset(
    {
        "alt",
        "title",
        "placeholder",
        "aria-label",
        "aria-description",
        "aria-placeholder",
    }
)

_RAW_TEXT_ELEMENTS = frozenset({"script", "style"})
_TAG_NAME_RE = re.compile(r"</?\s*([A-Za-z][A-Za-z0-9:_-]*)")
_ATTRIBUTE_RE = re.compile(
    r"(?P<name>[^\s/>=]+)"
    r"(?:\s*=\s*(?:"
    r'"(?P<double>[^"]*)"'
    r"|'(?P<single>[^']*)'"
    r"|(?P<unquoted>[^\s>]+)"
    r"))?",
    re.DOTALL,
)


@dataclass(frozen=True)
class ExtractedString:
    """One eligible source occurrence, including its exact source span."""

    text: str
    file: str | None
    line: int
    column: int
    start: int
    end: int
    kind: str  # "text" or "attribute"
    tag: str | None
    attribute: str | None
    raw: str

    def to_dict(self) -> dict:
        return asdict(self)


def _line_column(source: str, offset: int) -> tuple[int, int]:
    # Treat LF, CRLF, and CR as line endings without normalizing the source.
    prefix = source[:offset]
    line = len(re.findall(r"\r\n|\r|\n", prefix)) + 1
    last_lf = prefix.rfind("\n")
    last_cr = prefix.rfind("\r")
    last_newline = max(last_lf, last_cr)
    return line, offset - last_newline


def _candidate(
    source: str,
    start: int,
    end: int,
    *,
    file: str | None,
    kind: str,
    tag: str | None,
    attribute: str | None = None,
) -> ExtractedString | None:
    if kind == "text":
        # Ignore formatting whitespace around visible text while retaining the
        # exact offsets of the actual candidate in the original source.
        while start < end and source[start].isspace():
            start += 1
        while end > start and source[end - 1].isspace():
            end -= 1

    raw = source[start:end]
    if not raw or not raw.strip():
        return None

    # HTML references are decoded for logical dictionary matching, while raw
    # source and offsets remain untouched for later exact-span operations.
    text = html_entities.unescape(raw)
    if not text.strip():
        return None

    line, column = _line_column(source, start)
    return ExtractedString(
        text=text,
        file=file,
        line=line,
        column=column,
        start=start,
        end=end,
        kind=kind,
        tag=tag,
        attribute=attribute,
        raw=raw,
    )


def _find_tag_end(source: str, start: int) -> int | None:
    """Return the offset after a tag's `>`, respecting quoted attributes."""
    quote: str | None = None
    i = start + 1
    while i < len(source):
        char = source[i]
        if quote:
            if char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
        elif char == ">":
            return i + 1
        i += 1
    return None


def _parse_tag(source: str, start: int, end: int) -> tuple[str, bool, list[tuple[str, int, int, str]]] | None:
    """Parse a completed tag and return tag name, closing flag, attributes.

    Attribute tuple is (lowercase name, value start, value end, raw value).
    Malformed tags are rejected rather than guessed at.
    """
    markup = source[start:end]
    if markup.startswith(("<!", "<?")):
        return None

    match = _TAG_NAME_RE.match(markup)
    if not match:
        return None

    tag_name = match.group(1).lower()
    closing = markup[1:2] == "/"
    if closing:
        return tag_name, True, []

    attrs: list[tuple[str, int, int, str]] = []
    pos = match.end()
    # Parse attributes in the original source so the value offsets remain exact.
    while pos < len(markup) - 1:
        while pos < len(markup) - 1 and (markup[pos].isspace() or markup[pos] == "/"):
            pos += 1
        if pos >= len(markup) - 1:
            break
        attr_match = _ATTRIBUTE_RE.match(markup, pos)
        if not attr_match:
            # The whole tag is ambiguous; don't extract from it.
            return None
        name = attr_match.group("name").lower()
        groups = ("double", "single", "unquoted")
        value_group = next((g for g in groups if attr_match.group(g) is not None), None)
        if value_group is not None:
            value_start = start + attr_match.start(value_group)
            value_end = start + attr_match.end(value_group)
            raw_value = attr_match.group(value_group)
            attrs.append((name, value_start, value_end, raw_value))
        pos = attr_match.end()

    return tag_name, False, attrs


def extract_html(
    source: str,
    *,
    file: str | Path | None = None,
) -> list[ExtractedString]:
    """Extract eligible HTML text nodes and user-facing attribute values.

    This is intentionally a small scanner, not a full HTML parser. Ambiguous or
    incomplete tags are skipped conservatively. The input is never modified.
    """
    file_name = str(file) if file is not None else None
    results: list[ExtractedString] = []
    i = 0
    text_start = 0
    raw_text_tag: str | None = None

    while i < len(source):
        if raw_text_tag:
            close_pattern = re.compile(rf"</\s*{re.escape(raw_text_tag)}\s*>", re.IGNORECASE)
            close_match = close_pattern.search(source, i)
            if close_match is None:
                break
            i = close_match.start()
            text_start = i
            raw_text_tag = None
            continue

        if source.startswith("<!--", i):
            # Flush ordinary text before the comment.
            candidate = _candidate(
                source, text_start, i, file=file_name, kind="text", tag=None
            )
            if candidate:
                results.append(candidate)
            comment_end = source.find("-->", i + 4)
            if comment_end < 0:
                # An unclosed comment makes the remainder ambiguous.
                text_start = len(source)
                break
            i = comment_end + 3
            text_start = i
            continue

        if source[i] != "<":
            i += 1
            continue

        # A less-than sign that cannot begin a tag remains ordinary text.
        possible_tag = _TAG_NAME_RE.match(source, i)
        if not possible_tag and not source.startswith(("<!", "<?"), i):
            i += 1
            continue

        # Flush visible text before a candidate markup boundary.
        candidate = _candidate(
            source, text_start, i, file=file_name, kind="text", tag=None
        )
        if candidate:
            results.append(candidate)

        tag_end = _find_tag_end(source, i)
        if tag_end is None:
            # Incomplete markup: don't interpret the rest of the document.
            text_start = len(source)
            break

        parsed = _parse_tag(source, i, tag_end)
        if parsed is None:
            # Declarations and processing instructions are ignored. A malformed
            # tag is skipped as a unit; no attribute guesses are made.
            i = tag_end
            text_start = i
            continue

        tag_name, closing, attributes = parsed
        if not closing:
            for attr_name, value_start, value_end, _raw_value in attributes:
                allowed = attr_name in USER_FACING_ATTRIBUTES
                if tag_name == "input" and attr_name == "value":
                    input_type = next(
                        (html_entities.unescape(raw).strip().lower()
                         for name, _s, _e, raw in attributes if name == "type"),
                        "text",
                    )
                    allowed = input_type in {"submit", "button"}
                if not allowed:
                    continue
                candidate = _candidate(
                    source,
                    value_start,
                    value_end,
                    file=file_name,
                    kind="attribute",
                    tag=tag_name,
                    attribute=attr_name,
                )
                if candidate:
                    results.append(candidate)

        i = tag_end
        text_start = i
        if not closing and tag_name in _RAW_TEXT_ELEMENTS:
            raw_text_tag = tag_name

    # Flush trailing text only when not inside script/style or an unclosed comment.
    if raw_text_tag is None and text_start < len(source):
        candidate = _candidate(
            source, text_start, len(source), file=file_name, kind="text", tag=None
        )
        if candidate:
            results.append(candidate)

    # Keep deterministic source order. For ties, text precedes attributes only
    # when it starts at the same position (normally attribute spans are distinct).
    results.sort(key=lambda item: (item.start, item.end, item.kind, item.attribute or ""))
    return results


def extract_html_file(path: str | Path) -> list[ExtractedString]:
    path = Path(path)
    # Strict UTF-8: don't silently replace bytes and corrupt source provenance.
    # newline="" preserves CRLF/CR exactly so recorded spans remain valid.
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        source = handle.read()
    return extract_html(source, file=path.as_posix())


def write_json(strings: Iterable[ExtractedString], output: str | Path) -> None:
    """Write a deterministic UTF-8 JSON array of extracted occurrences."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    records = [item.to_dict() for item in strings]
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(records, ensure_ascii=False, indent=2) + "\n")


def scan_file(path: Path, lines: list[str] | None = None) -> list[dict]:
    """Dennis external-scanner plugin adapter (rich records are retained here)."""
    return [item.to_dict() for item in extract_html_file(path)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract translatable strings from HTML into JSON")
    parser.add_argument("source", help="HTML file to scan")
    parser.add_argument("--out", default="html-strings.json", help="JSON output path")
    args = parser.parse_args()
    strings = extract_html_file(args.source)
    write_json(strings, args.out)
    print(f"Extracted {len(strings)} occurrence(s) → {args.out}")


if __name__ == "__main__":
    main()
