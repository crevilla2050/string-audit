from pathlib import Path
from typing import List

from .models import Finding
from .utils import iter_python_files
from .detectors.hardcoded_strings import HardcodedStringDetector

from pathlib import Path
from .plugins import load_plugins
from .utils import iter_files  # we'll define this


def scan_directory(root: Path):
    
    plugins = load_plugins()
    print("[DEBUG] plugins:", [p["name"] for p in plugins])

    findings = []
    plugins = load_plugins()

    for file_path in iter_files(root, git_aware=True):

        try:
            lines = file_path.read_text(
                encoding="utf-8",
                errors="ignore"
            ).splitlines()
        except Exception:
            continue

        ext = file_path.suffix.lower()

        for plugin in plugins:

            if ext in plugin["extensions"]:
                findings.extend(plugin["scan"](file_path, lines))

            elif ext in plugin.get("SUPPORTED_EMBEDDERS", []):
                findings.extend(plugin["scan"](file_path, lines))

    return findings


