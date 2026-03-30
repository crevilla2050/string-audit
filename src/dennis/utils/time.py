# src/dennis/utils/time.py
from datetime import datetime, timezone


def iso_timestamp_filename():
    """
    Returns ISO timestamp safe for filenames.
    Example: 2026-03-01T14-22-31Z
    """
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace(":", "-")
        .replace("+00:00", "Z")
    )