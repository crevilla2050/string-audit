from typing import List
from ..models import Finding

def print_human_report(findings: List[Finding]) -> None:
    if not findings:
        print("No suspicious hardcoded strings found.")
        return

    print(f"Found {len(findings)} suspicious hardcoded strings\n")

    for f in findings:
        print(f"[WARN] {f.file}:{f.line}")
        print(f"    {f.text}\n")
