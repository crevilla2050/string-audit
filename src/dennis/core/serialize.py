"""
Deterministic JSON serialization utilities for Dennis.

Goals:
- Stable ordering
- Reproducible output
- Clean diffs
- No hidden entropy
"""

import json
from typing import Any, IO
from collections import OrderedDict

CHANGE_FIELD_ORDER = [
    "id",
    "type",          # ← ADDED
    "file",
    "line",
    "original",
    "replacement",
    "token",
    "helper_id",     # ← ADDED
    "helper_ref",    # ← ADDED
    "helper_source", # ← ADDED
    "confidence",
    "notes",
]

META_FIELD_ORDER = [
    "tool",
    "version",
    "generated_at",
]


def canonical_change(change: dict) -> dict:
    ordered = OrderedDict()
    for key in CHANGE_FIELD_ORDER:
        if key in change:
            ordered[key] = change[key]
    return ordered


def canonical_meta(meta: dict) -> dict:
    ordered = OrderedDict()
    for key in META_FIELD_ORDER:
        if key in meta:
            ordered[key] = meta[key]
    return ordered


def canonicalize_plan(plan: dict) -> dict:
    out = OrderedDict()

    if "meta" in plan:
        out["meta"] = canonical_meta(plan["meta"])

    if "changes" in plan:
        out["changes"] = [canonical_change(c) for c in plan["changes"]]

    # Preserve patches section if present
    if "patches" in plan:
        out["patches"] = plan["patches"]

    return out


def dump_json(plan: dict, fh):
    canonical = canonicalize_plan(plan)
    json.dump(canonical, fh, indent=2, ensure_ascii=False)
    fh.write("\n")

def dumps_json(data: Any) -> str:
    """
    Deterministic JSON string version.
    """
    return json.dumps(
        data,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"  # POSIX-friendly newline