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

def apply_plan(plan_path: Path, dry_run: bool = False, confirm: str | None = None) -> int:

    import json
    import datetime
    from pathlib import Path
    from typing import Dict, List
    from dennis.core.hash import canonical_hash

    plan = json.loads(plan_path.read_text(encoding="utf-8"))    

    payload_hash = canonical_hash(plan)
    payload_hash_short = payload_hash[:12]

    changes = plan.get("changes", [])
    patches = plan.get("patches", {})

    helpers = [
        ch for ch in changes
        if ch.get("type") == "helper"
    ]
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
    # PREVIEW MODE (default)
    # --------------------------------------

    if confirm is None:
        print("\n[Dennis] PREVIEW MODE — no changes will be applied\n")

        print(f"Payload hash: {payload_hash}")
        print(f"Short hash:   {payload_hash_short}")

        print(f"\nTotal changes: {len(changes)}")
        helper_changes = [
            ch for ch in changes
            if ch.get("type") == "helper"
        ]

        print(f"Helpers:       {len(helper_changes)}")

        print("\nTo apply this artifact, run:\n")
        print(f"  dennis apply {plan_path} --confirm {payload_hash_short}\n")

        return 0
    
    # --------------------------------------
    # CONFIRMATION CHECK
    # --------------------------------------

    if not payload_hash.startswith(confirm):
        print("\n[Dennis] ERROR: Confirmation hash mismatch\n")
        print(f"Expected prefix: {payload_hash_short}")
        print(f"Received:        {confirm}\n")
        raise SystemExit(1)

    # --------------------------------------
    # Helper resolution (FINAL MODEL)
    # --------------------------------------

    required_helpers = {
        ch.get("helper_id")
        for ch in changes
        if ch.get("type") == "helper"
    }

    available_helpers = set()

    for ch in changes:
        if ch.get("type") == "helper":

            helper_ref = ch.get("helper_ref")
            helper_name = Path(helper_ref).name if helper_ref else None

            # check in ./helpers
            if helper_name:
                helper_path = Path("helpers") / helper_name
                if helper_path.exists():
                    available_helpers.add(ch.get("helper_id"))

    missing = required_helpers - available_helpers

    if missing:
        print("\n[Dennis] ERROR: Missing required helpers.\n")
        print(f"  Required:  {sorted(required_helpers)}")
        print(f"  Available: {sorted(available_helpers)}")
        print(f"  Missing:   {sorted(missing)}\n")
        raise SystemExit(1)
    
    # --------------------------------------
    # Apply helper patches (FINAL MODEL)
    # --------------------------------------

    helpers = sorted(helpers, key=lambda h: (h.get("file"), h.get("line")))
    inserted_helpers = set()

    for h in helpers:

        helper_id = h.get("helper_id") or h.get("id")

        if helper_id in inserted_helpers:
            continue

        target_file = Path(h.get("file"))
        insert_line = h.get("line") or 1
        helper_ref = h.get("helper_ref")

        if not helper_ref:
            raise SystemExit(f"[Dennis] ERROR: helper missing helper_ref: {h}")

        helper_name = Path(helper_ref).name
        helper_path = Path("helpers") / helper_name

        if not helper_path.exists():
            raise SystemExit(f"[Dennis] ERROR: Helper file not found: {helper_path}")

        if not target_file.exists():
            raise SystemExit(f"[Dennis] ERROR: Target file not found: {target_file}")

        print(f"[Dennis] Injecting helper → {helper_path} into {target_file}:{insert_line}")

        helper_lines = helper_path.read_text(encoding="utf-8").splitlines()
        if not helper_lines:
            raise SystemExit(f"[Dennis] ERROR: Empty helper: {helper_id}")
        
        lines = target_file.read_text(encoding="utf-8").splitlines()

        # Idempotency check
        start_marker = f"# >>> DENNIS HELPER START: {helper_id}"

        if any(start_marker in line for line in lines):
            print(f"[Dennis] Skipping helper {helper_id} (already present)")
            continue

        wrapped = [
            f"# >>> DENNIS HELPER START: {helper_id}",
            *helper_lines,
            f"# <<< DENNIS HELPER END: {helper_id}",
        ]

        idx = max(0, min(len(lines), insert_line - 1))
        new_lines = lines[:idx] + wrapped + lines[idx:]

        if not dry_run:
            target_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

        inserted_helpers.add(helper_id)
        log["changes_applied"] += 1



    # --------------------------------------
    # Apply string transformations
    # --------------------------------------

    changes_by_file: Dict[str, List[dict]] = {}

    print(f"\nApplying plan: {plan_path}")
    print(f"Total changes in plan: {len(changes)}\n")

    for change in changes:

        change_type = change.get("type")

        # --------------------------------------
        # Handle helper removal FIRST
        # --------------------------------------
        if change_type == "helper_remove":

            file_path = Path(change.get("file"))
            helper_id = change.get("helper_id")

            if not file_path.exists():
                continue

            lines = file_path.read_text(encoding="utf-8").splitlines()

            start_marker = f"# >>> DENNIS HELPER START: {helper_id}"
            end_marker = f"# <<< DENNIS HELPER END: {helper_id}"

            new_lines = []
            inside = False

            for line in lines:
                if start_marker in line:
                    inside = True
                    continue
                if end_marker in line:
                    inside = False
                    continue
                if not inside:
                    new_lines.append(line)

            file_path.write_text("\n".join(new_lines), encoding="utf-8")

            print(f"[Dennis] Removed helper → {file_path}")

            continue  # IMPORTANT

        # --------------------------------------
        # Skip helper (already handled)
        # --------------------------------------
        if change_type == "helper":
            continue

        # --------------------------------------
        # Only process transforms
        # --------------------------------------
        if "original" not in change:
            continue
        
        changes_by_file.setdefault(change["file"], []).append(change)

    total = 0

    for file_name, file_changes in changes_by_file.items():

        file_changes.sort(key=lambda c: c["line"])
        file_path = Path(file_name)

        if not file_path.exists():
            raise SystemExit(f"[Dennis] File not found during apply: {file_path}")

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