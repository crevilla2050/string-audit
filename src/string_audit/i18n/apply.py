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
    # invert: text -> key
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

        # Replace literal with t("TOKEN")
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
