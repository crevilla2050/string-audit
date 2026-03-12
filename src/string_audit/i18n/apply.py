import json
import re
from pathlib import Path
from typing import Dict, List


SAFE_PATTERNS = [
    re.compile(r'print\((["\'])(.+?)\1\)'),
    re.compile(r'raise\s+(\w+)\((["\'])(.+?)\2\)'),
    re.compile(r'logging\.(info|warning|error|debug)\((["\'])(.+?)\2\)'),
]


def load_dictionary(path: Path) -> Dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {v: k for k, v in data.items()}


def iter_python_files(root: Path):
    yield from root.rglob("*.py")


def replace_line(line: str, mapping: Dict[str, str]) -> str:
    for pattern in SAFE_PATTERNS:
        match = pattern.search(line)
        if not match:
            continue

        groups = match.groups()
        text = groups[-1]

        if text not in mapping:
            continue

        token = mapping[text]

        new_literal = f't("{token}")'
        return line.replace(f'"{text}"', new_literal).replace(f"'{text}'", new_literal)

    return line


def apply_to_file(path: Path, mapping: Dict[str, str], dry_run: bool = False) -> int:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    new_lines: List[str] = []
    changes = 0

    for line in lines:
        new_line = replace_line(line, mapping)
        if new_line != line:
            changes += 1
        new_lines.append(new_line)

    if changes and not dry_run:
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return changes


def apply_i18n(root: Path, dict_path: Path, dry_run: bool = False) -> int:
    mapping = load_dictionary(dict_path)
    total_changes = 0

    for py_file in iter_python_files(root):
        total_changes += apply_to_file(py_file, mapping, dry_run)

    return total_changes


def ensure_runtime_support(lines):
    for l in lines:
        if "dictionary.json" in l or "messages =" in l:
            return lines

    return lines


# --------------------------------------------------------
# HELPER PATCH APPLY
# --------------------------------------------------------

def apply_helper_patches(plan: Dict, log: Dict, dry_run: bool = False):

    helpers = plan.get("patches", {}).get("helpers", [])

    for helper in helpers:

        file_path = Path(helper["file"])
        line_no = helper.get("line", 1) - 1
        helper_block_lines = helper.get("lines", [])

        if not file_path.exists():
            log["warnings"].append({
                "file": str(file_path),
                "type": "missing_file",
                "context": "helper_patch"
            })
            continue

        print(f"Applying helper patch → {file_path}:{line_no + 1}")

        lines = file_path.read_text(encoding="utf-8").splitlines()

        line_no = max(0, min(line_no, len(lines)))

        helper_id = helper.get("id", "helper")

        start_marker = f"# >>> DENNIS-HELPER:{helper_id}"
        end_marker = f"# <<< DENNIS-HELPER:{helper_id}"

        # Prevent duplicate helper insertion
        if any(start_marker in l for l in lines):
            print(f"Helper '{helper_id}' already present in {file_path}, skipping.")
            continue

        helper_block = [start_marker] + helper_block_lines + [end_marker]

        new_lines = lines[:line_no] + helper_block + lines[line_no:]

        if not dry_run:
            file_path.write_text(
                "\n".join(new_lines) + "\n",
                encoding="utf-8"
            )

        log.setdefault("patches", []).append({
            "type": "patch_applied",
            "subtype": "helper",
            "file": str(file_path),
            "line": line_no + 1,
            "helper_id": helper.get("id")
        })

# --------------------------------------------------------
# HELPER PATCH REMOVE
# --------------------------------------------------------

def remove_helper_patches(plan: Dict, log: Dict, dry_run: bool = False):

    helpers = plan.get("patches", {}).get("helpers", [])

    for helper in helpers:

        file_path = Path(helper["file"])
        helper_block_lines = helper.get("lines", [])

        if not file_path.exists():
            log["warnings"].append({
                "file": str(file_path),
                "type": "missing_file",
                "context": "helper_removal"
            })
            continue

        print(f"Removing helper patch → {file_path}")

        lines = file_path.read_text(encoding="utf-8").splitlines()

        helper_id = helper.get("id", "helper")

        start_marker = f"# >>> DENNIS-HELPER:{helper_id}"
        end_marker = f"# <<< DENNIS-HELPER:{helper_id}"

        start = None
        end = None

        for i, line in enumerate(lines):
            if line.strip() == start_marker:
                start = i
            elif line.strip() == end_marker and start is not None:
                end = i
                break

        if start is not None and end is not None:
            new_lines = lines[:start] + lines[end + 1:]

            if not dry_run:
                file_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

            log.setdefault("patches", []).append({
                "type": "patch_removed",
                "subtype": "helper",
                "file": str(file_path),
                "line": start + 1,
                "helper_id": helper.get("id")
            })

            continue

        block_len = len(helper_block_lines)
        match_index = None

        for i in range(len(lines) - block_len + 1):
            if lines[i:i + block_len] == helper_block_lines:
                match_index = i
                break

        if match_index is None:
            log["warnings"].append({
                "file": str(file_path),
                "type": "helper_block_not_found",
                "helper_id": helper.get("id")
            })
            continue

        new_lines = lines[:match_index] + lines[match_index + block_len:]

        if not dry_run:
            file_path.write_text(
                "\n".join(new_lines) + "\n",
                encoding="utf-8"
            )

        log.setdefault("patches", []).append({
            "type": "patch_removed",
            "subtype": "helper",
            "file": str(file_path),
            "line": match_index + 1,
            "helper_id": helper.get("id")
        })


