import re
from pathlib import Path
from typing import List

from ..models import Finding

class HardcodedStringDetector:
    name = "hardcoded-string"

    SUSPICIOUS_PATTERNS = [
        re.compile(r'print\((["\'])(.+?)\1\)'),
        re.compile(r'raise\s+\w+\((["\'])(.+?)\1\)'),
        re.compile(r'logging\.(info|warning|error|debug)\((["\'])(.+?)\2\)'),
    ]

    def scan_file(self, path: Path, lines: List[str]) -> List[Finding]:
        findings: List[Finding] = []

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            for pattern in self.SUSPICIOUS_PATTERNS:
                match = pattern.search(line)
                if match:
                    text = match.groups()[-1]
                    findings.append(
                        Finding(
                            file=str(path),
                            line=idx,
                            text=text,
                            detector=self.name,
                        )
                    )

        return findings
