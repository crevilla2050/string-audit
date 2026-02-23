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


def dump_json(data: Any, fp: IO[str]) -> None:
    """
    Write deterministic JSON to a file-like object.

    Guarantees:
    - Sorted keys
    - 2-space indentation
    - Unix newlines
    - Trailing newline (POSIX-friendly)
    """
    json.dump(
        data,
        fp,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )
    fp.write("\n")  # POSIX-friendly newline


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