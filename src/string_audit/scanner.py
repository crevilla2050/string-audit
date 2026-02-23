from pathlib import Path
from typing import List

from .models import Finding
from .utils import iter_python_files
from .detectors.hardcoded_strings import HardcodedStringDetector

def scan_directory(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    detector = HardcodedStringDetector()

    for file_path in iter_python_files(root, git_aware=True):
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        findings.extend(detector.scan_file(file_path, lines))

    return findings
