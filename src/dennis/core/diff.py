from pathlib import Path
from typing import List, Dict

# --------------------------------------------------------
# FILE DIFF
# --------------------------------------------------------

def diff_files(old_file: Path, new_file: Path) -> List[Dict]:
    old_lines = old_file.read_text(encoding="utf-8").splitlines()
    new_lines = new_file.read_text(encoding="utf-8").splitlines()

    changes = []
    max_len = max(len(old_lines), len(new_lines))

    for i in range(max_len):
        old = old_lines[i] if i < len(old_lines) else None
        new = new_lines[i] if i < len(new_lines) else None

        if old == new:
            continue

        # ----------------------------------------
        # INSERT (new line exists, old doesn't)
        # ----------------------------------------
        if old is None and new is not None:
            changes.append({
                "type": "insert",
                "file": str(new_file),
                "line": i + 1,
                "original": None,
                "replacement": new
            })
            continue

        # ----------------------------------------
        # DELETE (old line exists, new doesn't)
        # ----------------------------------------
        if old is not None and new is None:
            changes.append({
                "type": "delete",
                "file": str(new_file),
                "line": i + 1,
                "original": old,
                "replacement": None
            })
            continue

        # ----------------------------------------
        # REPLACE
        # ----------------------------------------
        changes.append({
            "type": "replace",
            "file": str(new_file),
            "line": i + 1,
            "original": old,
            "replacement": new
        })

    return changes


# --------------------------------------------------------
# DIRECTORY DIFF
# --------------------------------------------------------

def diff_directories(old_dir: Path, new_dir: Path) -> List[Dict]:
    changes = []


    for new_file in new_dir.rglob("*"):
        if not new_file.is_file():
            continue

        rel_path = new_file.relative_to(new_dir)
        old_file = old_dir / rel_path

        # ----------------------------------------
        # New file entirely
        # ----------------------------------------
        if not old_file.exists():
            lines = new_file.read_text(encoding="utf-8").splitlines()

            for i, line in enumerate(lines):
                changes.append({
                    "type": "insert",
                    "file": str(new_file),
                    "line": i + 1,
                    "original": None,
                    "replacement": line
                })

            continue

        # ----------------------------------------
        # Existing file → diff
        # ----------------------------------------
        changes.extend(diff_files(old_file, new_file))

    return changes
