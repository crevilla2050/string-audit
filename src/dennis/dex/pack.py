"""
DEX Artifact Packer
Dennis v1

Creates deterministic .dex artifacts (tar.gz).
"""

import tarfile
import gzip
import io
import json
from hashlib import sha256
from pathlib import Path
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from dennis.dex.manifest import build_manifest, validate_lineage_structure, build_root_lineage, build_derived_lineage, build_detached_lineage   
from dennis.core.hash import canonical_hash

DEFAULT_IGNORES = [
    ".git",
    ".git/*",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.log",
    ".DS_Store",
    "node_modules/",
    "Thumbs.db",
    "venv/",
    ".venv/",
    ".gitignore",

    # 🔥 CRITICAL ADDITIONS
    "payload/",
    "helpers/",
    "*.dex",
    "dennis-plan*",
    "dictionary*",
]

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

def load_gitignore(root: Path):
    gitignore = root / ".gitignore"

    if not gitignore.exists():
        return None

    lines = gitignore.read_text(encoding="utf-8").splitlines()
    return PathSpec.from_lines(GitWildMatchPattern, lines)

# ------------------------------------------------------------
# Main packer
# ------------------------------------------------------------

def pack_dex(
    payload_path,
    output_path,
    payload_type="dennis.plan.v2",
    include_files=True,
    parent_manifest=None,          # NEW
    force_detached=False           # NEW
):
    """
    Create a .dex artifact from a payload file.

    v2:
    - includes full filesystem snapshot (payload/files/)
    - keeps plan.json as transformation layer
    """
    
    payload_path = Path(payload_path)
    output_path = Path(output_path)

    payload_obj = json.loads(payload_path.read_text())

    # --------------------------------------------------------
    # Normalize helpers (v1 → v2)
    # --------------------------------------------------------

    
    helpers_output = []

    legacy_helpers = payload_obj.get("patches", {}).get("helpers", [])

    existing_helpers = {
        (ch.get("helper_id"), ch.get("file"), ch.get("line"))
        for ch in payload_obj.get("changes", [])
        if ch.get("type") == "helper"
    }

    seen_helper_ids = set()

    for ch in payload_obj.get("changes", []):
        if ch.get("type") == "helper":
            ref = ch.get("helper_ref")

            if ref and not ref.startswith("helpers/"):
                ch["helper_ref"] = f"helpers/{Path(ref).name}"


    # remove legacy helpers (important)
    if "patches" in payload_obj:
        payload_obj["patches"].pop("helpers", None)

    # --------------------------------------------------------
    # NEW: process helpers from changes[] (v2 system)
    # --------------------------------------------------------

    for ch in payload_obj.get("changes", []):
        if ch.get("type") != "helper":
            continue

        helper_source = ch.get("helper_source")


        if helper_source:
            helper_path_fs = (payload_path.parent / helper_source).resolve()
        else:
            helper_source = ch.get("helper_source")

            if not helper_source:
                raise SystemExit("[Dennis] ERROR: helper_source missing in plan")
            helper_path_fs = (payload_path.parent / helper_source).resolve()
            

        print("[DEBUG] resolving helper:", helper_path_fs)

        if not helper_path_fs.exists():
            raise SystemExit(f"[Dennis] ERROR: Helper not found: {helper_path_fs}")

        helper_bytes = helper_path_fs.read_bytes()
        helper_hash = sha256(helper_bytes).hexdigest()
        helper_id = helper_hash[:12]

        ext = helper_path_fs.suffix or ".txt"
        helper_name = f"helper_{helper_id}{ext}"
        helper_arc_path = f"helpers/{helper_name}"

        if helper_id not in seen_helper_ids:
            helpers_output.append({
                "id": helper_id,
                "path": helper_arc_path,
                "content": helper_bytes
            })
            seen_helper_ids.add(helper_id)

        # normalize plan
        ch["helper_id"] = helper_id
        ch["helper_ref"] = helper_arc_path
        

    payload_bytes = json.dumps(
        payload_obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

    # --------------------------------------------------------
    # Hash
    # --------------------------------------------------------

    payload_hash = canonical_hash(json.loads(payload_bytes))

    # --------------------------------------------------------
    # Lineage determination (CRITICAL)
    # --------------------------------------------------------
    if force_detached and parent_manifest:
        raise ValueError("Cannot use both parent_manifest and force_detached")

    if force_detached:
        lineage = build_detached_lineage()

    elif parent_manifest:

        if "lineage" not in parent_manifest:
            raise ValueError("Parent manifest missing lineage")

        if parent_manifest["lineage"].get("type") == "detached":
            raise ValueError("Cannot derive from detached artifact")
        
        if not parent_manifest["lineage"].get("lineage_id"):
            raise ValueError("Parent lineage missing lineage_id")

        lineage = build_derived_lineage(parent_manifest)

    else:
        # ROOT artifact
        lineage = build_root_lineage(payload_hash)
    
    print(f"[Dennis] Lineage type: {lineage['type']}")

    if lineage["lineage_id"]:
        print(f"[Dennis] Lineage ID: {lineage['lineage_id']}")

    manifest = build_manifest(
        payload_hash_value=payload_hash,
        payload_type=payload_type,
        lineage=lineage
    )

    validate_lineage_structure(manifest)

    manifest_bytes = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

    # --------------------------------------------------------
    # Tar creation
    # --------------------------------------------------------

    tar_buffer = io.BytesIO()

    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:

        # ----------------------------------------
        # payload/plan.json
        # ----------------------------------------

        payload_name = "payload/plan.json"
        ti = _tarinfo_for_bytes(payload_name, payload_bytes)
        tar.addfile(ti, io.BytesIO(payload_bytes))

        # ----------------------------------------
        # payload/files/
        # ----------------------------------------

        if include_files:
            root_dir = payload_path.parent  # project dir assumption

            gitignore_spec = load_gitignore(root_dir)

            default_spec = PathSpec.from_lines(GitWildMatchPattern, DEFAULT_IGNORES)

            def is_ignored(path_str):
                if default_spec.match_file(path_str):
                    return True
                if gitignore_spec and gitignore_spec.match_file(path_str):
                    return True
                return False
                print(
                    "[Dennis] WARNING: No .gitignore found.\n"
                    "         Using default ignore rules.\n"
                    "         Consider adding a .gitignore for better control."
                )

            for file_path in sorted(root_dir.rglob("*")):

                if not file_path.is_file():
                    continue

                # skip artifact itself
                if file_path.name.endswith(".dex"):
                    continue

                rel_path = file_path.relative_to(root_dir)

                # ----------------------------------------
                # IGNORE FILTER (NEW)
                # ----------------------------------------
                if is_ignored(str(rel_path)):
                    continue

                data = file_path.read_bytes()

                arcname = f"payload/files/{rel_path}"

                ti = _tarinfo_for_bytes(arcname, data)
                tar.addfile(ti, io.BytesIO(data))
        
        # ----------------------------------------
        # payload/helpers/
        # ----------------------------------------

        for helper in helpers_output:
            arcname = f"payload/{helper['path']}"
            data = helper["content"]

            ti = _tarinfo_for_bytes(arcname, data)
            tar.addfile(ti, io.BytesIO(data))

        # ----------------------------------------
        # manifest.json
        # ----------------------------------------

        ti = _tarinfo_for_bytes("manifest.json", manifest_bytes)
        tar.addfile(ti, io.BytesIO(manifest_bytes))

    tar_bytes = tar_buffer.getvalue()

    # --------------------------------------------------------
    # gzip layer (deterministic)
    # --------------------------------------------------------

    with open(output_path, "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", compresslevel=9, mtime=0) as gz:
            gz.write(tar_bytes)

    return output_path