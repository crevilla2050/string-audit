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
    "file_hash",
    "type",
    "original",
    "replacement",
    "token",
    "helper_id",
    "helper_path",
    "insertion_line",  # For helper insert-type changes
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
            sorted(plan["changes"], key=lambda c: (c.get("file"), c.get("line") or 0)),
            start=1
        ):
            is_helper = ch.get("type") == "helper"

            row = {
                "id": ch.get("id", i),
                "file": ch.get("file"),
                "line": ch.get("line"),
                "file_hash": ch.get("file_hash", ""),
                "type": ch.get("type", "replace"),
                "original": "" if is_helper else ch.get("original"),
                "replacement": "" if is_helper else ch.get("replacement"),
                "token": "" if is_helper else ch.get("token"),
                "helper_id": ch.get("helper_id", ""),
                "helper_path": ch.get("helper_ref", ""),
                "helper_source": ch.get("helper_source",""),
                "insertion_line": ch.get("line") if is_helper else "",
                "confidence": "",
                "notes": "helper insertion point" if is_helper else "",
            }

            writer.writerow(row)

    # ----------------------------------------
    # UX hint
    # ----------------------------------------

    if any(c.get("type") == "helper" for c in plan.get("changes", [])):
        print(
            "[Dennis] NOTE: This plan includes helper patches.\n"
            "         CSV does NOT include helper code.\n"
            "         Ensure helper files exist under helpers/ before applying."
        )


# -------------------------
# CSV → changes[]
# -------------------------
def read_csv_changes(path: str) -> List[Dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        changes = []

        for row in reader:

            change_type = row.get("type") or "replace"

            # --------------------------------------
            # Helper reconstruction
            # --------------------------------------
            if change_type == "helper":
                changes.append({
                    "type": "helper",
                    "helper_id": row.get("helper_id"),
                    "helper_ref": row.get("helper_path"),
                    "helper_source": row.get("helper_source"),
                    "file": row.get("file"),
                    "line": int(row["line"]) if row.get("line") else None,
                })
                continue

            # --------------------------------------
            # Normal replace change
            # --------------------------------------
            changes.append({
                "id": row.get("id"),
                "file": row.get("file"),
                "line": int(row["line"]) if row.get("line") else None,
                "type": change_type,
                "original": row.get("original"),
                "replacement": row.get("replacement"),
                "token": row.get("token"),
            })

        return changes