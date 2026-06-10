import json
from pathlib import Path

from datetime import (
    datetime,
    timezone
)

def timestamp():
    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%dT%H-%M-%S"
    )

def save_json(
    data,
    path
):
    """
    Save JSON using deterministic
    formatting.
    """

    Path(path).write_text(
        json.dumps(
            data,
            indent=4,
            sort_keys=True
        ),
        encoding="utf-8"
    )

def save_observation_index(
    index,
    output_dir
):
    """
    Save architecture observation
    index.
    """

    ts = timestamp()

    path = Path(
        output_dir
    ) / (
        f"architecture-index-{ts}.json"
    )

    save_json(
        index,
        path
    )

    return str(path)

def save_evidence_store(
    evidence,
    output_dir
):
    """
    Save architecture evidence
    store.
    """

    ts = timestamp()

    path = Path(
        output_dir
    ) / (
        f"architecture-evidence-{ts}.json"
    )

    save_json(
        evidence,
        path
    )

    return str(path)