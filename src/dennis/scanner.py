from pathlib import Path
from typing import List
from fnmatch import fnmatch

from .models import Finding
from .detectors.hardcoded_strings import HardcodedStringDetector

from .utils import iter_files


DENNIS_GENERATED_PATTERNS = [
    "scan-result-*.obad.json",
    "dictionary-*.json",
    "dennis-*.json",
]


def is_dennis_generated_file(path: Path) -> bool:
    """
    Returns True if the file is a Dennis-generated artifact
    that should not be scanned.

    We intentionally do NOT exclude all JSON files because
    JSON may become a first-class scan target in the future.
    """

    if ".dennis" in path.parts:
        return True

    filename = path.name

    for pattern in DENNIS_GENERATED_PATTERNS:
        if fnmatch(filename, pattern):
            return True

    return False


def is_binary_file(path: Path, chunk_size: int = 1024) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read(chunk_size)
            if not chunk:
                return False

            if b"\x00" in chunk:
                return True

            text_chars = bytearray({7,8,9,10,12,13,27} | set(range(32,127)))
            non_text = sum(byte not in text_chars for byte in chunk)

            return (non_text / len(chunk)) > 0.30
    except Exception:
        return True


def scan_directory(
    root: Path,
    git_mode: str = "tracked",
    file_types: set[str] | None = None,
    use_default_plugins: bool = False,
) -> List[Finding]:
    findings: List[Finding] = []
    detector = HardcodedStringDetector()

    from dennis.plugins import load_plugins, resolve_plugins
    plugins = resolve_plugins(
        load_plugins(), use_default_plugins=use_default_plugins
    )
    html_extensions = {".html", ".htm"}
    office_extensions = {".docx", ".odt"}
    normalized_file_types = (
        {extension.lower() for extension in file_types}
        if file_types is not None else None
    )

    for file_path in iter_files(root, git_mode=git_mode):
        extension = file_path.suffix.lower()

        if normalized_file_types is not None and extension not in normalized_file_types:
            continue

        if is_dennis_generated_file(file_path):
            continue

        matching_plugins = [
            plugin for plugin in plugins
            if extension in plugin["extensions"]
        ]
        is_office_document = extension in office_extensions and bool(matching_plugins)

        # DOCX/ODT are ZIP packages and look binary to the generic detector.
        # Let their format-aware plugin inspect them first.
        if not is_office_document and is_binary_file(file_path):
            continue

        if is_office_document:
            for plugin in matching_plugins:
                try:
                    results = plugin["scan"](file_path, [])
                except Exception:
                    # A malformed or unsupported package is skipped without
                    # preventing the scan of other files.
                    continue

                for result in results:
                    if isinstance(result, Finding):
                        findings.append(result)
                    elif isinstance(result, dict):
                        text = result.get("text") or result.get("original")
                        if not text:
                            continue
                        findings.append(Finding(
                            file=result.get("file") or str(file_path),
                            line=result.get("line") or 1,
                            text=text,
                            detector=plugin["name"],
                        ))
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
        except Exception:
            continue

        # HTML has a conservative format-aware extractor. Avoid also treating
        # attribute values and embedded script strings as generic source strings.
        if extension not in html_extensions or not matching_plugins:
            for finding in detector.scan_file(file_path, lines):
                findings.append(finding)

        for plugin in matching_plugins:
            try:
                results = plugin["scan"](file_path, lines)
            except Exception:
                continue

            for result in results:
                if isinstance(result, Finding):
                    findings.append(result)
                elif isinstance(result, dict):
                    text = result.get("text") or result.get("original")
                    if not text:
                        continue
                    findings.append(Finding(
                        file=result.get("file") or str(file_path),
                        line=result.get("line") or 1,
                        text=text,
                        detector=plugin["name"],
                    ))

    return findings
