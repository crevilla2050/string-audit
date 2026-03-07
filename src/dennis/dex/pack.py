"""
DEX Artifact Packer
Dennis v1

Creates deterministic .dex artifacts (tar.gz).
"""

import tarfile
import gzip
import io
import json
from pathlib import Path

from dennis.dex.manifest import build_manifest
from dennis.core.hash import canonical_hash


# ------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------

def _tarinfo_for_bytes(name: str, data: bytes) -> tarfile.TarInfo:
    """
    Create deterministic TarInfo metadata.
    """
    ti = tarfile.TarInfo(name=name)
    ti.size = len(data)
    ti.mtime = 0
    ti.uid = 0
    ti.gid = 0
    ti.uname = ""
    ti.gname = ""
    ti.mode = 0o644
    return ti


# ------------------------------------------------------------
# Main packer
# ------------------------------------------------------------

def pack_dex(payload_path, output_path, payload_type="dennis.plan.v1"):
    """
    Create a .dex artifact from a payload file.

    payload_path : file to include
    output_path  : resulting .dex file
    """

    payload_path = Path(payload_path)
    output_path = Path(output_path)

    payload_bytes = payload_path.read_bytes()

    # compute payload hash
    payload_hash = canonical_hash(json.loads(payload_bytes))

    manifest = build_manifest(
        payload_hash_value=payload_hash,
        payload_type=payload_type
    )

    manifest_bytes = json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False
    ).encode("utf-8")

    # --------------------------------------------------------
    # Create tar in memory (small files only in v1)
    # --------------------------------------------------------

    tar_buffer = io.BytesIO()

    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:

        # payload
        payload_name = f"payload/{payload_path.name}"
        ti = _tarinfo_for_bytes(payload_name, payload_bytes)
        tar.addfile(ti, io.BytesIO(payload_bytes))

        # manifest
        ti = _tarinfo_for_bytes("manifest.json", manifest_bytes)
        tar.addfile(ti, io.BytesIO(manifest_bytes))

    tar_bytes = tar_buffer.getvalue()

    # --------------------------------------------------------
    # gzip layer
    # --------------------------------------------------------

    with open(output_path, "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", compresslevel=9, mtime=0) as gz:
            gz.write(tar_bytes)

    return output_path

if __name__ == "__main__":
    import sys
    from pathlib import Path
    from dennis.dex.pack import pack_dex   # adjust if function name differs

    if len(sys.argv) != 3:
        print("Usage: python -m dennis.dex.pack <plan.json> <artifact.dex>")
        sys.exit(1)

    plan = Path(sys.argv[1])
    out = Path(sys.argv[2])

    pack_dex(plan, out)

    print(f"DEX artifact written → {out}")