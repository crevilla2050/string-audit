import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .apply import load_dictionary, iter_python_files, replace_line
from string_audit.detectors.hardcoded_strings import HardcodedStringDetector
from string_audit.i18n.generator import build_dictionary, write_en_json

def load_helper(helper_path: Path) -> Dict:
    """
    Load helper file and return helper patch structure.
    """
    lines = helper_path.read_text(encoding="utf-8").splitlines()

    h = hashlib.sha256()
    h.update("\n".join(lines).encode("utf-8"))

    return {
        "id": helper_path.stem,
        "hash": h.hexdigest(),
        "lines": lines,
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
    helpers: List[Dict] | None = None
) -> Dict:

    # --------------------------------------------------
    # Ensure dictionary file exists
    # --------------------------------------------------

    if not dict_path.exists():
        print(f"[Dennis] Dictionary not found. Creating new dictionary: {dict_path}")
        dict_path.write_text("{}\n", encoding="utf-8")

    mapping = load_dictionary(dict_path)

    # --------------------------------------------------
    # Bootstrap dictionary if empty
    # --------------------------------------------------

    if not mapping:

        print("[Dennis] Dictionary empty. Scanning project for strings...")

        detector = HardcodedStringDetector()
        discovered: List[str] = []

        for py_file in iter_python_files(root):
            lines = py_file.read_text(encoding="utf-8", errors="ignore").splitlines()

            findings = detector.scan_file(py_file, lines)

            for f in findings:
                if f.text:
                    discovered.append(f.text)

        if discovered:
            mapping = build_dictionary(discovered)
            write_en_json(mapping, dict_path)

            print(f"[Dennis] Dictionary generated → {dict_path}")
            print("[Dennis] Continuing with plan generation...")

    # --------------------------------------------------
    # Prepare replacement mapping (string → token)
    # --------------------------------------------------

    reverse_mapping = mapping

    changes: List[Dict] = []

    # --------------------------------------------------
    # Generate transformation plan
    # --------------------------------------------------

    for py_file in iter_python_files(root):
        file_hash = sha256_file(py_file)

        lines = py_file.read_text(encoding="utf-8", errors="ignore").splitlines()

        for idx, line in enumerate(lines, start=1):

            new_line = line
            token = None

            for text, key in reverse_mapping.items():

                if text in line:

                    # handle double quotes
                    if f'"{text}"' in line:
                        new_line = line.replace(
                            f'"{text}"',
                            f'messages["{key}"]'
                        )

                    # handle single quotes
                    elif f"'{text}'" in line:
                        new_line = line.replace(
                            f"'{text}'",
                            f'messages["{key}"]'
                        )

                    else:
                        continue

                    token = key
                    break

            if new_line != line:

                changes.append(
                    {
                        "file": str(py_file),
                        "line": idx,
                        "file_hash": file_hash,
                        "original": line,
                        "replacement": new_line,
                        "token": token,
                    }
                )
    patches = {}

    if helpers:
        patches["helpers"] = helpers

    plan = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project_root": str(root.resolve()),
            "dictionary": str(dict_path),
        },
        "changes": changes,
    }

    if patches:
        plan["patches"] = patches

    return plan


def write_plan(plan: Dict, output: Path) -> None:
    output.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def default_plan_filename() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    return f"dennis-plan-{ts}.json"