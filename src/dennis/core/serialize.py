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

def canonical_plan_projection(plan: dict) -> dict:
    """
    Return a complete normalized projection of a plan.

    Preserves all metadata fields while canonicalizing changes.
    Does not modify the original plan.
    """
    out = OrderedDict()

    if "meta" in plan:
        out["meta"] = OrderedDict(
            sorted(plan["meta"].items())
        )

    if "changes" in plan:
        out["changes"] = [
            OrderedDict(
                [
                    (key, change[key])
                    for key in CHANGE_FIELD_ORDER
                    if key in change
                ]
                + [
                    (key, change[key])
                    for key in sorted(change)
                    if key not in CHANGE_FIELD_ORDER
                ]
            )
            for change in plan["changes"]
        ]

    if "patches" in plan:
        out["patches"] = plan["patches"]

    return out


def canonical_tsa_projection(plan: dict) -> dict:
    """
    Return the plan projection used for TSA digest calculation.

    Excludes timestamps and timestamp evidence while retaining
    all other plan metadata and semantic content.
    """
    projection = canonical_plan_projection(plan)

    meta = projection.get("meta", {})

    excluded_fields = {
        "generated_at",
        "plan_created_at",
        "tsa_canonical_time",
        "timestamp_report",
        "timestamp_evidence",
        "timestamp_diagnostics",
    }

    projection["meta"] = OrderedDict(
        (key, value)
        for key, value in meta.items()
        if key not in excluded_fields
    )

    return projection


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