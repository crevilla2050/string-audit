from pathlib import Path
from typing import List

from .models import Finding
from .detectors.hardcoded_strings import HardcodedStringDetector

from .utils import iter_files


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


def scan_directory(root: Path, git_mode: str = "tracked") -> List[Finding]:
    findings: List[Finding] = []

    detector = HardcodedStringDetector()
    
    for file_path in iter_files(root, git_mode=git_mode):

        if is_binary_file(file_path):
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
        except Exception:
            continue

        # CORE detector
        for f in detector.scan_file(file_path, lines):
            findings.append(f)

        # PLUGINS
        from dennis.plugins import load_plugins

        plugins = load_plugins()

        for plugin in plugins:
            if file_path.suffix in plugin["extensions"]:
                try:
                    results = plugin["scan"](file_path, lines)

                    for r in results:
                        if isinstance(r, Finding):
                            findings.append(r)

                        elif isinstance(r, dict):
                            text = r.get("text") or r.get("original")
                            if not text:
                                continue

                            findings.append(
                                Finding(
                                    file=r.get("file"),
                                    line=r.get("line"),
                                    text=text,
                                    detector=plugin["name"],
                                )
                            )
                except Exception:
                    continue

    return findings