"""
CSV IO for Dennis plans.

CSV is a human-editable projection of the canonical JSON plan.
"""

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
def write_csv_from_plan(plan: Dict, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for ch in plan["changes"]:
            row = {
                "id": ch.get("id"),
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
                "line": int(row["line"]),
                "original": row["original"],
                "replacement": row["replacement"],
                "token": row["token"],
            })
        return changes