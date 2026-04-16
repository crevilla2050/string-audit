import os
import json
import tempfile
import shutil

CONFIG_DIR = os.path.expanduser("~/.dennis")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {}

    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data: dict):
    """
    Safely write config to disk using atomic write.
    """

    ensure_config_dir()

    # ----------------------------------------
    # Write to temp file first (atomic write)
    # ----------------------------------------
    fd, temp_path = tempfile.mkstemp(dir=CONFIG_DIR)

    try:
        current = load_config()
        current.update(data)

        with os.fdopen(fd, "w") as tmp:
            json.dump(current, tmp, indent=2)

        # ----------------------------------------
        # Atomic replace
        # ----------------------------------------
        shutil.move(temp_path, CONFIG_PATH)

    finally:
        # Cleanup in case of failure
        if os.path.exists(temp_path):
            os.remove(temp_path)