# --------------------------------------------------------
# MAIN PLAN APPLY
# --------------------------------------------------------

def apply_plan(plan_path: Path, dry_run: bool = False) -> int:

    import datetime

    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    changes = plan.get("changes", [])
    patches = plan.get("patches", {})
    meta = plan.get("meta", {})

    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    project_name = Path.cwd().name
    log_path = Path.cwd() / f"{project_name}-{timestamp}.json"

    log = {
        "plan": str(plan_path),
        "timestamp": timestamp,
        "changes_total": len(changes),
        "changes_applied": 0,
        "warnings": [],
        "skipped": []
    }

    # --------------------------------------
    # Helper patches
    # --------------------------------------
    remove_helpers = patches.get("remove_helpers", [])

    helpers = patches.get("helpers", [])

    # New-style explicit removal
    if remove_helpers:
        print(f"Removing {len(remove_helpers)} helper patch(es)\n")
        remove_helper_patches({"patches": {"helpers": remove_helpers}}, log, dry_run=dry_run)

    # Legacy invert-mode removal (only if explicit removal not present)
    elif helpers and meta.get("operation") == "invert":
        print(f"Removing {len(helpers)} helper patch(es)\n")
        remove_helper_patches(plan, log, dry_run=dry_run)

    if helpers:

        if meta.get("operation") == "invert":
            print(f"Removing {len(helpers)} helper patch(es)\n")
            remove_helper_patches(plan, log, dry_run=dry_run)

        else:
            print(f"Applying {len(helpers)} helper patch(es)\n")
            apply_helper_patches(plan, log, dry_run=dry_run)

    # --------------------------------------
    # Apply string transformations
    # --------------------------------------

    changes_by_file: Dict[str, List[dict]] = {}

    print(f"\nApplying plan: {plan_path}")
    print(f"Total changes in plan: {len(changes)}\n")

    for change in changes:
        changes_by_file.setdefault(change["file"], []).append(change)

    total = 0

    for file_name, file_changes in changes_by_file.items():

        file_changes.sort(key=lambda c: c["line"])
        file_path = Path(file_name)

        if not file_path.exists():
            log["warnings"].append({
                "file": str(file_path),
                "type": "missing_file"
            })
            continue

        expected_hash = file_changes[0].get("file_hash")

        if expected_hash:
            try:
                from dennis.core.hash import sha256_file
                current_hash = sha256_file(file_path)

                if current_hash != expected_hash:
                    print(f"⚠ File changed since plan generation: {file_path}")
                    print("Continuing with heuristic matching.\n")
            except Exception:
                pass

        lines = file_path.read_text(encoding="utf-8").splitlines()
        normalized_lines = [l.strip() for l in lines]

        line_index = {}
        for i, l in enumerate(normalized_lines):
            line_index.setdefault(l, []).append(i)

        modified = False

        for change in file_changes:

            line_no = change["line"] - 1
            expected = change["original"].strip()
            replacement = change["replacement"]

            match_index = None

            if 0 <= line_no < len(lines):
                if normalized_lines[line_no] == expected:
                    match_index = line_no

            if match_index is None:
                candidates = line_index.get(expected)
                if candidates:
                    match_index = candidates[0]

            if match_index is None:
                log["skipped"].append({
                    "file": str(file_path),
                    "line": change["line"],
                    "reason": "original_text_not_found"
                })
                continue

            if lines[match_index] != replacement:

                print(f"Applying change → {file_path}:{match_index + 1}")

                lines[match_index] = replacement
                normalized_lines[match_index] = replacement.strip()

                total += 1
                modified = True
                log["changes_applied"] += 1

        if modified and not dry_run:

            # Only inject runtime support during forward apply
            if meta.get("operation") != "invert":
                lines = ensure_runtime_support(lines)

            file_path.write_text(
                "\n".join(lines) + "\n",
                encoding="utf-8"
            )

    log_path.write_text(
        json.dumps(log, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    print(f"\nApplied {total} changes.")
    print(f"Log written → {log_path}\n")

    return total
