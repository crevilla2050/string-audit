from pathlib import Path
import difflib


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def generate_line_changes(rel_path, before_text, after_text):
    before_lines = before_text.splitlines()
    after_lines = after_text.splitlines()

    matcher = difflib.SequenceMatcher(None, before_lines, after_lines)

    changes = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():

        if tag == "replace":
            for idx, (b, a) in enumerate(zip(before_lines[i1:i2], after_lines[j1:j2])):
                changes.append({
                    "file": str(rel_path),
                    "line": i1 + idx + 1,
                    "original": b,
                    "replacement": a
                })

        elif tag == "delete":
            for idx, b in enumerate(before_lines[i1:i2]):
                changes.append({
                    "file": str(rel_path),
                    "line": i1 + idx + 1,
                    "original": b,
                    "replacement": ""
                })

        elif tag == "insert":
            for idx, a in enumerate(after_lines[j1:j2]):
                changes.append({
                    "file": str(rel_path),
                    "line": i1 + idx + 1,
                    "original": "",
                    "replacement": a
                })

    return changes


def generate_plan_from_dirs(before_dir, after_dir):
    before_dir = Path(before_dir)
    after_dir = Path(after_dir)

    before_files = {
        p.relative_to(before_dir): p
        for p in before_dir.rglob("*") if p.is_file()
    }

    after_files = {
        p.relative_to(after_dir): p
        for p in after_dir.rglob("*") if p.is_file()
    }

    changes = []

    # -----------------------------
    # FILES IN AFTER (create/modify)
    # -----------------------------
    for rel_path, after_path in sorted(after_files.items()):
        before_path = before_files.get(rel_path)

        content_after = read_file(after_path)

        if before_path is None:
            # NEW FILE → treat as insert all
            lines = content_after.splitlines()
            for i, line in enumerate(lines):
                changes.append({
                    "file": str(rel_path),
                    "line": i + 1,
                    "original": "",
                    "replacement": line
                })
        else:
            content_before = read_file(before_path)

            if content_before != content_after:
                file_changes = generate_line_changes(rel_path, content_before, content_after)

                # SAFETY FALLBACK
                if len(file_changes) > 200:
                    # Replace entire file via single change
                    changes.append({
                        "file": str(rel_path),
                        "line": 1,
                        "original": content_before,
                        "replacement": content_after
                    })
                else:
                    changes.extend(file_changes)

    # -----------------------------
    # FILES REMOVED
    # -----------------------------
    for rel_path, before_path in sorted(before_files.items()):
        if rel_path not in after_files:
            content_before = read_file(before_path)

            # Delete entire file via replacement
            changes.append({
                "file": str(rel_path),
                "line": 1,
                "original": content_before,
                "replacement": ""
            })

    return {
        "changes": changes,
        "meta": {
            "generator": "diff-to-plan"
        }
    }