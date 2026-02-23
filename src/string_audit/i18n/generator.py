import json
import re
from pathlib import Path
from typing import Dict, List


def normalize_key(text: str) -> str:
    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)

    # Collapse whitespace
    text = re.sub(r"\s+", "_", text.strip())

    return text.upper()


def load_findings(path: Path) -> List[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [item["text"] for item in data if item.get("text")]


def build_dictionary(strings: List[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}

    for text in strings:
        key = normalize_key(text)

        # Handle collisions deterministically
        original_key = key
        counter = 2
        while key in mapping and mapping[key] != text:
            key = f"{original_key}_{counter}"
            counter += 1

        mapping[key] = text

    return dict(sorted(mapping.items()))

def write_en_json(mapping: Dict[str, str], output: Path) -> None:
    output.write_text(
        json.dumps(mapping, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_en_js(mapping: Dict[str, str], output: Path) -> None:
    lines = ["export const en = {"]

    for key, value in mapping.items():
        escaped = value.replace('"', '\\"')
        lines.append(f'  {key}: "{escaped}",')

    lines.append("};\n")

    output.write_text("\n".join(lines), encoding="utf-8")

def load_existing_dict(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return {}

def merge_dictionaries(
    base: Dict[str, str],
    *existing_dicts: Dict[str, str],
) -> Dict[str, str]:
    merged = dict(base)

    for existing in existing_dicts:
        for key, value in existing.items():
            # Preserve existing keys
            if key not in merged:
                merged[key] = value
            # If key exists, prefer existing value (non-destructive)
            # Do nothing

    return dict(sorted(merged.items()))
