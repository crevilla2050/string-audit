# core/rehydrate.py
from datetime import datetime
from .sort import sort_changes
from pathlib import Path
import json
import tarfile
import tempfile


def rehydrate_from_csv(changes):
    """
    Reconstruct a minimal plan structure from CSV changes.

    This function is intentionally NON-canonical.
    It produces a projection-level plan that must be
    canonicalized by forge.canonical layers.
    
    This function must remain entropy-free.
    Do not inject timestamps or version fields here.
    Canonical layers handle identity.
    """

    return {
        "meta": {
            # Canonicalizer will fill these deterministically
            "generated_at": None,
            "source": "csv",
        },
        "changes": sort_changes(changes),
    }


def rehydrate(dex_path, output_dir: Path):
    """
    Reconstruct filesystem from DEX artifact.
    v2:
        - If payload/files exists → copy directly
    v1:
        - Fallback to plan-based reconstruction
    """

    dex_path = Path(dex_path)

    if not dex_path.exists():
        raise FileNotFoundError(f"DEX not found: {dex_path}")

    # ----------------------------------------
    # Extract archive
    # ----------------------------------------

    with tarfile.open(dex_path, "r:gz") as tar:
        tar.extractall(output_dir)


    payload_dir = output_dir / "payload"
    files_dir = payload_dir / "files"
    plan_path = payload_dir / "plan.json"

    # ----------------------------------------
    # MODE: STATE (v2)
    # ----------------------------------------

    helpers_dir = payload_dir / "helpers"

    has_files = files_dir.exists() and any(p.is_file() for p in files_dir.rglob("*"))
    has_helpers = helpers_dir.exists() and any(helpers_dir.glob("*.py"))

    if has_files or has_helpers:

        print("[Dennis] Rehydrate mode: STATE")

        # ----------------------------------------
        # Copy files
        # ----------------------------------------

        for file_path in files_dir.rglob("*"):

            if not file_path.is_file():
                continue

            rel = file_path.relative_to(files_dir)
            target = output_dir / rel

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(file_path.read_bytes())

        print("[Dennis] Files restored")

        # ----------------------------------------
        # Normalize helpers location
        # ----------------------------------------

        helpers_src = payload_dir / "helpers"
        helpers_dst = output_dir / "helpers"

        # print(f"[DEBUG] helpers_src exists: {helpers_src.exists()}")

        if helpers_src.exists():

            print(f"[Dennis] Found helpers in payload → {helpers_src}")

            helpers_dst.mkdir(parents=True, exist_ok=True)

            copied = 0

            for f in helpers_src.glob("*.py"):
                # print(f"[DEBUG] copying {f}")
                target = helpers_dst / f.name
                target.write_bytes(f.read_bytes())
                copied += 1

            print(f"[Dennis] Helpers restored: {copied} → {helpers_dst}")

        else:
            print("[Dennis] No helpers found in payload")

        return

    # ----------------------------------------
    # MODE: PLAN (v1 fallback)
    # ----------------------------------------

    print("[Dennis] Rehydrate mode: PLAN")

    if not plan_path.exists():
        raise SystemExit("Invalid DEX: missing payload/plan.json")

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    changes = plan.get("changes", [])

    files = {}

    for change in changes:
        file_path = change["file"]

        if file_path not in files:
            files[file_path] = []

        lines = files[file_path]
        idx = change["line"] - 1

        while len(lines) <= idx:
            lines.append("")

        if change.get("type") == "delete":
            if idx < len(lines):
                lines.pop(idx)
            continue

        replacement = change.get("replacement")

        if replacement is not None:
            lines[idx] = replacement

    # ----------------------------------------
    # Write reconstructed files
    # ----------------------------------------

    for file_path, lines in files.items():
        full_path = output_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        full_path.write_text("\n".join(lines), encoding="utf-8")

    # ----------------------------------------
    # Apply helpers (first-class model)
    # ----------------------------------------

    helpers_dir = output_dir / "helpers"

    if helpers_dir.exists() and plan_path.exists():

        plan = json.loads(plan_path.read_text(encoding="utf-8"))

        helper_changes = [
            ch for ch in plan.get("changes", [])
            if ch.get("type") == "helper"
        ]

        # ----------------------------------------
        # Fallback (legacy safety)
        # ----------------------------------------

        if not helper_changes:

            print("[Dennis] Reconstructing helper changes from payload")

            for helper_file in helpers_dir.glob("*.py"):
                helper_id = helper_file.stem.replace("helper_", "")

                helper_changes.append({
                    "type": "helper",
                    "file": None,
                    "line": 1,
                    "helper_ref": f"helpers/{helper_file.name}",
                    "helper_id": helper_id,
                })

        # ----------------------------------------
        # APPLY HELPERS
        # ----------------------------------------

        for change in helper_changes:

            target_file = output_dir / change.get("file")

            if not change.get("file"):
                print(f"[Dennis] WARNING: helper {change['helper_id']} has no target file")
                continue

            if not target_file.exists():
                print(f"[Dennis] WARNING: target file missing → {change['file']}")
                continue

            # normalize helper_ref
            helper_ref = change["helper_ref"]
            helper_name = Path(helper_ref).name

            helper_path = helpers_dir / helper_name

            if not helper_path.exists():
                raise SystemExit(f"[Dennis] ERROR: Missing helper: {helper_path}")

            helper_lines = helper_path.read_text(encoding="utf-8").splitlines()
            target_lines = target_file.read_text(encoding="utf-8").splitlines()

            insert_line = change.get("line") or 1
            idx = max(0, min(len(target_lines), insert_line - 1))

            helper_id = change.get("helper_id", "unknown")

            wrapped = [
                f"# >>> DENNIS HELPER START: {helper_id}",
                *helper_lines,
                f"# <<< DENNIS HELPER END: {helper_id}",
            ]

            target_lines = target_lines[:idx] + wrapped + target_lines[idx:]

            target_file.write_text("\n".join(target_lines), encoding="utf-8")

    
