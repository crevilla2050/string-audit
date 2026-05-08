import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .apply import load_dictionary, iter_python_files, replace_line
from dennis.detectors.hardcoded_strings import HardcodedStringDetector
from dennis.i18n.generator import build_dictionary, write_en_json
from dennis.scanner import scan_directory
from dennis.plugins import PLUGINS
from dennis.utils import iter_files

import subprocess

LANG_EXTENSIONS = {
    "python": [".py"],
    "php": [".php"],
    "javascript": [".js"],
    "html": [".html"],
    "css": [".css"],
    "sql": [".sql"],
    "java": [".java"],
    "csharp": [".cs"],
    "ruby": [".rb"],
    "go": [".go"],
    "rust": [".rs"],
    "text": [".txt"],
    "office XML": [".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp"],
}

def get_git_changed_files(root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "diff", "--no-color", "--patch", "--name-only"],
            cwd=root,
            capture_output=True,
            check=True
        )

        files = [
            root / line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]

        return [f for f in files if f.exists()]

    except Exception:
        print("[Dennis] WARNING: git diff failed, falling back to full scan")
        return []
    

def load_helper(helper_path: Path) -> Dict:
    """
    Load helper file and return helper patch structure.
    """
    lines = helper_path.read_text(encoding="utf-8").splitlines()

    helper_content = "\n".join(lines).encode("utf-8")

    helper_hash = hashlib.sha256(helper_content).hexdigest()
    helper_id = helper_hash[:12]

    helper_name = f"helper_{helper_id}.py"

    return {
        "id": helper_id,
        "hash": helper_hash,
        "path": f"helpers/{helper_name}",
    }

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def generate_plan(
    root: Path,
    dict_path: Path,
    helpers: List[Dict] | None = None,
    git_mode: str = "tracked",
    lang: str = "python",
    exclude_langs: set[str] | None = None
) -> Dict:

    # --------------------------------------------------
    # Ensure dictionary file exists
    # --------------------------------------------------
    plugin = PLUGINS.get(lang, PLUGINS["python"])

    if not dict_path.exists():
        print(f"[Dennis] Dictionary not found. Creating new dictionary: {dict_path}")
        dict_path.write_text("{}\n", encoding="utf-8")

    mapping = load_dictionary(dict_path)

    # --------------------------------------------------
    # Bootstrap dictionary if empty
    # --------------------------------------------------

    if not mapping:

        print("[Dennis] Dictionary empty. Scanning project for dennis to work with...")

        findings = scan_directory(root, git_mode=git_mode)

        discovered = [
            f.text
            for f in findings
            if getattr(f, "text", None)
        ]

        if discovered:
            mapping = build_dictionary(discovered)

            # ----------------------------------------
            # DEBUG (optional but useful)
            # ----------------------------------------
            # # print(f"[DEBUG] Raw dictionary entries: {len(mapping)}")

            # ----------------------------------------
            # WRITE RAW DICTIONARY
            # ----------------------------------------
            write_en_json(mapping, dict_path)

            print(f"[Dennis] Dictionary generated → {dict_path}")

            # ----------------------------------------
            # CLEAN SECOND PASS
            # ----------------------------------------
            from dennis.utils import (
                apply_all_filters,
                cleaned_filename    
            )

            cleaned = apply_all_filters(mapping)

            # print(f"[DEBUG] Cleaned dictionary entries: {len(cleaned)}")

            clean_path = cleaned_filename(dict_path)

            write_en_json(cleaned, clean_path)

            print(f"[Dennis] Cleaned dictionary → {clean_path}")
            print("[Dennis] Continuing with plan generation...")

            # ----------------------------------------
            # IMPORTANT: Use CLEANED mapping going forward
            # ----------------------------------------
            mapping = cleaned

    # --------------------------------------------------
    # Prepare replacement mapping (string → token)
    # --------------------------------------------------

    reverse_mapping = {v: k for k, v in mapping.items()}
    # print("[DEBUG] reverse_mapping:", reverse_mapping)

    changes: List[Dict] = []

    # --------------------------------------------------
    # Generate transformation plan
    # --------------------------------------------------

    findings = scan_directory(root, git_mode=git_mode)

    # print(f"[DEBUG] Total findings: {len(findings)}")
    for f in findings[:5]:  # first 5
        # print(f"[DEBUG] Finding: {f.file}:{f.line} '{f.text}'")

    # Decouple scanning from transformation: process all code files
    for file_path in iter_files(root, git_mode=git_mode):

        if exclude_langs:
            ext = file_path.suffix.lower()
            if any(ext in LANG_EXTENSIONS.get(lang_name, []) for lang_name in exclude_langs):
                # print(f"[DEBUG] Skipping {file_path} due to exclude_langs")
                continue

        if file_path.suffix.lower() == ".json":
            # print(f"[DEBUG] Skipping JSON {file_path}")
            continue

        # Only process code files
        if file_path.suffix.lower() not in [".py"]:  # add other langs as needed
            continue

        # print(f"[DEBUG] Processing {file_path}")

        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        file_hash = sha256_file(file_path)

        for idx, line in enumerate(lines, start=1):
            if not line or not line.strip():
                # print(f"[DEBUG] Empty line {idx} for {file_path}")
                continue

            # print(f"[DEBUG] Transforming line {idx}: {line}")
            new_line, token = plugin.transform_line(line, reverse_mapping)

            # print(f"[DEBUG] Transform result: token={token}, new_line={repr(new_line)}")

            if token and new_line and new_line != line:
                # print(f"[DEBUG] Adding change for {file_path}:{idx}")
                try:
                    file_abs = file_path.resolve()
                    root_abs = root.resolve()
                    rel_path = str(file_abs.relative_to(root_abs))
                except (ValueError, OSError):
                    rel_path = str(file_path)

                changes.append({
                    "file": rel_path,
                    "line": idx,
                    "file_hash": file_hash,
                    "original": line,
                    "replacement": new_line,
                    "token": token,
                })
    
    # --------------------------------------------------
    # Link helpers to changes (NEW)
    # --------------------------------------------------
    # print("[DEBUG] helpers received:", helpers)
    
    if helpers:
        # print("[DEBUG] entering helper append block")
        for h in helpers:
            helper_change = {
                "type": "helper",
                "helper_id": h.get("id") or h.get("helper_id"),
                "file": h.get("file"),
                "line": h.get("line"),
                "helper_ref": h.get("helper_ref") or h.get("path"),
                "helper_source": h.get("helper_source") or h.get("helper"),
            }
            # print("[DEBUG] appending helper:", helper_change)
            changes.append(helper_change)
            # print("[DEBUG] helper change added:", changes[-1])

    plan = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project_root": str(root.resolve()),
            "dictionary": str(dict_path),
        },
        "changes": changes,
    }

    return plan


def write_plan(plan: Dict, output: Path) -> None:
    output.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def default_plan_filename() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    return f"dennis-plan-{ts}.json"