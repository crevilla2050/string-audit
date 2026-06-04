import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import shutil
import zipfile

from dennis.core.hash import canonical_hash


SAFE_PATTERNS = [
    re.compile(r'print\((["\'])(.+?)\1\)'),
    re.compile(r'raise\s+(\w+)\((["\'])(.+?)\2\)'),
    re.compile(r'logging\.(info|warning|error|debug)\((["\'])(.+?)\2\)'),
]

HELPER_START = "# >>> DENNIS HELPER START: {helper_id}"
HELPER_END   = "# <<< DENNIS HELPER END: {helper_id}"

ARTIFACT_PATHS = [
    "payload",
    "signatures",
    "manifest.json",
    "rehydrated-plan.json",
    ".dennis",
]
def create_artifact_bundle(payload_hash_short: str):

    cwd = Path.cwd()

    # --------------------------------------
    # staging dir
    # --------------------------------------

    staging = cwd / ".dennis_staging"

    if staging.exists():
        shutil.rmtree(staging)

    staging.mkdir()

    # --------------------------------------
    # copy artifacts into staging
    # --------------------------------------

    for name in ARTIFACT_PATHS:
        src = cwd / name

        if not src.exists():
            continue

        dst = staging / name

        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    # --------------------------------------
    # create zip
    # --------------------------------------

    now = datetime.utcnow()
    timestamp = now.strftime("%Y-%m-%dT%H-%M-%S")
    short12 = payload_hash_short[:12]

    cache_dir = Path.home() / ".dennis" / "artifacts_cache" / f"{now.year}" / f"{now.month:02d}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    staging = Path.cwd() / ".dennis_staging"

    zip_path = cache_dir / f"artifact_{timestamp}_{short12}.zip"

    bundle_meta = {
        "payload_hash": payload_hash_short,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

    (staging / "bundle.json").write_text(json.dumps(bundle_meta, indent=2))
    

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        from zipfile import ZipInfo

        seen = set()

        for file in staging.rglob("*"):

            if file.is_dir():
                continue

            arcname = str(file.relative_to(staging))

            # 🔥 prevent duplicates deterministically
            if arcname in seen:
                continue

            if ".dennis" in file.parts:
                continue

            seen.add(arcname)

            data = file.read_bytes()

            zinfo = ZipInfo(arcname)
            zinfo.date_time = (1980, 1, 1, 0, 0, 0)

            z.writestr(zinfo, data)

            # --------------------------------------
            # cleanup staging
            # --------------------------------------

    shutil.rmtree(staging)

    print(f"[Dennis] Artifact bundle created → {zip_path}")

    return zip_path


def is_artifact(path: Path) -> bool:
    return path.name in ARTIFACT_PATHS

def get_artifact_cache_dir():
    now = datetime.utcnow()
    base = Path.home() / ".dennis" / "artifacts_cache"
    path = base / f"{now.year}" / f"{now.month:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path

def load_dictionary(path: Path) -> Dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {v: k for k, v in data.items()}

def register_artifact(path, new_path):
    import json

    registry = Path.home() / ".dennis" / "artifacts_registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)

    if registry.exists():
        data = json.loads(registry.read_text())
    else:
        data = {}

    data[str(path)] = {
        "isolated": str(new_path),
        "generated_at": datetime.utcnow().isoformat()
    }

    registry.write_text(json.dumps(data, indent=2))

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


def get_helper_cache_dir():
    now = datetime.utcnow()
    base = Path.home() / ".dennis" / "helpers_cache"
    path = base / f"{now.year}" / f"{now.month:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def register_isolated_helper(helper_id, original_path, new_path):

    registry_path = Path.home() / ".dennis" / "helpers_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    if registry_path.exists():
        data = json.loads(registry_path.read_text())
    else:
        data = {}

    data[helper_id] = {
        "original": str(original_path),
        "isolated": str(new_path),
        "generated_at": datetime.utcnow().isoformat()
    }

    registry_path.write_text(json.dumps(data, indent=2))


# --------------------------------------------------------
# MAIN PLAN APPLY
# --------------------------------------------------------

def apply_plan(
    plan_path: Path,
    dry_run: bool = False,
    confirm: str | None = None,
    helper_mode: str = "keep",
    artifact_policy: str = "keep"
) -> int:

    import json
    import datetime
    from pathlib import Path
    from typing import Dict, List
    from dennis.core.hash import canonical_hash

    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    payload_hash = canonical_hash(plan)
    payload_hash_short = payload_hash[:12]

    changes = plan.get("changes", [])

    helpers = [ch for ch in changes if ch.get("type") == "helper"]

    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    project_name = Path.cwd().name
    log_path = Path.cwd() / f"{project_name}-{timestamp}.json"

    log = {
        "plan": str(plan_path),
        "generated_at": timestamp,
        "changes_total": len(changes),
        "changes_applied": 0,
        "warnings": [],
        "skipped": []
    }

    # --------------------------------------
    # PREVIEW MODE
    # --------------------------------------

    if confirm is None:
        print("\n[Dennis] PREVIEW MODE — no changes will be applied\n")
        print(f"Payload hash: {payload_hash}")
        print(f"Short hash:   {payload_hash_short}")
        print(f"\nTotal changes: {len(changes)}")
        print(f"Helpers:       {len(helpers)}")
        print("\nTo apply this artifact, run:\n")
        print(f"  dennis apply {plan_path} --confirm {payload_hash_short}\n")
        return 0

    # --------------------------------------
    # CONFIRMATION CHECK
    # --------------------------------------

    if not payload_hash.startswith(confirm):
        print("\n[Dennis] ERROR: Confirmation hash mismatch\n")
        raise SystemExit(1)

    # --------------------------------------
    # HELPER RESOLUTION
    # --------------------------------------

    required_helpers = {ch.get("helper_id") for ch in helpers}
    available_helpers = set()

    for ch in helpers:
        helper_ref = ch.get("helper_ref")
        if helper_ref:
            helper_name = Path(helper_ref).name
            helper_path = Path("helpers") / helper_name
            if helper_path.exists():
                available_helpers.add(ch.get("helper_id"))

    missing = required_helpers - available_helpers
    if missing:
        raise SystemExit(f"[Dennis] Missing helpers: {missing}")

    # --------------------------------------
    # APPLY HELPERS (INSERT)
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

        helper_path = Path("helpers") / Path(helper_ref).name

        lines = target_file.read_text(encoding="utf-8").splitlines()

        start_marker = HELPER_START.format(helper_id=helper_id)

        if any(line.strip() == start_marker for line in lines):
            print(f"[Dennis] Skipping helper {helper_id} (already present)")
            continue

        helper_lines = helper_path.read_text(encoding="utf-8").splitlines()

        wrapped = [
            HELPER_START.format(helper_id=helper_id),
            *helper_lines,
            HELPER_END.format(helper_id=helper_id)
        ]

        idx = max(0, min(len(lines), insert_line - 1))
        new_lines = lines[:idx] + wrapped + lines[idx:]

        if not dry_run:
            target_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

        inserted_helpers.add(helper_id)
        log["changes_applied"] += 1

    # --------------------------------------
    # APPLY CHANGES
    # --------------------------------------

    changes_by_file: Dict[str, List[dict]] = {}

    print(f"\nApplying plan: {plan_path}")
    print(f"Total changes in plan: {len(changes)}\n")

    for change in changes:

        change_type = change.get("type")

        # --------------------------------------
        # HELPER REMOVE
        # --------------------------------------

        if change_type == "helper_remove":

            target_file = Path(change.get("file"))
            helper_id = change.get("helper_id")
            helper_ref = change.get("helper_ref")

            lines = target_file.read_text(encoding="utf-8").splitlines()

            start_marker = HELPER_START.format(helper_id=helper_id)
            end_marker   = HELPER_END.format(helper_id=helper_id)

            new_lines = []
            inside = False
            removed = False

            for line in lines:

                if line.strip() == start_marker:
                    inside = True
                    removed = True
                    continue

                if line.strip() == end_marker:
                    inside = False
                    continue

                if not inside:
                    new_lines.append(line)

            if removed:
                print(f"[Dennis] Removed helper → {target_file}")

                if not dry_run:
                    target_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

                log["changes_applied"] += 1

            # ---- helper lifecycle ----

            if helper_ref:
                helper_path = Path("helpers") / Path(helper_ref).name

                print(f"DEBUG helper_ref: {helper_ref}")
                print(f"DEBUG helper_mode: {helper_mode}")

                if helper_mode == "remove":
                    
                    if helper_path.exists():
                        print(f"[Dennis] Removing helper file → {helper_path}")
                        if not dry_run:
                            helper_path.unlink()

                elif artifact_policy == "isolate":

                    print("[Dennis] Creating artifact bundle (isolate mode)")

                    if not dry_run:
                        bundle_path = create_artifact_bundle(payload_hash_short)

                        # after successful bundle → remove originals
                        for name in ARTIFACT_PATHS:
                            path = Path.cwd() / name

                            if not path.exists():
                                continue

                            print(f"[Dennis] Removing artifact after bundle → {path}")

                            if path.is_dir():
                                shutil.rmtree(path)
                            else:
                                path.unlink()

            continue

        # --------------------------------------
        # STRING TRANSFORMS
        # --------------------------------------

        if "original" not in change:
            continue

        changes_by_file.setdefault(change["file"], []).append(change)

    total = 0

    for file_name, file_changes in changes_by_file.items():

        file_changes.sort(key=lambda c: c["line"])
        file_path = Path(file_name)

        lines = file_path.read_text(encoding="utf-8").splitlines()
        normalized = [l.strip() for l in lines]

        for change in file_changes:

            expected = change["original"].strip()
            replacement = change["replacement"]

            for i, line in enumerate(normalized):
                if line == expected:
                    print(f"Applying change → {file_path}:{i+1}")
                    lines[i] = replacement
                    normalized[i] = replacement.strip()
                    total += 1
                    break

        if not dry_run:
            file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # --------------------------------------
    # ARTIFACT POLICY
    # --------------------------------------

    if artifact_policy != "keep":

        cwd = Path.cwd()

        for item in cwd.iterdir():

            if not is_artifact(item):
                continue

            # -----------------------------
            # CLEAN
            # -----------------------------

            if artifact_policy == "clean":

                print(f"[Dennis] Removing artifact → {item}")

                if not dry_run:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()

            # -----------------------------
            # ISOLATE
            # -----------------------------

            elif artifact_policy == "isolate":

                cache_dir = get_artifact_cache_dir()
                target = cache_dir / item.name

                # avoid overwrite
                if target.exists():
                    import time
                    target = cache_dir / f"{item.stem}_{int(time.time())}{item.suffix}"

                print(f"[Dennis] Isolating artifact → {item} → {target}")

                if not dry_run:
                    shutil.move(str(item), str(target))
                    register_artifact(payload_hash_short, bundle_path)


    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")

    print(f"\nApplied {total} changes.")
    print(f"Log written → {log_path}\n")

    return total