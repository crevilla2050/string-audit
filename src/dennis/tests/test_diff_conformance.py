import json
from pathlib import Path
from dennis.dex.canonical_diff import (
    generate_observed_diff_directories,
    normalize_to_dennis_diff_v1,
    diff_hash
)

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def test_case(case_dir):
    source = case_dir / "input_a"
    target = case_dir / "input_b"
    expected = load_json(case_dir / "expected.json")
    expected_hash = (case_dir / "expected.hash").read_text().strip()

    result = generate_observed_diff_directories(source, target)
    canonical = normalize_to_dennis_diff_v1(result)
    actual_hash = diff_hash(canonical)

    assert canonical == expected, f"Mismatch in {case_dir.name}"
    assert actual_hash == expected_hash, f"Hash mismatch in {case_dir.name}"