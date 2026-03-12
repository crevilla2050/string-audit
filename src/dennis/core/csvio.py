"""
CSV IO for Dennis plans.

CSV is a human-editable projection of the canonical JSON plan.
"""
from pathlib import Path
import csv
from typing import List, Dict

FIELDNAMES = [
    "id",
    "file",
    "line",
    "original",
    "replacement",
    "token",
    "confidence",
    "notes",
]

# -------------------------
# JSON → CSV
# -------------------------

def write_csv_from_plan(plan: Dict, path: Path) -> None:
    if "changes" not in plan:
        raise ValueError("Invalid plan: missing 'changes'")
        
    
    with open(path, "w", newline="\n", encoding="utf-8-sig") as f:
    
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for i, ch in enumerate(
                sorted(plan["changes"], key=lambda c: (c["file"], c["line"])),
                start=1
        ):
            row = {
                "id": ch.get("id", i),
                "file": ch.get("file"),
                "line": ch.get("line"),
                "original": ch.get("original"),
                "replacement": ch.get("replacement"),
                "token": ch.get("token"),
                "confidence": "",
                "notes": "",
            }
            writer.writerow(row)


# -------------------------
# CSV → changes[]
# -------------------------
def read_csv_changes(path: str) -> List[Dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        changes = []
        for row in reader:
            changes.append({
                "id": row["id"],
                "file": row["file"],
                "line": int(row["line"]) if row["line"] else None,
                "original": row["original"],
                "replacement": row["replacement"],
                "token": row["token"],
            })
        return changes