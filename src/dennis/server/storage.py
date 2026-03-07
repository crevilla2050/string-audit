from pathlib import Path

ARTIFACT_ROOT = Path("/var/lib/dennis/artifacts")


def artifact_path(hash_value: str) -> Path:
    d1 = hash_value[0:2]
    d2 = hash_value[2:4]
    return ARTIFACT_ROOT / d1 / d2 / f"{hash_value}.dex"


def ensure_artifact_dirs(hash_value: str):
    path = artifact_path(hash_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path