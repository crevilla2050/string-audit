from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime, timezone


def canonicalize_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a plan into Dennis Canonical Plan v1.

    This function:
    - Stabilizes meta envelope
    - Normalizes null vs empty
    - Enforces deterministic field presence
    """

    changes = [_canonicalize_change(c) for c in plan.get("changes", [])]

    canonical = {
        "meta": _canonicalize_meta(plan.get("meta", {})),
        "changes": changes,
    }

    return canonical


def _canonicalize_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tool": "dennis",
        "version": "0.1",
        # preserve generated_at if present, else generate deterministic UTC
        "generated_at": meta.get(
            "generated_at",
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        ),
    }


def _canonicalize_change(c: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "file": c["file"],
        "line": int(c["line"]),
        "original": c["original"],
        "replacement": c["replacement"],
        "token": c.get("token") or None,
    }