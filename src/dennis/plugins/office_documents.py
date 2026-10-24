"""Read-only text extraction for Microsoft Word DOCX and OpenDocument ODT.

The plugin emits paragraph-level strings and structural provenance as JSON-ready
records. It does not edit document packages or promise round-trip replacement.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET

PLUGIN_NAME = "office-document-string-extractor"
SUPPORTED_EXTENSIONS = (".docx", ".odt")

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
_STYLE_NS = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
_HEADER_FOOTER_TAGS = {
    f"{{{_STYLE_NS}}}header",
    f"{{{_STYLE_NS}}}footer",
    f"{{{_STYLE_NS}}}header-left",
    f"{{{_STYLE_NS}}}footer-left",
    f"{{{_STYLE_NS}}}header-first",
    f"{{{_STYLE_NS}}}footer-first",
}

_W_P = f"{{{_W_NS}}}p"
_W_T = f"{{{_W_NS}}}t"
_W_TAB = f"{{{_W_NS}}}tab"
_W_BR = f"{{{_W_NS}}}br"
_W_CR = f"{{{_W_NS}}}cr"
_TEXT_P = f"{{{_TEXT_NS}}}p"
_TEXT_H = f"{{{_TEXT_NS}}}h"
_TEXT_S = f"{{{_TEXT_NS}}}s"
_TEXT_TAB = f"{{{_TEXT_NS}}}tab"
_TEXT_LINE_BREAK = f"{{{_TEXT_NS}}}line-break"

# Archive limits are conservative safeguards, not a complete ZIP-bomb defense.
_MAX_XML_MEMBER_BYTES = 32 * 1024 * 1024
_MAX_ARCHIVE_ENTRIES = 10_000
_MAX_ARCHIVE_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
_MAX_COMPRESSION_RATIO = 1_000
_MIN_RATIO_CHECK_BYTES = 1024 * 1024


def _validate_archive_limits(archive: zipfile.ZipFile) -> None:
    infos = archive.infolist()

    if len(infos) > _MAX_ARCHIVE_ENTRIES:
        raise ValueError("Document archive contains too many entries")

    total_size = sum(info.file_size for info in infos)
    if total_size > _MAX_ARCHIVE_UNCOMPRESSED_BYTES:
        raise ValueError("Document archive exceeds the uncompressed size limit")

    for info in infos:
        if info.file_size < _MIN_RATIO_CHECK_BYTES:
            continue

        ratio = info.file_size / max(info.compress_size, 1)
        if ratio > _MAX_COMPRESSION_RATIO:
            raise ValueError(
                f"Document archive entry has an excessive compression ratio: "
                f"{info.filename}"
            )


@dataclass(frozen=True)
class DocumentString:
    text: str
    file: str
    format: str
    part: str
    paragraph_index: int
    paragraph_kind: str
    start: int
    end: int
    text_nodes: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def _read_xml(archive: zipfile.ZipFile, member: str) -> ET.Element | None:
    try:
        info = archive.getinfo(member)
    except KeyError:
        return None
    if info.file_size > _MAX_XML_MEMBER_BYTES:
        raise ValueError(f"XML member is too large to inspect safely: {member}")
    data = archive.read(member)
    upper_data = data.upper()
    if b"<!DOCTYPE" in upper_data or b"<!ENTITY" in upper_data:
        raise ValueError(f"DTD/entity declarations are not supported in document XML: {member}")
    return ET.fromstring(data)


def _paragraph_segments(paragraph: ET.Element, *, word: bool) -> list[tuple[str, str]]:
    """Return (element-path-within-paragraph, text) segments in document order."""
    segments: list[tuple[str, str]] = []

    def walk(node: ET.Element, path: str) -> None:
        if word:
            if node.tag == _W_T and node.text:
                segments.append((path, node.text))
            elif node.tag == _W_TAB:
                segments.append((path, "\t"))
            elif node.tag in {_W_BR, _W_CR}:
                segments.append((path, "\n"))
        else:
            if node.text:
                segments.append((path, node.text))
            if node.tag == _TEXT_S:
                count_raw = node.attrib.get(f"{{{_TEXT_NS}}}c", "1")
                try:
                    count = max(1, min(int(count_raw), 10000))
                except ValueError:
                    count = 1
                segments.append((path, " " * count))
            elif node.tag == _TEXT_TAB:
                segments.append((path, "\t"))
            elif node.tag == _TEXT_LINE_BREAK:
                segments.append((path, "\n"))

        for index, child in enumerate(list(node)):
            walk(child, f"{path}/{index}")
            if not word and child.tail:
                segments.append((f"{path}/{index}:tail", child.tail))

    walk(paragraph, ".")
    return segments


def _record_paragraphs(
    root: ET.Element,
    *,
    path: Path,
    file_format: str,
    part: str,
    paragraph_tags: tuple[str, ...],
    word: bool,
    restrict_to_header_footer: bool = False,
) -> list[DocumentString]:
    results: list[DocumentString] = []
    paragraph_index = 0

    def visit(node: ET.Element, ancestors: tuple[str, ...]) -> None:
        nonlocal paragraph_index
        local_ancestors = ancestors + (node.tag,)

        if node.tag in paragraph_tags:
            if restrict_to_header_footer and not any(
                tag in _HEADER_FOOTER_TAGS
                for tag in ancestors
            ):
                # In styles.xml, only actual header/footer content is relevant.
                pass
            else:
                paragraph_index += 1
                segments = _paragraph_segments(node, word=word)
                text_parts: list[str] = []
                node_records: list[dict] = []
                offset = 0
                for node_path, value in segments:
                    if not value:
                        continue
                    text_parts.append(value)
                    node_records.append({
                        "path": node_path,
                        "start": offset,
                        "end": offset + len(value),
                        "text": value,
                    })
                    offset += len(value)
                text = "".join(text_parts)
                if text.strip():
                    results.append(DocumentString(
                        text=text,
                        file=path.as_posix(),
                        format=file_format,
                        part=part,
                        paragraph_index=paragraph_index,
                        paragraph_kind=("heading" if node.tag == _TEXT_H else "paragraph"),
                        start=0,
                        end=len(text),
                        text_nodes=node_records,
                    ))

        for child in list(node):
            visit(child, local_ancestors)

    visit(root, ())
    return results


def _identify_document_format(archive: zipfile.ZipFile) -> str:
    """Identify supported packages and validate metadata when present."""
    names = set(archive.namelist())
    has_word_part = "word/document.xml" in names
    has_odt_part = "content.xml" in names

    if has_word_part and has_odt_part:
        raise ValueError(
            "Ambiguous Office package contains both DOCX and ODT document parts"
        )

    if has_word_part:
        root = _read_xml(archive, "word/document.xml")
        if root is None or root.tag != f"{{{_W_NS}}}document":
            raise ValueError(
                "Invalid DOCX package: missing or invalid Word document root"
            )

        if "[Content_Types].xml" in names:
            content_types = _read_xml(archive, "[Content_Types].xml")
            expected = (
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document.main+xml"
            )
            valid = content_types is not None and any(
                element.tag.endswith("Override")
                and element.attrib.get("PartName") == "/word/document.xml"
                and element.attrib.get("ContentType") == expected
                for element in content_types.iter()
            )
            if not valid:
                raise ValueError(
                    "Invalid DOCX package: missing or contradictory Word "
                    "document content type"
                )
        return "docx"

    if has_odt_part:
        root = _read_xml(archive, "content.xml")
        expected_root = (
            "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
            "document-content"
        )
        if root is None or root.tag != expected_root:
            raise ValueError(
                "Invalid ODT package: missing or invalid OpenDocument content root"
            )

        if "mimetype" in names:
            info = archive.getinfo("mimetype")
            if info.file_size > 256:
                raise ValueError("Invalid ODT package: mimetype marker is too large")
            try:
                mimetype = archive.read("mimetype").decode("ascii")
            except UnicodeDecodeError:
                raise ValueError(
                    "Invalid ODT package: mimetype marker is not ASCII"
                ) from None
            if mimetype != "application/vnd.oasis.opendocument.text":
                raise ValueError(
                    "Invalid ODT package: contradictory mimetype marker"
                )
        return "odt"

    raise ValueError("Unrecognized Office package: no supported document part found")


def extract_document(path: str | Path) -> list[DocumentString]:
    """Extract paragraph-level strings from .docx or .odt without modifying it."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported document extension: {suffix}")

    results: list[DocumentString] = []
    with zipfile.ZipFile(path, "r") as archive:
        _validate_archive_limits(archive)
        detected_format = _identify_document_format(archive)
        if detected_format != suffix[1:]:
            raise ValueError(
                f"Document extension mismatch: file ends in {suffix}, "
                f"but package content identifies as {detected_format.upper()}"
            )
        if suffix == ".docx":
            members = ["word/document.xml"]
            names = archive.namelist()
            members.extend(sorted(
                name for name in names
                if name.startswith("word/header") and name.endswith(".xml")
            ))
            members.extend(sorted(
                name for name in names
                if name.startswith("word/footer") and name.endswith(".xml")
            ))
            for member in members:
                root = _read_xml(archive, member)
                if root is None:
                    continue
                results.extend(_record_paragraphs(
                    root,
                    path=path,
                    file_format="docx",
                    part=member,
                    paragraph_tags=(_W_P,),
                    word=True,
                ))
        else:
            content = _read_xml(archive, "content.xml")
            if content is not None:
                results.extend(_record_paragraphs(
                    content,
                    path=path,
                    file_format="odt",
                    part="content.xml",
                    paragraph_tags=(_TEXT_P, _TEXT_H),
                    word=False,
                ))
            styles = _read_xml(archive, "styles.xml")
            if styles is not None:
                results.extend(_record_paragraphs(
                    styles,
                    path=path,
                    file_format="odt",
                    part="styles.xml",
                    paragraph_tags=(_TEXT_P, _TEXT_H),
                    word=False,
                    restrict_to_header_footer=True,
                ))

    return results


def write_json(strings: Iterable[DocumentString], output: str | Path) -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps([item.to_dict() for item in strings], ensure_ascii=False, indent=2) + "\n"
        )


def scan_file(path: Path, lines: list[str] | None = None) -> list[dict]:
    """Dennis external-scanner plugin adapter."""
    results = []
    for item in extract_document(path):
        record = item.to_dict()
        record["line"] = item.paragraph_index
        results.append(record)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract DOCX/ODT text into JSON")
    parser.add_argument("source", help="A .docx or .odt document")
    parser.add_argument("--out", default="document-strings.json", help="JSON output path")
    args = parser.parse_args()
    strings = extract_document(args.source)
    write_json(strings, args.out)
    print(f"Extracted {len(strings)} paragraph(s) → {args.out}")


if __name__ == "__main__":
    main()
