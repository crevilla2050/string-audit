from pathlib import Path
import json

from dennis.dex.canonical_diff import (
    generate_observed_diff_directories,
    normalize_to_dennis_diff_v1,
    diff_hash,
)

def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def run_case(case_dir: Path):
    source = case_dir / "input_a"
    target = case_dir / "input_b"

    expected = load_json(case_dir / "expected.json")
    expected_hash = (case_dir / "expected.hash").read_text().strip()

    result = generate_observed_diff_directories(source, target)
    canonical = normalize_to_dennis_diff_v1(result)
    actual_hash = diff_hash(canonical)

    errors = []

    if canonical != expected:
        errors.append("canonical_mismatch")

    if actual_hash != expected_hash:
        errors.append("hash_mismatch")

    return errors, canonical, expected, actual_hash, expected_hash