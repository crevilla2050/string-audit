import json
from typing import List
from ..models import Finding

def write_json_report(findings: List[Finding], output_path: str) -> None:
    data = [
        {
            "file": f.file,
            "line": f.line,
            "text": f.text,
            "detector": f.detector,
            "severity": f.severity,
        }
        for f in findings
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
