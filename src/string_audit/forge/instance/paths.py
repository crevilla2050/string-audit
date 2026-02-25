from pathlib import Path
import os

APP_NAME = "dennis"


def default_data_root() -> Path:
    # Respect XDG if available
    xdg = os.getenv("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / APP_NAME

    # Fallback
    return Path.home() / f".{APP_NAME}"


def plans_dir(root: Path | None = None) -> Path:
    root = root or default_data_root()
    return root / "plans"