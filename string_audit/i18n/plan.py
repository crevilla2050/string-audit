import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .apply import load_dictionary, iter_python_files, replace_line


def generate_plan(root: Path, dict_path: Path) -> Dict:
    mapping = load_dictionary(dict_path)
    changes: List[Dict] = []

    for py_file in iter_python_files(root):
        lines = py_file.read_text(encoding="utf-8", errors="ignore").splitlines()

        for idx, line in enumerate(lines, start=1):
            new_line = replace_line(line, mapping)
            if new_line != line:
                changes.append(
                    {
                        "file": str(py_file),
                        "line": idx,
                        "original": line,
                        "replacement": new_line,
                        "token": mapping.get(line.strip().strip('"').strip("'"), None),
                    }
                )

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project_root": str(root.resolve()),
            "dictionary": str(dict_path),
        },
        "changes": changes,
    }


def write_plan(plan: Dict, output: Path) -> None:
    output.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

def default_plan_filename() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    return f"string-audit-plan-{ts}.json"
