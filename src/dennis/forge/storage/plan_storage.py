from pathlib import Path
import hashlib
import json
import os
import tempfile
from dennis.forge.hash.canonical import canonical_hash_bytes

class PlanStorage:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.plans_dir = self.root / "plans"

    # ---------- helpers ----------

    def _shard_path(self, hash_hex: str) -> Path:
        a = hash_hex[:2]
        b = hash_hex[2:4]
        return self.plans_dir / a / b / f"{hash_hex}.json"

    def _ensure_dirs(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)

    # ---------- public API ----------

    def put(self, canonical_json_bytes: bytes, expected_hash: str | None = None) -> str:
        h = canonical_hash_bytes(canonical_json_bytes)

        if expected_hash and expected_hash != h:
            raise ValueError("Hash mismatch during storage")

        path = self._shard_path(h)

        if path.exists():
            return h  # dedup

        self._ensure_dirs(path)

        with tempfile.NamedTemporaryFile(delete=False, dir=path.parent) as tmp:
            tmp.write(canonical_json_bytes)
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_name = tmp.name

        os.replace(temp_name, path)
        return h

    def get(self, hash_hex: str) -> bytes:
        path = self._shard_path(hash_hex)
        return path.read_bytes()

    def exists(self, hash_hex: str) -> bool:
        return self._shard_path(hash_hex).exists()

    def path(self, hash_hex: str) -> Path:
        return self._shard_path(hash_hex)

    def verify(self, hash_hex: str) -> bool:
        path = self._shard_path(hash_hex)
        if not path.exists():
            return False
        data = path.read_bytes()
        return hashlib.sha256(data).hexdigest() == hash_hex