import os
from dennis import server
from dotenv import load_dotenv

from dennis.dex.pack import collect_project_files, export_dexscope_json, load_dexscope

load_dotenv(os.path.expanduser("~/.dennis/.env"))

import argparse
from marshal import version
from os import path
import re
from pathlib import Path
import json
from datetime import datetime, timezone
import urllib.request
import urllib.error
import requests
import base64
import hashlib

from dennis.scanner import scan_directory
from dennis.reporters.human import print_human_report
from dennis.reporters.json_reporter import write_json_report
from dennis.commands.projects import register_projects_commands

from dennis.i18n.generator import (
    load_findings,
    build_dictionary,
    write_en_json,
    write_en_js,
    load_existing_dict,
    merge_dictionaries,
)

from dennis.i18n.plan import (
    generate_plan,
    write_plan,
    default_plan_filename,
    load_helper
)

from dennis.core.export_html import export_html
from dennis.core.export_xml import export_xml
from dennis.core.import_xml import import_xml
from dennis.core.serialize import dump_json
from dennis.core.export_xsd import export_xsd
from dennis.core.validate_xml import validate_xml_file
from dennis.core.identity import derive_key_id_from_public_key_bytes

# QR
from dennis.qr import (
    decode_ascii_payload,
    decode_image_qr,
    extract_uri_from_ascii,
    extract_uri_from_image,
)
from dennis.qr.encode import make_qr_uri, generate_ascii_qr, generate_png_qr
from dennis.qr.parse import parse_dfp_uri

from dennis.core.invert import cmd_invert

from dennis.dex.canonical_diff import (
    generate_observed_diff_directories,
    generate_planned_diff,
    normalize_to_dennis_diff_v1,
    diff_hash,
    generate_observed_diff_git, 
    validate_diff_artifact
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_case(case_dir: Path):
    input_a = case_dir / "input_a"
    input_b = case_dir / "input_b"
    expected_json_path = case_dir / "expected.json"
    expected_hash_path = case_dir / "expected.hash"

    errors = []

    if not input_a.exists() or not input_b.exists():
        return ["missing_inputs"], None, None, None, None

    if not expected_json_path.exists():
        return ["missing_expected_json"], None, None, None, None

    if not expected_hash_path.exists():
        return ["missing_expected_hash"], None, None, None, None

    expected = load_json(expected_json_path)
    expected_hash = expected_hash_path.read_text().strip()

    try:
        result = generate_observed_diff_directories(input_a, input_b, verbose=args.verbose)
        canonical = normalize_to_dennis_diff_v1(result)
        actual_hash = diff_hash(canonical)
    except Exception as e:
        return [f"runtime_error: {e}"], None, expected, None, expected_hash

    if canonical != expected:
        errors.append("canonical_mismatch")

    if actual_hash != expected_hash:
        errors.append("hash_mismatch")

    return errors, canonical, expected, actual_hash, expected_hash


def banner():
    return "Dennis the Forge — deterministic codemods"

NON_SEMANTIC_FIELDS = {"confidence", "notes"}
OUTPUT_FORMATS = ["text", "json", "xml", "html"]


def normalize_change(change, semantic=True):

    if not semantic:
        return change

    return {
        k: v for k, v in change.items()
        if k not in NON_SEMANTIC_FIELDS
    }

def index_changes(plan, semantic=True):

    result = {}

    for c in plan.get("changes", []):

        # Use explicit id if present
        cid = c.get("id")

        # Otherwise derive a deterministic id
        if cid is None:
            cid = f"{c.get('file')}:{c.get('line')}:{c.get('original')}"

        result[cid] = normalize_change(c, semantic)

    return result

def add_format_argument(parser):
    parser.add_argument(
        "--format",
        choices=["csv", "html", "xml", "txt"],
        default="csv",
        help="Dictionary format"
    )

def add_remote_argument(parser):
    parser.add_argument(
        "--remote",
        default="http://127.0.0.1:8000",
        help="Remote registry URL"
    )

def get_env_config():
    import os

    api_prefix = os.getenv("API_PREFIX")
    server = os.getenv("DENNIS_SERVER")

    if api_prefix is None:
        api_prefix = "/api"

    return {
        "server": server,
        "api_prefix": api_prefix
    }

def is_git_repo(path: str | Path) -> bool:
    return (Path(path) / ".git").exists()

import subprocess

def get_git_tracked_files(path: str | Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(path), "ls-files"],
        capture_output=True,
        text=True,
        check=True
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]

def is_binary_file(path: Path) -> bool:
    try:
        with open(path, 'rb') as f:
            chunk = f.read(1024)
        return b'\0' in chunk
    except Exception:
        return True  # safest fallback
    

from dennis.commands.projects import (
    projects_deleted,
    projects_restore
)

import subprocess

def command_diff():
    import tempfile, json, os, requests
    from dennis.forge.config import load_config
    from dennis.dex.canonical_diff import generate_observed_diff_git

    # ----------------------------------------
    # 1. GET DIFF (use canonical generator)
    # ----------------------------------------
    artifact = generate_observed_diff_git()

    if not artifact['payload']['files']:
        print("No changes detected")
        return

    # ----------------------------------------
    # 2. LOAD CONFIG
    # ----------------------------------------
    config = load_config()
    token = config.get("auth", {}).get("token")
    api_prefix = config.get("api_prefix", "")
    server = config.get("server")

    if not token:
        raise SystemExit("Not authenticated. Run: dennis login")

    url = f"{server.rstrip('/')}{api_prefix}/artifacts"

    # ----------------------------------------
    # 3. WRITE TEMP FILE
    # ----------------------------------------
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        tmp.write(json.dumps(artifact).encode("utf-8"))
        tmp_path = tmp.name

    # ----------------------------------------
    # 4. UPLOAD (CORRECT WAY)
    # ----------------------------------------
    try:
        with open(tmp_path, "rb") as f:
            files = {
                "file": ("diff.json", f, "application/json")
            }

            headers = {
                "Authorization": f"Bearer {token}"
            }

            resp = requests.post(url, headers=headers, files=files)

        if resp.status_code not in (200, 201):
            raise SystemExit(f"Upload failed: {resp.text}")

        result = resp.json()
        print("✔ Diff artifact created:", result.get("artifact_hash"))

    finally:
        os.remove(tmp_path)

import difflib

def pretty_json(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True)

def show_diff(expected, actual):
    expected_str = pretty_json(expected).splitlines()
    actual_str = pretty_json(actual).splitlines()

    diff = difflib.unified_diff(
        expected_str,
        actual_str,
        fromfile="expected",
        tofile="actual",
        lineterm=""
    )

    for line in diff:
        print("    " + line)

def refresh_dexscope(root_dir):

    root_dir = Path(root_dir)

    scope_file = root_dir / ".dexscope"

    if not scope_file.exists():
        raise SystemExit(
            "[Dennis] ERROR: .dexscope not found. "
            "Run 'dennis scope export' first."
        )

    generated_files = {
        str(p.relative_to(root_dir))
        for p in collect_project_files(root_dir)
    }

    old_lines = scope_file.read_text(
        encoding="utf-8"
    ).splitlines()

    output_lines = []

    consumed = set()

    for line in old_lines:

        stripped = line.strip()

        # preserve blank lines
        if not stripped:
            output_lines.append(line)
            continue

        # preserve header
        if stripped == "# Dennis Scope v1":
            output_lines.append(line)
            continue

        # preserve comments/inactive entries exactly
        if stripped.startswith("#"):
            candidate = stripped[1:].strip()

            if candidate in generated_files:
                consumed.add(candidate)

            output_lines.append(line)
            continue            

        # active file entry
        if stripped in generated_files:
            output_lines.append(line)
            consumed.add(stripped)

    remaining = generated_files - consumed

    if remaining:

        output_lines.append("")

        for path in sorted(remaining):
            output_lines.append(path)

    scope_file.write_text(
        "\n".join(output_lines) + "\n",
        encoding="utf-8"
    )

    print(f"[Dennis] Scope refreshed → {scope_file}")

# ============================================================
# IDENTITY HELPERS
# ============================================================
# Invariants:
# - key_id = canonical_hash(public_key_bytes)[:16] (implemented as sha256 hex prefix)
# - CLI never auto-selects identity.
# - No active identity -> signing must fail.
# - --key always overrides active identity.
# - whoami derives identity and never trusts stored values.

def resolve_identity_paths(name: str):
    keys_dir = Path.home() / ".dennis" / "keys"
    private_path = keys_dir / f"{name}.key"
    public_path = keys_dir / f"{name}.pub"

    if not private_path.exists():
        raise SystemExit(f"Identity key not found: {private_path}")

    if not public_path.exists():
        raise SystemExit(f"Identity public key not found: {public_path}")

    return private_path, public_path


def load_identity(pub_path: Path) -> dict:
    try:
        identity = json.loads(pub_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"Failed to read identity file: {pub_path} ({e})")

    public_key_b64 = identity.get("public_key")
    if not public_key_b64:
        raise SystemExit(f"Identity file missing public_key: {pub_path}")

    try:
        public_key_bytes = base64.b64decode(public_key_b64)
    except Exception:
        raise SystemExit(f"Identity file has invalid public_key encoding: {pub_path}")

    enriched = dict(identity)
    enriched["derived_key_id"] = derive_key_id_from_public_key_bytes(public_key_bytes)
    return enriched


def _context_path():
    return Path.home() / ".dennis" / "context.json"


def load_context():
    path = _context_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def save_context(data):
    path = _context_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))

def debug_identity(pub_path):
    from pathlib import Path
    import json

    from dennis.core.keys import key_id_from_pub

    # Load your public key file
    pub_path = Path(pub_path)
    pub_text = pub_path.read_text()

    # If your .pub is JSON (which it is), extract public_key field
    data = json.loads(pub_text)
    pub_b64 = data["public_key"]

    import base64
    pub_bytes = base64.b64decode(pub_b64)

    # Compute both IDs
    id_from_bytes = derive_key_id_from_public_key_bytes(pub_bytes)
    id_from_pub = key_id_from_pub(pub_text)

    print("derived_key_id:", id_from_bytes)
    print("key_id_from_pub:", id_from_pub)

    assert id_from_bytes == id_from_pub, "❌ MISMATCH: identity derivation is inconsistent"

    print("✅ OK: identity derivation is consistent")

def run_interactive_plan(args):
    import json
    from pathlib import Path
    from datetime import datetime

    print("[Dennis] Interactive planning mode\n")

    def ask(prompt, default=None):
        try:
            val = input(prompt).strip()
            return val if val else default
        except KeyboardInterrupt:
            print("\n[Dennis] Interactive mode cancelled")
            raise SystemExit(0)

    try:
        helpers = []

        inject = ask("Inject helper? (y/N): ", "n").lower()

        if inject == "y":
            from pathlib import Path

            helper_path = ask("Helper file path: ")
            helper_file = Path(helper_path)

            if not helper_file.exists():
                raise SystemExit(f"[Dennis] ERROR: helper file not found → {helper_path}")

            if not helper_file.is_file():
                raise SystemExit(f"[Dennis] ERROR: helper is not a file → {helper_path}")


            target = ask("Target file: ")
            target_file = Path(target)

            helper_path = str(helper_file.resolve())
            target = str(target_file.resolve())

            if not target_file.exists():
                raise SystemExit(f"[Dennis] ERROR: target file not found → {target}")

            if not target_file.is_file():
                raise SystemExit(f"[Dennis] ERROR: target is not a file → {target}")
            line_raw = ask("Insert at line (default 1): ", "1")

            try:
                line = int(line_raw)
                if line < 1:
                    raise ValueError
            except ValueError:
                raise SystemExit("[Dennis] ERROR: line must be a positive integer")

            helpers.append({
                "file": helper_path,
                "target": target,
                "line": line
            })

        use_git = ask("Use git mode? (Y/n): ", "y").lower() != "n"

        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        filename = f"spec-{timestamp}.json"

        spec = {
            "version": 1,
            "mode": "project",
            "root": args.root or ".",
            "helpers": helpers,
            "options": {
                "use_git": use_git
            },
            "created_at": timestamp + "Z",
            "filename": filename
        }

        # ----------------------------------------
        # Timestamped filename
        # ----------------------------------------

        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        spec_path = Path(filename)

        spec_path.write_text(json.dumps(spec, indent=2))

        print(f"\n[Dennis] Spec written → {spec_path}\n")

        # ----------------------------------------
        # CLI hint (training layer)
        # ----------------------------------------

        if not getattr(args, "no_cli_hint", False):

            cmd = ["dennis", "plan", "."]

            if helpers:
                h = helpers[0]
                cmd += [
                    "--add-helper", h["file"],
                    "--target-file", h["target"],
                    "--line", str(h["line"])
                ]

            if use_git:
                cmd.append("--use-git")

            print("Equivalent command:\n")
            print(" ".join(cmd))
            print("\nTip: reuse this configuration with:")
            print(f"  dennis plan {spec_path}\n")

    except KeyboardInterrupt:
        print("\n[Dennis] Interactive mode cancelled")
        raise SystemExit(0)


# ============================================================
# ARGPARSE
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dennis",
        description="Dennis Forge — deterministic codemod engine and artifact system.",
        epilog="Forged slowly. Built for trust.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-v", "--version",
        action="store_true",
        help="Show Dennis version"
    )
    parser.epilog = """
    Examples:

    dennis plan .
    dennis plan . --dict dictionary.json
    dennis dex pack plan.json artifact.dex
    (optional) dennis keygen
    dennis dex sign artifact.dex --key my_key.key
    dennis inspect artifact.dex
    dennis encrypt artifact.dex

    Diff examples:
    dennis git-diff
    dennis diff-directories /path/to/before /path/to/after
    dennis compare planned.dex observed.dex
    dennis inspect diff.dex

    Forged slowly. Built for trust.
    """

    parser.usage = """
    dennis [command] [options]

    Core workflow:
    plan       generate transformation plan
    pack       create DEX artifact
    dex sign       sign artifact
    inspect    inspect artifact metadata
    verify     verify signatures
    validate-plan   validate transformation semantics

    Diff system:
    git-diff   create diff artifact from git changes
    diff-directories   create diff artifact by comparing directories
    compare    reconcile planned vs observed diffs

    Security:
    encrypt    convert DEX → XDEX
    decrypt    convert XDEX → DEX

    Execution:
    rehydrate  restore project context from artifact
    apply      execute transformation plan
    """

    parser.add_argument(
        "--accept-lineage",
        help="Override lineage mismatch (must match artifact lineage_id)"
    )

    parser.add_argument(
        "--accept-detached",
        action="store_true",
        help="Allow applying detached artifact (no lineage)"
    )


    sub = parser.add_subparsers(dest="command")


    # --------------------------------------------------------
    # PLAN (DEFAULT + EXPORT)
    # --------------------------------------------------------

    plan_cmd = sub.add_parser(
        "plan",
        help="Generate transformation plan or export plan"
    )

    plan_cmd.description = """
    Plan operations:

    Default:
    Generate transformation plan from a project directory

    Subcommands:
    export    export plan to other formats
    import    import helper mappings from CSV
    """

    # ---------------------------------------------------------
    # CORE ARGUMENTS (RUN MODE)
    # ---------------------------------------------------------

    plan_cmd.add_argument(
        "root",
        nargs="?",
        help="Project root directory (default: current directory)"
    )

    plan_cmd.add_argument(
        "--dict",
        help="Dictionary JSON file (optional, auto-generated if omitted)"
    )

    plan_cmd.add_argument(
        "--baseline",
        help="Baseline DEX artifact for diff-based plan generation"
    )

    plan_cmd.add_argument(
        "--out",
        help="Output plan filename"
    )

    plan_cmd.add_argument(
        "--add-helper",
        action="append",
        help="Helper file to insert"
    )

    plan_cmd.add_argument(
        "--target-file",
        action="append",
        help="Target file for helper"
    )

    plan_cmd.add_argument(
        "--line",
        action="append",
        type=int,
        help="Insertion line for helper"
    )

    plan_cmd.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode to generate spec.json"
    )

    plan_cmd.add_argument(
        "--no-cli-hint",
        action="store_true",
        help="Do not show equivalent CLI command"
    )

    plan_cmd.add_argument(
        "--scan",
        action="store_true",
        help="Scan project and output observations only without generating a plan"
    )

    # ---------------------------------------------------------
    # MANUAL SUBCOMMAND (KEY FIX)
    # ---------------------------------------------------------

    plan_cmd.add_argument(
        "plan_command",
        nargs="?",
        choices=["export", "import"],
        help="Optional subcommand"
    )

    # ---------------------------------------------------------
    # EXPORT ARGUMENTS
    # ---------------------------------------------------------

    plan_cmd.add_argument(
        "plan",
        nargs="?",
        help="Plan JSON file (for export)"
    )

    plan_cmd.add_argument(
        "--format",
        choices=["csv", "html", "xml", "txt"],
        default="csv",
        help="Export format"
    )

    plan_cmd.add_argument(
        "--file",
        help="Output filename"
    )

    plan_cmd.add_argument(
        "--use-git",
        action="store_true",
        help="Limit scan to files changed according to git"
    )

    plan_cmd.add_argument(
        "import_file",
        nargs="?",
        help="CSV file with helper mappings (for import)"
    )

    plan_cmd.add_argument(
        "--lang",
        default="python",
        help="Language plugin to use (default: python)"
    )

    plan_cmd.add_argument(
        "--exclude-lang",
        help="Comma-separated list of programming languages to exclude"
    )

    # ---------------------------------------------------------
    # IMPORT ARGUMENTS
    # ---------------------------------------------------------

    

    git_diff_cmd = sub.add_parser(
        "git-diff",
        help="Create artifact from git diff"
    )

    diff_directories_cmd = sub.add_parser(
        "diff-directories",
        help="Create artifact by comparing two directories"
    )

    diff_directories_cmd.add_argument(
        "source_dir",
        help="Source directory path"
    )

    diff_directories_cmd.add_argument(
        "target_dir",
        help="Target directory path"
    )

    diff_directories_cmd.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output (debug information)"
    )

    diff_directories_cmd.add_argument(
        "--create-plan",
        action="store_true",
        help="Generate a plan.json from observed differences"
    )


    compare_cmd = sub.add_parser(
        "compare",
        help="Compare planned vs observed diffs (reconciliation)"
    )

    compare_cmd.add_argument(
        "planned_diff",
        help="Path to planned diff DEX artifact"
    )

    compare_cmd.add_argument(
        "observed_diff",
        help="Path to observed diff DEX artifact"
    )

    # --------------------------------------------------------
    # VERIFY-EXECUTION
    # --------------------------------------------------------

    verify_exec_cmd = sub.add_parser(
        "verify-execution",
        help="Verify that execution matched expected diff"
    )

    verify_exec_cmd.add_argument(
        "--expected",
        required=True,
        help="Path to expected diff JSON (dennis-expected-*.json)"
    )

    verify_exec_cmd.add_argument(
        "--observed",
        required=True,
        help="Path to observed diff JSON (dennis-observed-*.json)"
    )

    verify_exec_cmd.add_argument(
        "--strict",
        action="store_true",
        help="Fail verification when execution scope differs from planned scope"
    )

    # --------------------------------------------------------
    # ENCRYPT
    # --------------------------------------------------------

    encrypt_cmd = sub.add_parser(
        "encrypt",
        help="Convert DEX → XDEX (encrypt artifact)"
    )

    encrypt_cmd.add_argument(
        "artifact",
        help="Path to .dex artifact"
    )

    encrypt_cmd.add_argument(
        "--out",
        help="Output .xdex file (optional)"
    )


    # --------------------------------------------------------
    # DECRYPT
    # --------------------------------------------------------

    decrypt_cmd = sub.add_parser(
        "decrypt",
        help="Convert XDEX → DEX (decrypt artifact)"
    )

    decrypt_cmd.add_argument(
        "artifact",
        help="Path to .xdex artifact"
    )

    decrypt_cmd.add_argument(
        "--out",
        help="Output .dex file (optional)"
    )


    # REHYDRATE
    rehydrate = sub.add_parser(
    "rehydrate",
        help="Restore project context from DEX artifact"
    )

    rehydrate.add_argument(
        "artifact",
        help="Path to <artifact.dex> to rehydrate from"
    )

    rehydrate.add_argument(
        "--out",
        default=".",
        help="Output directory (default: current directory)"
    )

    # VALIDATE
    validate = sub.add_parser("validate", help="Validate a DEX artifact")
    validate.add_argument("path", help="Path to .dex file")
    validate.add_argument(
        "--signature-file",
        action="append",
        help="External public key file(s) to use for signature verification"
    )

    # HASH
    hash_cmd = sub.add_parser("hash")
    hash_cmd.add_argument("file")

    # PUSH
    push_cmd = sub.add_parser(
        "push",
        help="Use to publish a plan.json to remote registry (use 'publish' for artifacts)"
    )
    
    push_cmd.add_argument("plan")
    push_cmd.add_argument("--qr", action="store_true")
    push_cmd.add_argument("--qr-path")
    add_remote_argument(push_cmd)

    # PULL
    pull_cmd = sub.add_parser("pull", help="Download artifact from registry")
    pull_cmd.add_argument("hash", help="Full artifact hash")
    
    add_remote_argument(pull_cmd)

    # QR GENERATION
    qr_parser = sub.add_parser("qr", help="Generate Dennis QR codes")
    qr_parser.add_argument("hash")
    qr_parser.add_argument("--ascii", action="store_true")
    qr_parser.add_argument("--png", help="Output PNG file path")
    qr_parser.add_argument("--qr-path", default=".")

    # QR SCANNING
    scan_qr = sub.add_parser("scan-qr")
    scan_qr.add_argument("--ascii", action="store_true")
    scan_qr.add_argument("--image", action="store_true")
    scan_qr.add_argument("--from-file", required=True)

    # IDENTITY
    identity_cmd = sub.add_parser("identity", help="Identity management")
    identity_sub = identity_cmd.add_subparsers(dest="identity_command", required=True)

    identity_use = identity_sub.add_parser("use", help="Set active identity")
    identity_use.add_argument("name", help="Identity key name (without extension)")

    identity_sub.add_parser("current", help="Show active identity")
    identity_sub.add_parser("list", help="List available identities")

    # DEX group (sign / verify)
    dex = sub.add_parser("dex", help="DEX artifact actions")
    dex_sub = dex.add_subparsers(dest="dex_command", required=True)

    dex_sign = dex_sub.add_parser("sign", help="Sign a DEX artifact")
    dex_sign.add_argument("artifact", help="Path to artifact.dex")
    dex_sign.add_argument("--key", help="Private key file (ed25519). Overrides active identity.")
    dex_sign.add_argument("--key-id", help="Key identifier to store in signatures/<key_id>.pub (default: derived from public key)")

    dex_verify = dex_sub.add_parser("verify", help="Verify signatures on a DEX artifact")
    dex_verify.add_argument("artifact", help="Path to artifact.dex")
    dex_verify.add_argument("--verbose", action="store_true", help="Show extra verification info (counts only)")

    # SEARCH
    search_cmd = sub.add_parser("search", help="Search artifacts in registry")
    add_remote_argument(search_cmd)
    search_cmd.add_argument("--type", dest="payload_type", help="Filter by payload type")
    search_cmd.add_argument("--hash", dest="hash_prefix", help="Search by artifact hash prefix")
    search_cmd.add_argument("--limit", type=int, default=20)
    search_cmd.add_argument("--offset", type=int, default=0)
    
    # ARCHITECTURE SCAN
    architecture = sub.add_parser(
        "architecture",
        help="Architecture analysis commands"
    )

    architecture_sub = architecture.add_subparsers(
        dest="architecture_command",
        required=True
    )

    arch_scan = architecture_sub.add_parser(
        "scan",
        help="Scan source tree and generate architecture observations"
    )

    arch_scan.add_argument(
        "path",
        help="Source tree path"
    )

    arch_scan.add_argument(
        "--output",
        choices=["json"],
        default="json",
        help="Output format"
    )

    # PUBLISH
    publish_cmd = sub.add_parser(
        "publish",
        help="Publish a signed DEX artifact to a registry"
    )
    publish_cmd.add_argument("artifact", help="Path to artifact.dex")
    add_remote_argument(publish_cmd)

    # INSPECT
    inspect_cmd = sub.add_parser("inspect", help="Inspect artifact metadata")
    inspect_cmd.add_argument("target", help="Artifact hash or .dex file")
    
    add_remote_argument(inspect_cmd)
    inspect_cmd.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )

    inspect_cmd.add_argument(
        "--validate-schema",
        action="store_true",
        help="Validate output against inspect.v1.schema.json"
    )

    inspect_cmd.add_argument(
        "--goals",
        action="store_true",
        help="Run Goal Discovery on an OBAD artifact"
    )

    inspect_cmd.add_argument(
        "--specs",
        action="store_true",
        help="Run Spec Discovery on a Goal Discovery artifact"
    )
    
    # SIGNATURES 
    sig_cmd = sub.add_parser("signatures", help="Show artifact signatures")
    sig_cmd.add_argument("hash")
    add_remote_argument(sig_cmd)
    add_format_argument(sig_cmd)

    # LINEAGE
    lin_cmd = sub.add_parser("lineage", help="Show artifact provenance chain")
    lin_cmd.add_argument("hash")
    add_remote_argument(lin_cmd)
    add_format_argument(lin_cmd)

    # DIFF
    diff_cmd = sub.add_parser("diff", help="Compare two Dennis artifacts")
    diff_cmd.add_argument("artifact_a")
    diff_cmd.add_argument("artifact_b")
    diff_cmd.add_argument("--ignore-semantics", action="store_true")
    add_format_argument(diff_cmd)

    test_diff_cmd = sub.add_parser(
        "test-diff",
        help="Run Dennis diff conformance tests"
    )
    test_diff_cmd.add_argument(
        "--init",
        action="store_true",
        help="Generate expected.hash files (bootstrap mode)"
    )
    test_diff_cmd.add_argument(
        "--case",
        help="Run a single test case (e.g. case_003_block_merge)"
    )
    test_diff_cmd.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed mismatch information"
    )

    # PACK
    pack_cmd = sub.add_parser("pack", help="Create deterministic DEX artifact")
    pack_cmd.add_argument("payload", help="Path to plan.json payload")
    pack_cmd.add_argument("out", help="Output artifact.dex")
    pack_cmd.add_argument(
        "--type",
        default="dennis.plan.v1",
        help="Payload type (default: dennis.plan.v1)"
    )
    pack_cmd.add_argument(
        "--parent",
        help="Path to parent artifact.dex to inherit lineage from (optional)"
    )
    pack_cmd.add_argument(
        "--detached",
        action="store_true",
        help="Create a detached signature (optional)"
    )

    # --------------------------------------------------------
    # SCOPE
    # --------------------------------------------------------

    scope_cmd = sub.add_parser(
        "scope",
        help="DEX scope management"
    )

    scope_sub = scope_cmd.add_subparsers(
        dest="scope_command",
        required=True
    )

    scope_export = scope_sub.add_parser(
        "export",
        help="Generate .dexscope from project"
    )

    scope_refresh = scope_sub.add_parser(
        "refresh",
        help="Refresh existing .dexscope"
    )

    scope_refresh.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Project root"
    )

    scope_export.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Project root"
    )

    scope_inspect = scope_sub.add_parser(
        "inspect",
        help="Show scope evaluation"
    )

    scope_inspect.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Project root"
    )

    scope_json = scope_sub.add_parser(
        "json",
        help="Generate .dexscope.json"
    )

    scope_json.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Project root"
    )


    # UNPACK
    unpack_cmd = sub.add_parser("unpack", help="Extract DEX artifact")
    unpack_cmd.add_argument("artifact")
    unpack_cmd.add_argument("--out", default=None)

    # REGISTRY GROUP
    registry = sub.add_parser("registry", help="Registry federation commands")
    registry_sub = registry.add_subparsers(dest="registry_command", required=True)

    # registry add
    reg_add = registry_sub.add_parser("add", help="Add remote registry")
    reg_add.add_argument("url")
    add_remote_argument(reg_add)

    # registry list
    reg_list = registry_sub.add_parser("list", help="List remote registries")
    add_remote_argument(reg_list)

    # registry sync
    reg_sync = registry_sub.add_parser("sync", help="Sync remote registries")
    add_remote_argument(reg_sync)

    # apply
    apply_cmd = sub.add_parser(
        "apply",
        help="Execute transformation plan"
    )
    apply_cmd.add_argument("plan", help="Path to plan.json or artifact.dex")

    apply_cmd.add_argument(
        "--confirm",
        help="Confirm execution using payload hash prefix"
    )
    apply_cmd.add_argument(
        "--helper-mode",
        choices=["keep", "remove", "isolate"],
        default="keep",
        help="Control helper file lifecycle after undo"
    )
    apply_cmd.add_argument(
        "--artifact-policy",
        choices=["keep", "clean", "isolate"],
        default="keep",
        help="Control handling of execution artifacts after apply"
    )
    

    # Export
    dict_cmd = sub.add_parser("dict", help="Dictionary utilities")

    dict_sub = dict_cmd.add_subparsers(dest="dict_command")

    export_cmd = dict_sub.add_parser("export", help="Export dictionary")

    export_cmd.add_argument(
        "dictionary",
        help="Source dictionary.json"
    )

    export_cmd.add_argument(
        "--file",
        help="Output filename"
    )

    add_format_argument(export_cmd)

    import_cmd = dict_sub.add_parser("import", help="Import dictionary")
    import_cmd.add_argument("input")
    import_cmd.add_argument("dictionary")
    add_format_argument(import_cmd)

    keygen_cmd = sub.add_parser(
        "keygen",
        help="Generate a Dennis signing keypair"
    )

    filter_cmd = sub.add_parser(
        "filter",
        help="Clean dictionary using semantic filters"
    )

    filter_cmd.add_argument("file")

    filter_cmd.add_argument(
        "--filters",
        nargs="+",
        default=["sql", "css", "url", "code", "dict"],
        help="Filters to apply (default: sql css url)"
    )

    filter_cmd.add_argument(
        "--out",
        help="Optional output file (otherwise auto-named)"
    )

    # --------------------------------------------------------
    # INVERT
    # --------------------------------------------------------

    invert_cmd = sub.add_parser(
        "invert",
        help="Generate inverse plan (undo plan)"
    )

    invert_cmd.add_argument(
        "plan",
        help="Plan JSON file"
    )

    invert_cmd.add_argument(
        "--stdout",
        action="store_true",
        help="Write inverse plan to stdout"
    )

    add_plugin = sub.add_parser(
        "install-plugin",
        help="Install a plugin or dictionary for Dennis"
    )

    add_plugin.add_argument("file")

    add_plugin.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing file"
    )

    add_plugin.add_argument(
        "--backup",
        action="store_true",
        help="Backup existing file before installing"
    )

    # --------------------------------------------------------
    # key management and encryption utilities (moved from crypto.py for better CLI integration)
    # --------------------------------------------------------

    key_cmd = sub.add_parser("key", help="Key management")

    key_sub = key_cmd.add_subparsers(dest="key_command")

    # bootstrap

    key_boot = key_sub.add_parser("bootstrap")
    key_boot.add_argument("pub")

    # approve

    key_app = key_sub.add_parser("approve")
    key_app.add_argument("pub")
    key_app.add_argument("--signer", required=True)

    # list

    key_list = key_sub.add_parser("list")

    # debug-identity

    key_debug = key_sub.add_parser(
        "debug-identity",
        help="Debug identity derivation from a public key"
    )
    key_debug.add_argument("pub")

    validate_plan_cmd = sub.add_parser(
        "validate-plan",
        help="Validate transformation plan inside artifact"
    )

    validate_plan_cmd.add_argument(
        "input",
        help="Path to artifact.dex"
    )

    # --------------------------------------------------------
    # USER
    # --------------------------------------------------------

    user_cmd = sub.add_parser("user", help="User management")
    user_sub = user_cmd.add_subparsers(dest="user_command")
    user_sub.required = True

    # user create
    user_create = user_sub.add_parser("create", help="Create a new user")
    user_create.add_argument("email")

    # user verify
    user_verify = user_sub.add_parser("verify", help="Verify user email")
    user_verify.add_argument("token")

    login_cmd = sub.add_parser("login", help="Authenticate with Dennis The Forge")

    login_cmd.add_argument("--server", required=True)
    login_cmd.add_argument("--email", required=True)
    login_cmd.add_argument("--token", help="Use existing token (for automation)")

    logout_cmd = sub.add_parser("logout", help="Clear stored authentication")

    sub.add_parser("whoami", help="Show current authenticated user")

    register_projects_commands(sub)

    return parser

# ============================================================
# MAIN
# ============================================================

def main() -> None:
    global Path, json
    from dennis.forge.config import load_config

    parser = build_parser()
    args = parser.parse_args()

    env_cfg = get_env_config()
    file_cfg = load_config()
    

    server = (
        getattr(args, "server", None)
        or env_cfg.get("server")
        or file_cfg.get("server")
    )

    server = server.rstrip("/") if server else None

    if args.command in {"login", "publish", "pull", "push"}:
        if not server:
            raise SystemExit("Server not configured. Use --server or set DENNIS_SERVER")

    api_prefix = env_cfg.get("api_prefix")
    api_prefix = api_prefix or "/api"

    if api_prefix is None:
        api_prefix = "/api"

    api_prefix = api_prefix.rstrip("/")

    
    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------
    if args.command == "validate":

        from dennis.dex.validate import validate_dex_file

        results = validate_dex_file(args.path, signature_files=args.signature_file)

        print("\n[ Dennis Validate ]\n")

        # Schema
        if results["schema"]:
            print("[OK] Schema valid")
        else:
            print("[FAIL] Schema invalid")

        # Signatures
        sig_ok = sum(1 for _, ok in results["signatures"] if ok)
        sig_total = len(results["signatures"])

        print(f"[OK] Signatures valid ({sig_ok}/{sig_total})")

        # Provenance
        if results["provenance"]:
            print(f"[OK] Provenance chain valid ({results['provenance_steps']} steps)")
        else:
            print("[FAIL] Provenance chain invalid")

        # Identity
        print("\nPayload Hash:", results.get("payload_hash"))
        print("Trust State:", results.get("provenance_hash"))
        print("Container:", results.get("container", "unknown"))

        if results.get("container") == "xdex":
            print("Header:", "valid" if results.get("header_valid") else "invalid") 
        print()

        return
    
    elif args.command == "validate-plan":
        from dennis.core.plan_validator import validate_plan_from_artifact
        import json

        result = validate_plan_from_artifact(args.input)

        print(json.dumps(result, indent=2))
        return
    
    
    if args.command == "plan":

        from datetime import datetime, timezone
        import tempfile
        from pathlib import Path
        import json

        def _load_spec_if_present(args):
            if not args.root:
                return None

            root_path = Path(args.root)

            if root_path.is_file() and root_path.suffix == ".json":
                try:
                    spec = json.loads(root_path.read_text(encoding="utf-8"))
                except Exception as e:
                    raise SystemExit(f"[Dennis] ERROR: Failed to read spec → {e}")

                if "version" not in spec:
                    raise SystemExit("[Dennis] ERROR: Invalid spec (missing version)")

                print(f"[Dennis] Using spec: {root_path}")

                return spec

            return None

        def ts():
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

        if getattr(args, "interactive", False):
            return run_interactive_plan(args)

        # ----------------------------------------
        # Detect mode (spec support)
        # ----------------------------------------

        spec = _load_spec_if_present(args)
        spec_mode = False

        if spec:
            spec_mode = True

            # override root
            args.root = spec.get("root", ".")

            # options
            opts = spec.get("options", {})
            args.use_git = opts.get("use_git", False)
            args.lang = opts.get("lang", args.lang)

            # helpers (spec-driven)
            args.helper_specs = [
                {
                    "helper": h["file"],
                    "target": h["target"],
                    "line": h["line"]
                }
                for h in spec.get("helpers", [])
            ]

        if not spec_mode and args.root in ("export", "import"):
            args.plan_command = args.root
            args.root = None

        if args.plan_command is None:
            args.plan_command = "run"
        
        excluded_langs = set()

        if args.exclude_lang:
            excluded_langs = {
                lang.strip() for lang in args.exclude_lang.split(",")
            }
        # ----------------------------------------
        # Helper validation (FIXED PIPELINE)
        # ----------------------------------------

        if not spec_mode:

            helpers = args.add_helper or []
            targets = args.target_file or []
            lines = args.line or []

            args.helper_specs = []

            if helpers:

                if not targets:
                    raise SystemExit(
                        "Error: --target-file required when using --add-helper"
                    )

                if len(targets) != len(helpers):
                    raise SystemExit(
                        "Error: number of --target-file must match --add-helper"
                    )

                if lines and len(lines) != len(helpers):
                    raise SystemExit(
                        "Error: number of --line must match --add-helper"
                    )

                if not lines:
                    lines = [1] * len(helpers)

                args.helper_specs = [
                    {
                        "helper": h,
                        "target": t,
                        "line": l
                    }
                    for h, t, l in zip(helpers, targets, lines)
                ]

        # ----------------------------------------
        # EXPORT MODE
        # ----------------------------------------

        if args.plan_command == "export":
            from dennis.core.csvio import write_csv_from_plan

            if not args.plan:
                raise SystemExit("export requires: plan file")

            import json
            plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))

            output = args.file or Path(args.plan).with_suffix(".csv")
            
            # print("[DEBUG BEFORE CSV]", plan["changes"][-1])
            write_csv_from_plan(plan, output)
            # print("[DEBUG BEFORE CSV]", plan["changes"][-1])

            print(f"[Dennis] CSV exported → {output}")
            print(
                "[Dennis] You can now edit the CSV and re-import it using:\n"
                f"         dennis plan import {output}"
            )
            return

        # ----------------------------------------
        # IMPORT MODE
        # ----------------------------------------

        elif args.plan_command == "import":
            from dennis.i18n.csvio import import_plan_csv

            if not args.import_file:
                raise SystemExit("import requires: csv file")

            import_plan_csv(args.import_file, baseline=args.baseline, out=args.out)
            return

        # ----------------------------------------
        # RUN MODE (MAIN LOGIC)
        # ----------------------------------------

        if not args.root:
            raise SystemExit("dennis plan requires a root directory (before snapshot)")

        source_dir = Path(args.root).resolve()
        if not source_dir.exists():
            raise SystemExit(f"Source directory does not exist: {source_dir}")

        # ----------------------------------------
        # MODE: BASELINE
        # ----------------------------------------

        if args.baseline:

            from dennis.core.diff import diff_directories
            from dennis.core.serialize import dump_json
            from dennis.core.csvio import write_csv_from_plan
            from dennis.core.rehydrate import rehydrate

            def ts():
                return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

            with tempfile.TemporaryDirectory() as tmp_dir:
                baseline_path = Path(tmp_dir)

                print(f"[Dennis] Rehydrating baseline → {args.baseline}")
                rehydrate(args.baseline, output_dir=baseline_path)

                print("[Dennis] Computing diff...")
                changes = diff_directories(baseline_path, source_dir)

            plan = {
                "changes": changes,
                "meta": {
                    "baseline": args.baseline
                    # "generated_at": ts()
                }
            }

            output = Path(args.out) if args.out else Path(f"plan-{ts()}.json")
            csv_path = output.with_suffix(".csv")

            with open(output, "w", encoding="utf-8") as f:
                # print("[DEBUG FINAL BEFORE WRITE]", plan["changes"][-1])
                dump_json(plan, f)
            write_csv_from_plan(plan, csv_path)

            print(f"[Dennis] Plan generated → {output}")
            print(f"[Dennis] CSV generated  → {csv_path}")

            # Generate expected diff
            try:
                dennis_dir = Path(".dennis")
                dennis_dir.mkdir(exist_ok=True)

                expected_diff = generate_planned_diff(plan, base_dir=baseline_path)

                if not validate_diff_artifact(expected_diff):
                    raise ValueError("Generated expected diff is invalid")

                if plan.get("changes") and not expected_diff["payload"]["files"]:
                    print("[ERROR] Expected diff is empty — check base_dir alignment")
                    raise SystemExit(1)

                timestamp = ts()
                plan_artifact_path = dennis_dir / f"dennis-plan-{timestamp}.json"
                expected_artifact_path = dennis_dir / f"dennis-expected-{timestamp}.json"

                with open(plan_artifact_path, "w", encoding="utf-8") as f:
                    json.dump(plan, f, indent=2)

                with open(expected_artifact_path, "w", encoding="utf-8") as f:
                    json.dump(expected_diff, f, indent=2)

                file_count = len(expected_diff["payload"]["files"])
                change_count = sum(len(f["changes"]) for f in expected_diff["payload"]["files"])

                print("\n[Dennis] Canonical Diff Generated")
                print(f"  Intent   → {plan_artifact_path}")
                print(f"  Expected → {expected_artifact_path}")
                print(f"  Files: {file_count}, Changes: {change_count}")
                print(f"  Expected hash: {diff_hash(expected_diff)}")

            except Exception as e:
                print(f"[WARNING] Could not generate expected diff: {e}")
                import traceback
                traceback.print_exc()

            return

        # ----------------------------------------
        # MODE: DICTIONARY (DEFAULT)
        # ----------------------------------------

        from dennis.i18n.plan import generate_plan
        from dennis.forge.hash.canonical import canonical_hash

        def ts():
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

        dict_path = Path(args.dict) if args.dict else Path(f"dictionary-{ts()}.json")
        output = Path(args.out) if args.out else Path(default_plan_filename())

        helpers = []

        for spec in getattr(args, "helper_specs", []):
            helper_path = Path(spec["helper"])

            if not helper_path.exists():
                raise SystemExit(f"Helper file not found: {helper_path}")

            helper_info = load_helper(helper_path)

            helpers.append({
                "helper_id": helper_info["id"] or helper_info["helper_id"],
                "helper_ref": helper_info.get("helper_ref") or helper_info["path"],  # already normalized to helpers/
                "helper_source": spec["helper"],
                "file": spec["target"],
                "line": spec["line"],
            })

        git_mode = "changed" if args.use_git else "tracked"

        if args.use_git:
            from dennis.utils import is_git_repo

            if not is_git_repo(source_dir):
                raise SystemExit("[Dennis] --use-git requires a git repository.")

        excluded_langs = set()

        if args.exclude_lang:
            excluded_langs = {
                lang.strip() for lang in args.exclude_lang.split(",")
            }

        result = generate_plan(
            source_dir,
            dict_path,
            helpers=helpers,
            git_mode=git_mode,
            lang=args.lang,
            exclude_langs=excluded_langs,
            scan_only=getattr(args, "scan", False)
        )

        if getattr(args, "scan", False):
            scan_ts = ts()

            scan_path = Path(f"scan-result-{scan_ts}.obad.json")

            scan_payload = {
                "meta": {
                    "format": "obad",
                    "version": 1,
                    "generated_at": scan_ts,
                    "project_root": str(source_dir.resolve()),
                    "git_mode": git_mode,
                },
                "findings": result,
            }

            with open(scan_path, "w", encoding="utf-8") as f:
                json.dump(
                    scan_payload,
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            print(f"[Dennis] Scan written → {scan_path}")

            print(
                json.dumps(
                    scan_payload,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            return

        plan = result

        if args.scan:
            print(
                json.dumps(
                    result,
                    indent=2,
                    ensure_ascii=False
                )
            )
            return

        from dennis.core.serialize import dump_json
        from dennis.core.csvio import write_csv_from_plan
        import copy

        with open(output, "w", encoding="utf-8") as f:
            dump_json(plan, f)

        import copy
        csv_path = output.with_suffix(".csv")
        # print("[DEBUG BEFORE CSV]", plan["changes"][-2:])

        write_csv_from_plan(copy.deepcopy(plan), csv_path)

        # print("[DEBUG AFTER CSV]", plan["changes"][-2:])

        print(f"Plan written → {output}")
        print(f"CSV written  → {csv_path}")
        print(f"Plan hash: {canonical_hash(plan)}")

        # ----------------------------------------
        # GENERATE EXPECTED DIFF (canonical form)
        # ----------------------------------------
        try:
            # Create .dennis output directory
            dennis_dir = Path(".dennis")
            dennis_dir.mkdir(exist_ok=True)

            # Generate expected diff with source snapshot
            expected_diff = generate_planned_diff(plan, base_dir=source_dir)

            # Validate expected diff
            if not validate_diff_artifact(expected_diff):
                raise ValueError("Generated expected diff is invalid")

            if plan.get("changes") and not expected_diff["payload"]["files"]:
                print("[ERROR] Expected diff is empty — check base_dir alignment")
                raise SystemExit(1)

            # Save both artifacts with consistent naming
            timestamp = ts()
            plan_artifact_path = dennis_dir / f"dennis-plan-{timestamp}.json"
            expected_artifact_path = dennis_dir / f"dennis-expected-{timestamp}.json"

            with open(plan_artifact_path, "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2)

            with open(expected_artifact_path, "w", encoding="utf-8") as f:
                json.dump(expected_diff, f, indent=2)

            # Print statistics
            file_count = len(expected_diff["payload"]["files"])
            change_count = sum(len(f["changes"]) for f in expected_diff["payload"]["files"])

            print("\n[Dennis] Canonical Diff Generated")
            print(f"  Intent   → {plan_artifact_path}")
            print(f"  Expected → {expected_artifact_path}")
            print(f"  Files: {file_count}, Changes: {change_count}")
            print(f"  Expected hash: {diff_hash(expected_diff)}")

        except Exception as e:
            print(f"[WARNING] Could not generate expected diff: {e}")
            import traceback
            traceback.print_exc()

        return

    # --------------------------------------------------------
    # ENCRYPT
    # --------------------------------------------------------
    elif args.command == "encrypt":

        from dennis.dex.crypto import encrypt_dex

        out = encrypt_dex(args.artifact, args.out)

        print(f"Encrypted → {out}")


    # --------------------------------------------------------
    # DECRYPT
    # --------------------------------------------------------
    elif args.command == "decrypt":

        from dennis.dex.crypto import decrypt_xdex

        out = decrypt_xdex(args.artifact, args.out)

        print(f"Decrypted → {out}")

    # --------------------------------------------------------
    # REGISTRY COMMANDS
    # --------------------------------------------------------
    elif args.command == "registry":

        import urllib.request
        import json

        if args.registry_command == "add":

            url = args.remote.rstrip("/") + api_prefix + "/registry/remotes"

            payload = json.dumps({"url": args.url}).encode()

            req = urllib.request.Request(
                url,
                data=payload,
                method="POST",
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())

            print("Remote registry added:")
            print(data)

        elif args.registry_command == "list":

            url = args.remote.rstrip("/") + api_prefix + "/registry/remotes"

            with urllib.request.urlopen(url) as resp:
                data = json.loads(resp.read())

            remotes = data.get("remotes", [])

            if not remotes:
                print("No remote registries configured.")
                return

            print("\nRemote registries\n-----------------\n")

            for r in remotes:
                print(f"{r.get('name','?'):20} {r.get('url')}")

        elif args.registry_command == "sync":

            url = args.remote.rstrip("/") + api_prefix + "/registry/sync"

            req = urllib.request.Request(url, method="POST")

            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())

            print("Federation sync started")
            print(data)
    
    # --------------------------------------------------------
    # USER COMMANDS
    # --------------------------------------------------------
    
    elif args.command == "user":

        if args.user_command == "create":

            if not server:
                raise SystemExit("Server not configured. Use --server or set DENNIS_SERVER")

            url = f"{server.rstrip('/')}{api_prefix}/users"

            payload = {
                "email": args.email
            }

            try:
                resp = requests.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if resp.status_code not in (200, 201):
                    raise SystemExit(f"Error: {resp.text}")

                data = resp.json()

                print("✔ User created")
                print(f"Email: {data.get('email', args.email)}")

            except Exception as e:
                raise SystemExit(f"Error creating user: {e}")
        
        elif args.user_command == "verify":

            if not server:
                raise SystemExit("Server not configured")

            url = f"{server.rstrip('/')}{api_prefix}/auth/verify/{args.token}"

            try:
                resp = requests.get(url)

                if resp.status_code != 200:
                    raise SystemExit(f"Verification failed: {resp.text}")

                print("✔ Email verified successfully")

            except Exception as e:
                raise SystemExit(f"Error verifying user: {e}")

    elif args.command == "identity":
        from dennis.forge.config import load_config, save_config

        cfg = load_config()
        active_name = cfg.get("identity", {}).get("active")

        if args.identity_command == "use":
            name = args.name
            _, pub_path = resolve_identity_paths(name)
            identity = load_identity(pub_path)

            save_config({
                "identity": {
                    "active": name
                }
            })

            print(f"[Dennis] Active identity set to: {name} ({identity['derived_key_id']})")
            return

        elif args.identity_command == "current":
            if not active_name:
                raise SystemExit("No active identity. Use: dennis identity use <key>")

            _, pub_path = resolve_identity_paths(active_name)
            identity = load_identity(pub_path)

            print(f"name: {active_name}")
            print(f"id: {identity['derived_key_id']}")
            print(f"key: ed25519:{identity['derived_key_id']}")
            return

        elif args.identity_command == "list":
            keys_dir = Path.home() / ".dennis" / "keys"
            pub_files = sorted(keys_dir.glob("*.pub")) if keys_dir.exists() else []

            if not pub_files:
                print("No identities found.")
                return

            for pub_path in pub_files:
                name = pub_path.stem
                marker = "*" if name == active_name else " "
                try:
                    identity = load_identity(pub_path)
                    derived_key_id = identity["derived_key_id"]
                except SystemExit:
                    derived_key_id = "invalid"

                print(f"{marker} {name:<10} {derived_key_id}")
            return

    elif args.command == "whoami":

        cfg = load_config()

        email = cfg.get("auth", {}).get("email")
        active_name = cfg.get("identity", {}).get("active")

        if not active_name:
            print("No active identity. Use: dennis identity use <key>")
            return

        _, pub_path = resolve_identity_paths(active_name)
        identity = load_identity(pub_path)

        if email:
            print(email)

        print(f"name: {active_name}")
        print(f"id: {identity['derived_key_id']}")
        print(f"key: ed25519:{identity['derived_key_id']}")

    # --------------------------------------------------------
    # PROJECTS
    # --------------------------------------------------------

    elif args.command == "projects":
        pass  # handled in register_projects_commands
        

    # --------------------------------------------------------
    # DEX COMMANDS
    # --------------------------------------------------------
    elif args.command == "dex":

        import json

        if args.dex_command == "sign":
            from dennis.dex.sign import sign_dex
            from dennis.forge.config import load_config

            artifact = args.artifact
            key_id = args.key_id

            # Invariant: --key always overrides active identity.
            if args.key:
                key_path = args.key
            else:
                cfg = load_config()
                active_name = cfg.get("identity", {}).get("active")
                if not active_name:
                    raise SystemExit("No active identity set. Use:\n  dennis identity use <key>")

                key_path, pub_path = resolve_identity_paths(active_name)

            # Signing is fully handled inside sign_dex
            sign_dex(artifact, key_path, key_id=key_id)

            # Resolve derived identity for output consistency
            if key_id:
                reported_key_id = key_id
            else:
                from nacl.signing import SigningKey
                import getpass
                from nacl.secret import SecretBox
                from nacl.pwhash import argon2id

                with open(key_path, "rb") as f:
                    header = f.readline()
                    salt = f.read(argon2id.SALTBYTES)
                    encrypted = f.read()

                password = getpass.getpass("Enter passphrase (for reporting only): ")

                key = argon2id.kdf(
                    SecretBox.KEY_SIZE,
                    password.encode(),
                    salt,
                    opslimit=argon2id.OPSLIMIT_MODERATE,
                    memlimit=argon2id.MEMLIMIT_MODERATE,
                )

                box = SecretBox(key)
                private_bytes = box.decrypt(encrypted)
                signing_key = SigningKey(private_bytes)
                verify_key = signing_key.verify_key

                reported_key_id = derive_key_id_from_public_key_bytes(verify_key.encode())

            print(json.dumps({
                "success": True,
                "message": f"Signed: {artifact}",
                "key_id": key_id or reported_key_id
            }, indent=2))

            return

        elif args.dex_command == "verify":
            from dennis.core.verification import analyze_signatures
            import json

            artifact = args.artifact
            result = analyze_signatures(artifact)

            print(json.dumps(result, indent=2))

            raise SystemExit(0 if result["accepted"] else 1)


    # --------------------------------------------------------
    # HASH
    # --------------------------------------------------------
    elif args.command == "hash":
        from dennis.forge.hash.canonical import canonical_hash
        from pathlib import Path
        import json
        

        obj = json.loads(Path(args.file).read_text())
        print(canonical_hash(obj))


    # --------------------------------------------------------
    # PUSH
    # --------------------------------------------------------
    elif args.command == "push":
        import urllib.request
        from dennis.forge.hash.canonical import canonical_hash
        from datetime import datetime
        import json

        plan = json.loads(Path(args.plan).read_text())
        plan_hash = canonical_hash(plan)

        url = args.remote.rstrip("/") + api_prefix + "/plan"
        req = urllib.request.Request(
            url,
            data=json.dumps(plan).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())

        print(f"Pushed plan {result['hash']}")

        # ---------- AUTO QR ----------
        if args.qr:
            import datetime
            from dennis.qr.encode import generate_ascii_qr, generate_png_qr
            out_dir = Path(args.qr_path) if args.qr_path else Path(args.plan).parent
            out_dir.mkdir(parents=True, exist_ok=True)

            ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M")

            ascii_qr = generate_ascii_qr(plan_hash) or ""
            
            txt = out_dir / f"dennis-qr-{plan_hash[:8]}-{ts}.txt"
            txt.write_text(ascii_qr)

            png = out_dir / f"dennis-qr-{plan_hash[:8]}-{ts}.png"
            generate_png_qr(plan_hash, str(png))

            print("QR artifacts:")
            print(f"  {txt}")
            print(f"  {png}")

    # --------------------------------------------------------
    # QR GENERATION
    # --------------------------------------------------------
    elif args.command == "qr":
        from dennis.qr.encode import make_qr_uri, generate_ascii_qr, generate_png_qr
        from dennis.forge.hash.canonical import canonical_hash
        from pathlib import Path
        import json

        value = args.hash.strip()
        p = Path(value)

        # ----------------------------------------------------
        # File input → auto-hash
        # ----------------------------------------------------
        if p.exists():
            try:
                obj = json.loads(p.read_text())
            except Exception as e:
                raise SystemExit(f"Not a valid Dennis plan (expected JSON plan): {p} ({e})")

            plan_hash = canonical_hash(obj)
            print(f"Computed hash: {plan_hash}")

        # ----------------------------------------------------
        # Raw hash input
        # ----------------------------------------------------
        else:
            plan_hash = value

        # ----------------------------------------------------
        # Generate QR
        # ----------------------------------------------------
        uri = make_qr_uri(plan_hash)
        print(f"URI: {uri}")

        ascii_qr = generate_ascii_qr(plan_hash)
        print(ascii_qr)

        if getattr(args, "png", None):
            generate_png_qr(plan_hash, args.png)
            print(f"\nPNG saved to: {args.png}")

    # --------------------------------------------------------
    # SCAN QR
    # --------------------------------------------------------
    elif args.command == "scan-qr":
        if args.ascii:
            text = Path(args.from_file).read_text()
            uri = extract_uri_from_ascii(text)

        elif args.image:
            uri = extract_uri_from_image(args.from_file)

        else:
            raise SystemExit("Specify --ascii or --image")

        print("DFP URI:")
        print(uri)

        parsed = parse_dfp_uri(uri)
        print("\nParsed:")
        for k, v in parsed.items():
            print(f"{k}: {v}")

            
    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------
    elif args.command == "search":
        import urllib.request
        import urllib.parse
        import json

        params = {
            "limit": args.limit,
            "offset": args.offset,
        }

        if args.payload_type:
            params["payload_type"] = args.payload_type

        if args.hash_prefix:
            params["hash"] = args.hash_prefix

        query = urllib.parse.urlencode(params)

        url = args.remote.rstrip("/") + api_prefix + "/artifacts?" + query

        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())

        artifacts = data.get("artifacts", [])

        if not artifacts:
            print("No artifacts found.")
            return

        for a in artifacts:
            print(
                f"{a['artifact_hash']}  "
                f"{a.get('payload_type','?')}  "
                f"{a.get('created_at','')}"
            )

    # --------------------------------------------------------
    # PUBLISH
    # --------------------------------------------------------
    elif args.command == "publish":
        import urllib.request
        import uuid
        import json
        import subprocess
        import sys
        import os

        from dennis.forge.config import load_config

        artifact_path = Path(args.artifact)

        if not artifact_path.exists():
            raise SystemExit(f"Artifact not found: {artifact_path}")

        # ----------------------------------------
        # 1. VALIDATE PLAN
        # ----------------------------------------
        print("[Dennis] Validating plan...")

        vp = subprocess.run(
            ["dennis", "validate-plan", str(artifact_path)],
            capture_output=True,
            text=True
        )

        if vp.returncode != 0:
            print(vp.stderr)
            raise SystemExit("validate-plan failed")

        vp_json = json.loads(vp.stdout)

        if not vp_json.get("valid"):
            print(json.dumps(vp_json, indent=2))
            raise SystemExit("❌ Plan validation failed")

        print("✔ Plan valid")

        # ----------------------------------------
        # 2. VERIFY SIGNATURE
        # ----------------------------------------
        print("[Dennis] Verifying artifact...")

        vf = subprocess.run(
            ["dennis", "dex", "verify", str(artifact_path)],
            capture_output=True,
            text=True
        )

        if vf.returncode != 0:
            print(vf.stderr)
            raise SystemExit("verify failed")

        vf_json = json.loads(vf.stdout)

        if not vf_json.get("verified"):
            print(json.dumps(vf_json, indent=2))
            raise SystemExit("❌ Artifact is not properly signed")

        print("✔ Signature valid")

        # ----------------------------------------
        # 3. LOAD CONFIG (AUTH)
        # ----------------------------------------
        config = load_config()
        token = config.get("auth", {}).get("token")
        
        if not server:
            raise SystemExit("No server configured")

        if not token:
            raise SystemExit("Not authenticated. Please run: dennis login")

        # url = server.rstrip("/") + api_prefix + "/artifacts/upload"
        url = server.rstrip("/") + api_prefix + "/artifacts"
        
        
        # ----------------------------------------
        # 4 & 5: BUILD MULTIPART REQUEST
        # ----------------------------------------

        url = f"{server.rstrip('/')}{api_prefix}/artifacts"
        # print("DEBUG URL:", url)

        try:
            with open(artifact_path, "rb") as f:
                files = {
                    "file": (artifact_path.name, f, "application/octet-stream")
                }

                headers = {
                    "Authorization": f"Bearer {token}"
                }

                resp = requests.post(url, headers=headers, files=files)

            if resp.status_code not in (200, 201):
                raise SystemExit(f"Upload failed: {resp.text}")

            result = resp.json()

        except Exception as e:
            raise SystemExit(f"Upload failed: {str(e)}")

        # ----------------------------------------
        # 6. OUTPUT
        # ----------------------------------------
        status = result.get("status")
        artifact_hash = result.get("artifact_hash")

        if status == "exists":
            print("⚠ Artifact already exists with following hash:")
            print(f"  {artifact_hash}")
            return

        elif status == "ok":
            print(f"✔ Published artifact → {artifact_hash}")

        else:
            # fallback safety
            print(f"✔ Published artifact → {artifact_hash}")

    # --------------------------------------------------------
    # PULL
    # --------------------------------------------------------
    elif args.command == "pull":
        import urllib.request

        artifact_hash = args.hash.strip()

        if len(artifact_hash) != 64:
            raise SystemExit("Error: full artifact hash required (64 hex chars)")

        url = args.remote.rstrip("/") + api_prefix + f"/artifacts/{artifact_hash}"
        # print("DEBUG URL:", url)
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
            disposition = resp.headers.get("Content-Disposition")

        if disposition and "filename=" in disposition:
            filename = disposition.split("filename=")[1].strip('"')
        else:
            filename = f"{artifact_hash}.dex"

        Path(filename).write_bytes(data)

        print(f"Downloaded → {filename}")

    # --------------------------------------------------------
    # ARCHITECTURE  
    # --------------------------------------------------------
    
    elif args.command == "architecture":

        if (
            args.architecture_command
            == "scan"
        ):

            from dennis.architecture.scan import (
                run_architecture_scan
            )

            run_architecture_scan(
                source_path=args.path,
                output_format=args.output,
            )

            return

    # --------------------------------------------------------
    # INSPECT
    # --------------------------------------------------------
    elif args.command == "inspect":

        import urllib.request
        import json
        import gzip
        import tarfile
        import io

        target = args.target.strip()

        # --------------------------------------------------------
        # LOCAL FILE INSPECTION
        # --------------------------------------------------------

        if Path(target).exists():
            path = Path(target)

            if not path.is_file():
                raise SystemExit(f"Artifact file not found: {path}")

            if path.suffix == ".json":
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        artifact = json.load(f)

                    meta = artifact.get("meta", {})

                    if meta.get("format") == "goal-discovery":

                        if args.specs:

                            from dennis.goals.specs import (
                                validate_goal_discovery,
                                discover_specs,
                            )

                            validate_goal_discovery(artifact)

                            result = discover_specs(artifact)

                            result["lineage"] = {
                                "derived_from": [
                                    path.name
                                ]
                            }

                            print(
                                json.dumps(
                                    result,
                                    indent=2,
                                    ensure_ascii=False,
                                )
                            )

                            return

                    if meta.get("format") == "obad":

                        if args.goals:

                            from dennis.goals.discovery import (
                                validate_obad,
                                discover_goals,
                            )

                            validate_obad(artifact)
                            
                            result = discover_goals(artifact)
                            result["lineage"] = {
                                "derived_from": [
                                    path.name
                                ]
                            }
                            print(
                                json.dumps(
                                    result,
                                    indent=2,
                                    ensure_ascii=False,
                                )
                            )

                            return
                except Exception:
                    pass

            # --------------------------------------------------------
            # Detect encrypted artifact
            # --------------------------------------------------------

            import hashlib

            with open(path, "rb") as f:
                magic = f.read(5)

                if magic == b"XDEX1":

                    header_hash = f.read(32)
                    salt = f.read(16)

                    expected_hash = hashlib.sha256(magic + salt).digest()

                    print("\n[ Dennis ]")

                    if header_hash != expected_hash:
                        print("XDEX header is INVALID. The file may be corrupted or tampered with.")
                        raise SystemExit(1)

                    print("XDEX artifact detected")
                    print("Payload: encrypted")
                    print("Decryption required for full inspection")

                    return
            from dennis.core.verification import analyze_signatures

            analysis = analyze_signatures(path)
            # --------------------------------------------------------
            # Inspect normal DEX
            # --------------------------------------------------------

            try:

                with gzip.open(path, "rb") as gz:
                    tar_bytes = gz.read()

                tar_buffer = io.BytesIO(tar_bytes)

                files = {}

                with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
                    for m in tar.getmembers():
                        f = tar.extractfile(m)
                        if f:
                            files[m.name] = f.read()

                manifest = json.loads(files["manifest.json"])
                # ----------------------------------------
                # Extract embedded spec (intent)
                # ----------------------------------------

                intent = None

                spec_bytes = files.get("meta/spec.json")

                if spec_bytes:
                    try:
                        intent = json.loads(spec_bytes)
                    except Exception:
                        intent = {
                            "error": "Failed to parse spec.json"
                        }

                    if intent:
                        print("\nIntent")
                        print("------")

                        print(f"Mode:        {intent.get('mode')}")
                        print(f"Root:        {intent.get('root')}")

                        if intent.get("options"):
                            print(f"Options:     {intent['options']}")

                        if intent.get("helpers"):
                            print("\nHelpers:")
                            for h in intent["helpers"]:
                                print(f"  - {h['file']} → {h['target']}:{h['line']}")
                
                # ----------------------------------------
                # Extract embedded scope metadata
                # ----------------------------------------

                scope_data = None

                scope_bytes = files.get(
                    "meta/dexscope.json"
                )

                if scope_bytes:
                    try:
                        scope_data = json.loads(
                            scope_bytes
                        )
                    except Exception:
                        scope_data = {
                            "error": (
                                "Failed to parse "
                                "dexscope.json"
                            )
                        }

                from dennis.dex.sign import verify_manifest_signatures
                import base64

                plan_bytes = files.get("payload/plan.json")
                patch_info = {}

                if plan_bytes:
                    try:
                        plan = json.loads(plan_bytes)
                        patches = plan.get("patches", {})

                        raw_changes = plan.get("changes", [])

                        operations = []

                        for change in raw_changes:

                            op = {
                                "type": change.get("type", "replace"),
                                "file": change.get("file"),
                                "line": change.get("line"),
                            }

                            # ----------------------------------------
                            # Optional semantic fields
                            # ----------------------------------------

                            optional_fields = [
                                "original",
                                "replacement",
                                "token",
                                "helper_id",
                                "helper_ref",
                                "helper_source",
                            ]

                            for field in optional_fields:
                                if field in change:
                                    op[field] = change[field]

                            operations.append(op)

                        grouped_files = {}

                        for op in operations:

                            file_path = op["file"]

                            if file_path not in grouped_files:
                                grouped_files[file_path] = {
                                    "path": file_path,
                                    "operations": []
                                }

                            grouped_files[file_path]["operations"].append(op)

                        files_list = list(grouped_files.values())

                        patch_info = {
                            "summary": {
                                "helpers": len(patches.get("helpers", [])),
                                "remove_helpers": len(patches.get("remove_helpers", []))
                            },
                            "operations": operations,
                            "files": files_list,
                        }
                    except Exception:
                        patch_info = {}
                
                    created_at = intent.get("created_at") if intent else None

                    if created_at:
                        print(f"\nCreated at:  {created_at}")

                signatures = manifest.get("signatures", [])
                enriched_signatures = []

                for s in signatures:
                    key_id = s.get("key_id")
                    s_out = dict(s)

                    pubkey_bytes = files.get(f"signatures/{key_id}.pub")
                    if pubkey_bytes:
                        s_out["public_key"] = base64.b64encode(pubkey_bytes).decode("utf-8")

                    enriched_signatures.append(s_out)

                verification_entries = verify_manifest_signatures(manifest, files)

                import hashlib

                identity_map = {}
                for s in enriched_signatures:
                    declared_key_id = s.get("key_id")
                    public_key_b64 = s.get("public_key")

                    derived_key_id = None
                    matches = False
                    identity_status = "anonymous"

                    if public_key_b64:
                        try:
                            pub_bytes = base64.b64decode(public_key_b64)
                            derived_key_id = hashlib.sha256(pub_bytes).hexdigest()[:16]
                        except Exception:
                            derived_key_id = None

                    if declared_key_id is None:
                        identity_status = "anonymous"
                    elif derived_key_id is not None and declared_key_id == derived_key_id:
                        identity_status = "canonical"
                        matches = True
                    else:
                        identity_status = "legacy"

                    identity_map[declared_key_id] = {
                        "derived_key_id": derived_key_id,
                        "matches": matches,
                        "identity_status": identity_status,
                    }

                enriched_verification_entries = []
                for v in verification_entries:
                    declared_key_id = v.get("key_id")
                    identity_info = identity_map.get(declared_key_id, {
                        "derived_key_id": None,
                        "matches": False,
                        "identity_status": "anonymous" if declared_key_id is None else "legacy",
                    })

                    merged = dict(v)
                    merged.update(identity_info)
                    enriched_verification_entries.append(merged)

                verification = {
                    "status": "valid" if analysis["verified"] else "invalid",
                    "accepted": analysis["accepted"],
                    "policy": analysis["policy"],
                    "signatures": []
                }

                for entry in enriched_verification_entries:
                    key_id = entry.get("key_id")

                    # find matching trust info from analysis
                    trust_info = next(
                        (s for s in analysis["details"] if s["key_id"] == key_id),
                        {}
                    )

                    merged = dict(entry)
                    merged["trusted"] = trust_info.get("trusted", False)

                    verification["signatures"].append(merged)

                data = {
                    "protocol": {
                        "version": 1,
                        "deprecated": [
                            "patches.operations"
                        ]
                    },
                    "artifact": {
                        "hash": "local-file",
                        "path": str(path),
                    },
                    "meta": manifest.get("meta", {}),
                    "scope": scope_data if scope_data else {},
                    "payload": {
                        "type": manifest.get("payload", {}).get("type"),
                        "hash": manifest.get("payload", {}).get("hash", {}).get("value"),
                        "size_bytes": len(files.get("payload/plan.json", b"")),
                    },
                    "lineage": manifest.get("lineage", {}),
                    "signatures": enriched_signatures,
                    "verification": verification,
                    "intent": intent if intent else {},
                    "patches": patch_info if patch_info else {"summary": {"helpers": 0, "remove_helpers": 0}, "operations": []},
                    "diff": {
                        "files": []
                    },
                }

            except Exception as e:
                raise SystemExit(
                    f"Not a Dennis artifact or unsupported file: {repr(e)}"
                )

        # --------------------------------------------------------
        # REGISTRY INSPECTION
        # --------------------------------------------------------

        else:

            artifact_hash = target

            if len(artifact_hash) != 64:
                raise SystemExit("Error: full artifact hash required (64 hex chars)")

            url = args.remote.rstrip("/") + api_prefix + f"/artifacts/{artifact_hash}/metadata"

            import urllib.error

            try:
                with urllib.request.urlopen(url) as resp:
                    data = json.loads(resp.read())

            except urllib.error.URLError:

                print("\n[Dennis] Unable to reach registry.")
                print(f"Attempted URL: {url}")

                print("\n[Dennis] If you want to inspect a local artifact, use:")
                print("  dennis inspect <artifact.dex>")

                print("\n[Dennis] To inspect a registry artifact, specify a registry:")
                print("  dennis inspect <hash> --remote http://localhost:8000")

                raise SystemExit(1)

        # --------------------------------------------------------
        # OUTPUT
        # --------------------------------------------------------

        if args.validate_schema:

            import jsonschema

            schema_path = (
                Path(__file__).parent
                / "schemas"
                / "inspect.v1.schema.json"
            )

            with open(schema_path, "r", encoding="utf-8") as f:
                inspect_schema = json.load(f)

        if args.validate_schema:
            jsonschema.validate(
                instance=data,
                schema=inspect_schema
            )
        
        if args.format == "json":
            print(json.dumps(data, indent=2))
            return

        print("\nArtifact")
        print("--------")
        print(f"Hash:        {data.get('artifact', {}).get('hash')}")
        print(f"Path:        {data.get('artifact', {}).get('path')}")

        meta = data.get("meta", {})
        print("\nMeta")
        print("----")
        print(f"Format:      {meta.get('format')}")
        print(f"Version:     {meta.get('version')}")
        print(f"Created:     {meta.get('created_at')}")
        print(f"Created by:  {meta.get('created_by')}")

        payload = data.get("payload", {})
        print("\nPayload")
        print("-------")
        print(f"Type:        {payload.get('type')}")
        print(f"Hash:        {payload.get('hash')}")
        print(f"Size:        {payload.get('size_bytes')}")

        lineage = data.get("lineage", {})
        print("\nLineage")
        print("-------")
        print(f"Type:        {lineage.get('type')}")
        print(f"Lineage ID:  {lineage.get('lineage_id')}")
        print(f"Parent:      {lineage.get('parent')}")

        scope = data.get("scope", {})

        if scope:

            print("\nScope")
            print("-----")

            active = scope.get(
                "active",
                []
            )

            inactive = scope.get(
                "inactive",
                []
            )

            comments = scope.get(
                "comments",
                []
            )

            print(
                f"Active:      {len(active)}"
            )

            print(
                f"Inactive:    {len(inactive)}"
            )

            print(
                f"Comments:    {len(comments)}"
            )

            if inactive:

                print("\nExcluded:")

                for item in inactive:
                    print(f"  {item}")

        sigs = data.get("signatures", [])

        print("\nSignatures")
        print("----------")

        if not sigs:
            print("None")
        else:
            for s in sigs:
                verification = data.get("verification", {})
                sig_details = verification.get("signatures", [])

                def get_trust_marker(key_id):
                    for s in sig_details:
                        if s.get("key_id") == key_id:
                            return "✔" if s.get("trusted") else "✖"
                    return "?"
        
        # --------------------------------------------------------
        # VERIFICATION (human-readable)
        # --------------------------------------------------------

        verification = data.get("verification", {})
        sig_details = verification.get("signatures", [])

        def get_trust_marker(key_id):
            for s in sig_details:
                if s.get("key_id") == key_id:
                    return "✔" if s.get("trusted") else "✖"
            return "?"

        for s in sigs:
            key_id = s.get("key_id")
            trust = get_trust_marker(key_id)

            print(
                f"{key_id}  "
                f"{s.get('algorithm')}  "
                f"{s.get('created_at')}  "
                f"[trusted: {trust}]"
            )

        if verification:
            print("\nVerification")
            print("------------")

            status = verification.get("status")
            accepted = verification.get("accepted")
            policy = verification.get("policy")

            # nicer boolean display
            accepted_str = "✔ yes" if accepted else "✖ no"

            status_str = "✔ valid" if status == "valid" else "✖ invalid"
            print(f"Status:      {status_str}")
            print(f"Accepted:    {accepted_str}")
            print(f"Policy:      {policy}")

            sig_details = verification.get("signatures", [])

            if sig_details:
                valid_count = sum(1 for s in sig_details if s.get("valid"))
                trusted_count = sum(1 for s in sig_details if s.get("valid") and s.get("trusted"))

                print(f"Valid sigs:  {valid_count}")
                print(f"Trusted:     {trusted_count}/{valid_count}")

                print("\nSignature Details")
                print("-----------------")

                for s in sig_details:
                    key_id = s.get("key_id")

                    valid = "✔" if s.get("valid") else "✖"
                    trusted = "✔" if s.get("trusted") else "✖"
                    identity = s.get("identity_status", "?")

                    print(f"{key_id}")
                    print(f"  valid:    {valid}")
                    print(f"  trusted:  {trusted}")
                    print(f"  identity: {identity}")

            message = verification.get("message")
            if message:
                print("\nDecision")
                print("--------")
                print(message)

        registry = data.get("registry")

        if registry:

            print("\nRegistry")
            print("--------")

            origin = registry.get("origin_registry") or "local"
            chain = registry.get("chain_status")
            stored = registry.get("stored_at")

            print(f"Origin:     {origin}")
            print(f"Chain:      {chain}")
            print(f"Stored:     {stored}")

        if patch_info:
            summary = patch_info.get("summary", {})
            print("\nPatches")
            print("-------")
            if summary.get("helpers"):
                print(f"Helpers:     {summary['helpers']}")
            if summary.get("remove_helpers"):
                print(f"Removals:    {summary['remove_helpers']}")

    # --------------------------------------------------------
    # SIGNATURES
    # --------------------------------------------------------
    elif args.command == "signatures":
        import urllib.request
        import json

        url = args.remote.rstrip("/") + api_prefix + f"/artifacts/{args.hash}/signatures"

        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())

        sigs = data.get("signatures", [])

        if not sigs:
            print("No signatures.")
            return

        for s in sigs:
            print(
                f"{s.get('key_id','?')}  "
                f"{s.get('algorithm','?')}  "
                f"{s.get('created_at','')}"
            )

    # --------------------------------------------------------
    # LINEAGE
    # --------------------------------------------------------
    elif args.command == "lineage":
        import json
        import urllib.request
        url = args.remote.rstrip("/") + api_prefix + f"/artifacts/{args.hash}/lineage"

        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())

        chain = data.get("lineage", [])

        for i, a in enumerate(chain):

            prefix = "└─ " if i else ""

            print(
                f"{prefix}{a['artifact_hash']}  "
                f"{a.get('payload_type','?')}  "
                f"{a.get('created_at','')}"
            )

    # --------------------------------------------------------
    # DIFF
    # --------------------------------------------------------
    elif args.command == "diff":
        from dennis.dex.diff import diff_dex
        import json

        result = diff_dex(
            args.artifact_a,
            args.artifact_b,
            ignore_semantics=args.ignore_semantics
        )

        print(json.dumps(result, indent=2))



    elif args.command == "git-diff":

        import tempfile, json
        from dennis.dex.pack import pack_dex
        from dennis.dex.canonical_diff import generate_observed_diff_git
        

        # ----------------------------------------
        # 1. GENERATE CANONICAL DIFF
        # ----------------------------------------
        artifact = generate_observed_diff_git()

        # Validate the artifact
        if not validate_diff_artifact(artifact):
            raise SystemExit("Generated diff does not conform to dennis.diff.v1 schema")

        # ----------------------------------------
        # 2. OUTPUT PATHS (LOCAL)
        # ----------------------------------------
        output_dir = Path.cwd() / ".dennis"
        output_dir.mkdir(exist_ok=True)

        json_path = output_dir / "diff.json"
        dex_path = output_dir / "diff.dex"

        # ----------------------------------------
        # 3. WRITE JSON
        # ----------------------------------------
        json_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

        # ----------------------------------------
        # 4. PACK DEX
        # ----------------------------------------
        pack_dex(
            payload_path=json_path,
            output_path=dex_path,
            payload_type="dennis.diff.v1"
        )

        # ----------------------------------------
        # 5. OUTPUT
        # ----------------------------------------
        print("✔ Diff artifact created locally:")
        print(f"  JSON → {json_path}")
        print(f"  DEX  → {dex_path}")
        print()
        print("Next step:")
        print(f"  dennis inspect {dex_path}")
        print(f"  dennis publish {dex_path}")

    elif args.command == "diff-directories":

        import json
        from dennis.dex.pack import pack_dex

        source_dir = Path(args.source_dir)
        target_dir = Path(args.target_dir)

        if not source_dir.exists() or not source_dir.is_dir():
            raise SystemExit(f"Source directory does not exist: {source_dir}")

        if not target_dir.exists() or not target_dir.is_dir():
            raise SystemExit(f"Target directory does not exist: {target_dir}")

        # ----------------------------------------
        # 1. GENERATE CANONICAL DIFF
        # ----------------------------------------
        artifact = generate_observed_diff_directories(source_dir, target_dir, verbose=args.verbose)

        if args.create_plan:
            from dennis.core.diff_to_plan import generate_plan_from_dirs

            plan = generate_plan_from_dirs(source_dir, target_dir)
            output_path = "dennis-plan-generated.json"

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2, ensure_ascii=False)

            print(f"[Dennis] Plan generated → {output_path}")

        # Validate the artifact
        if not validate_diff_artifact(artifact):
            raise SystemExit("Generated diff does not conform to dennis.diff.v1 schema")

        # ----------------------------------------
        # 2. OUTPUT PATHS (LOCAL)
        # ----------------------------------------
        output_dir = Path.cwd() / ".dennis"
        output_dir.mkdir(exist_ok=True)

        json_path = output_dir / "diff.json"
        dex_path = output_dir / "diff.dex"

        # ----------------------------------------
        # 3. WRITE JSON
        # ----------------------------------------
        json_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

        # ----------------------------------------
        # 4. PACK DEX
        # ----------------------------------------
        pack_dex(
            payload_path=json_path,
            output_path=dex_path,
            payload_type="dennis.diff.v1"
        )

        # ----------------------------------------
        # 5. OUTPUT
        # ----------------------------------------
        print("✔ Diff artifact created locally:")
        print(f"  JSON → {json_path}")
        print(f"  DEX  → {dex_path}")
        print()
        print("Next step:")
        print(f"  dennis inspect {dex_path}")
        print(f"  dennis publish {dex_path}")

    elif args.command == "compare":

        import json
        from dennis.dex.importer import import_dex
        from dennis.dex.canonical_diff import generate_reconciliation_diff
        from dennis.dex.pack import pack_dex

        planned_path = Path(args.planned_diff)
        observed_path = Path(args.observed_diff)

        if not planned_path.exists():
            raise SystemExit(f"Planned diff artifact not found: {planned_path}")

        if not observed_path.exists():
            raise SystemExit(f"Observed diff artifact not found: {observed_path}")

        # ----------------------------------------
        # 1. LOAD DIFF ARTIFACTS
        # ----------------------------------------
        planned_manifest, planned_payload = import_dex(planned_path)
        observed_manifest, observed_payload = import_dex(observed_path)

        planned_diff = json.loads(planned_payload)
        observed_diff = json.loads(observed_payload)

        # Validate types
        if planned_diff.get('type') != 'dennis.diff.v1':
            raise SystemExit(f"Planned artifact is not a diff: {planned_diff.get('type')}")

        if observed_diff.get('type') != 'dennis.diff.v1':
            raise SystemExit(f"Observed artifact is not a diff: {observed_diff.get('type')}")

        # ----------------------------------------
        # 2. GENERATE RECONCILIATION DIFF
        # ----------------------------------------
        reconciliation_diff = generate_reconciliation_diff(planned_diff, observed_diff)

        # ----------------------------------------
        # 3. OUTPUT PATHS (LOCAL)
        # ----------------------------------------
        output_dir = Path.cwd() / ".dennis"
        output_dir.mkdir(exist_ok=True)

        json_path = output_dir / "reconciliation.json"
        dex_path = output_dir / "reconciliation.dex"

        # ----------------------------------------
        # 4. WRITE JSON
        # ----------------------------------------
        json_path.write_text(json.dumps(reconciliation_diff, indent=2), encoding="utf-8")

        # ----------------------------------------
        # 5. PACK DEX
        # ----------------------------------------
        pack_dex(
            payload_path=json_path,
            output_path=dex_path,
            payload_type="dennis.diff.v1"
        )

        # ----------------------------------------
        # 6. OUTPUT SUMMARY
        # ----------------------------------------
        summary = reconciliation_diff['payload'].get('reconciliation_summary', {})
        print("✔ Reconciliation diff created:")
        print(f"  JSON → {json_path}")
        print(f"  DEX  → {dex_path}")
        print()
        print("Summary:")
        print(f"  Files: {summary.get('total_files', 0)}")
        print(f"  Matched changes: {summary.get('matched_changes', 0)}")
        print(f"  Missing changes: {summary.get('missing_changes', 0)}")
        print(f"  Unexpected changes: {summary.get('unexpected_changes', 0)}")
        print()
        print("Next step:")
        print(f"  dennis inspect {dex_path}")

    # --------------------------------------------------------
    # PACK
    # --------------------------------------------------------
    elif args.command == "pack":

        import json
        from dennis.dex.pack import pack_dex
        #from dennis.forge.hash.canonical import canonical_hash
        from dennis.core.hash import canonical_hash

        payload_path = Path(args.payload)
        output_path = Path(args.out)

        if not payload_path.exists():
            raise SystemExit(f"Payload file not found: {payload_path}")

        # load payload to compute hash
        payload = json.loads(payload_path.read_text())
        payload_hash = canonical_hash(payload)

        print("Forging artifact...")
        print(f"Payload hash: {payload_hash}")

        parent_manifest = None

        from dennis.dex.importer import import_dex

        # --------------------------------------------------------
        # 1. EXPLICIT PARENT (always wins)
        # --------------------------------------------------------
        if args.parent:
            parent_path = Path(args.parent)

            if not parent_path.exists():
                raise SystemExit(f"[Dennis] Parent artifact not found: {args.parent}")

            print("[Dennis] Using explicit parent:", parent_path)

            parent_manifest, _ = import_dex(parent_path)

        # --------------------------------------------------------
        # 2. IMPLICIT PARENT (context fallback)
        # --------------------------------------------------------
        else:
            ctx = load_context()

            if ctx and ctx.get("last_artifact_path"):
                parent_path = Path(ctx["last_artifact_path"])

                if parent_path.exists():
                    print("[Dennis] Using implicit parent from context:", parent_path)
                    parent_manifest, _ = import_dex(parent_path)
                else:
                    print("[Dennis] Context parent not found, ignoring context")
            else:
                print("[Dennis] No parent specified, creating root artifact")

        if args.parent and args.detached:
            raise SystemExit("[Dennis] Cannot use --parent and --detached together")

        output = pack_dex(
            payload_path=Path(args.payload),
            output_path=Path(args.out),
            payload_type=args.type,
            parent_manifest=parent_manifest,
            force_detached=args.detached
        )

        # --------------------------------------------------------
        # UPDATE CONTEXT
        # --------------------------------------------------------
        try:
            from dennis.dex.importer import import_dex

            manifest, _ = import_dex(output_path)

            lineage = manifest.get("lineage", {})

            save_context({
                "active_lineage_id": lineage.get("lineage_id"),
                "root_hash": lineage.get("lineage_id"),
                "last_artifact_path": str(output_path.resolve())
            })

            print("[Dennis] Context updated")

        except Exception as e:
            print("[Dennis] Warning: could not update context:", e)

        print(f"Artifact written → {output_path}")

    # --------------------------------------------------------
    # LINEAGE RESET
    # --------------------------------------------------------
    elif args.command == "lineage-reset":
        path = _context_path()
        if path.exists():
            path.unlink()
        print("[Dennis] Lineage context cleared")

    # --------------------------------------------------------
    # UNPACK
    # --------------------------------------------------------
    elif args.command == "unpack":

        import tarfile
        import gzip
        import io

        from pathlib import Path

        artifact = Path(args.artifact)

        out_dir = Path(args.out) if args.out else artifact.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        with gzip.open(artifact, "rb") as gz:
            tar_bytes = gz.read()

        tar_buffer = io.BytesIO(tar_bytes)

        with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
            tar.extractall(out_dir)

        print(f"Artifact extracted → {out_dir}")

    # --------------------------------------------------------
    # KEYGEN COMMAND
    # --------------------------------------------------------
    elif args.command == "keygen":

        from dennis.dex.keygen import generate_keypair

        generate_keypair()

    # --------------------------------------------------------
    # REHYDRATE
    # --------------------------------------------------------
    elif args.command == "rehydrate":

        import re
        from dennis.core.rehydrate import rehydrate
        from dennis.dex.importer import import_dex

        artifact = Path(args.artifact)
        out_dir = Path(args.out)

        out_dir.mkdir(parents=True, exist_ok=True)

        # ✅ FULL REHYDRATION (files + helpers)
        rehydrate(artifact, output_dir=out_dir)

        # ✅ THEN extract plan (for UX)
        manifest, payload_bytes = import_dex(artifact)
        plan = json.loads(payload_bytes)

        plan_path = out_dir / "rehydrated-plan.json"

        plan_path.write_text(
            json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
        )

        print(f"Plan restored → {plan_path}")

    elif args.command == "apply":

        from dennis.i18n.apply import apply_plan
        from dennis.dex.importer import import_dex
        import tempfile
        from pathlib import Path as _Path
        import json as _json

        plan_path = _Path(args.plan)


        if plan_path.suffix == ".dex":

            manifest, payload_bytes = import_dex(plan_path)

            # --------------------------------------------------------
            # LINEAGE ENFORCEMENT (CRITICAL)
            # --------------------------------------------------------

            def _context_path():
                return Path.home() / ".dennis" / "context.json"

            def get_active_lineage():
                path = _context_path()
                if not path.exists():
                    return None
                try:
                    return json.loads(path.read_text()).get("active_lineage_id")
                except Exception:
                    return None

            def save_active_lineage(lineage_id):
                ctx_dir = _context_path().parent
                ctx_dir.mkdir(parents=True, exist_ok=True)

                _context_path().write_text(_json.dumps({
                    "active_lineage_id": lineage_id,
                    "root_hash": lineage_id
                }, indent=2))

            lineage = manifest.get("lineage", {})
            artifact_lineage_id = lineage.get("lineage_id")
            artifact_type = lineage.get("type")

            active_lineage_id = get_active_lineage()

            print(f"[Dennis] Artifact lineage type: {artifact_type}")
            if artifact_lineage_id:
                print(f"[Dennis] Artifact lineage ID: {artifact_lineage_id}")

            # ----------------------------------------
            # DETACHED
            # ----------------------------------------

            if artifact_type == "detached" or not artifact_lineage_id:
                print("[Dennis] WARNING: Detached artifact detected")

                if not args.accept_detached:
                    raise SystemExit(
                        "[Dennis] ERROR: Detached artifact requires --accept-detached"
                    )

                print("[Dennis] Detached artifact explicitly accepted")

            # ----------------------------------------
            # FIRST RUN (BOOTSTRAP)
            # ----------------------------------------

            if active_lineage_id is None:

                if artifact_type == "detached":
                    raise SystemExit(
                        "[Dennis] ERROR: Cannot initialize lineage from detached artifact"
                    )

                print(f"[Dennis] Initializing lineage → {artifact_lineage_id}")
                save_active_lineage(artifact_lineage_id)

            # ----------------------------------------
            # LINEAGE MISMATCH
            # ----------------------------------------

            elif artifact_lineage_id != active_lineage_id:

                print("[Dennis] ERROR: Lineage mismatch")
                print(f"  Active:   {active_lineage_id}")
                print(f"  Artifact: {artifact_lineage_id}")

                if not args.accept_lineage:
                    raise SystemExit(
                        "[Dennis] Refusing to apply artifact from different lineage.\n"
                        "Use --accept-lineage <lineage_id> to override."
                    )

                if args.accept_lineage != artifact_lineage_id:
                    raise SystemExit(
                        "[Dennis] Provided lineage does not match artifact."
                    )

                print("[Dennis] WARNING: Lineage override accepted")

            # --------------------------------------------------------
            # APPLY (only after passing all checks)
            # --------------------------------------------------------

            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                tmp.write(payload_bytes)
                tmp_path = _Path(tmp.name)

            try:
                changes = apply_plan(
                    tmp_path,
                    confirm=args.confirm,
                    helper_mode=args.helper_mode,
                    artifact_policy=args.artifact_policy
                )
            finally:
                tmp_path.unlink(missing_ok=True)

        else:
            changes = apply_plan(
                    plan_path,
                    confirm=args.confirm,
                    helper_mode=args.helper_mode,
                    artifact_policy=args.artifact_policy
                )

    elif args.command == "dict":

        from dennis.i18n.csvio import (
            export_dictionary_to_csv,
            import_dictionary_from_csv
        )

        fmt = args.format

        if args.dict_command == "export":

            if fmt == "csv":
                export_dictionary_to_csv(
                    Path(args.dictionary),
                    Path(args.output)
                )
            else:
                raise SystemExit(f"Format not implemented yet: {fmt}")

        elif args.dict_command == "import":

            if fmt == "csv":
                import_dictionary_from_csv(
                    Path(args.input),
                    Path(args.dictionary)
                )
            else:
                raise SystemExit(f"Format not implemented yet: {fmt}")
            
    # --------------------------------------------------------
    # INVERT
    # --------------------------------------------------------

    elif args.command == "invert":
        cmd_invert(args.plan, stdout=args.stdout)
        return


    elif args.command == "install-plugin":

        import shutil
        from datetime import datetime
        from dennis.utils import (
            ensure_dennis_dirs,
            get_plugin_dir,
            get_dict_dir,
        )

        src = Path(args.file)

        if not src.exists():
            raise SystemExit(f"File not found: {src}")

        ensure_dennis_dirs()

        # ----------------------------------------
        # Decide destination
        # ----------------------------------------

        if src.suffix == ".py":
            dest_dir = get_plugin_dir()

        elif src.suffix == ".dict":
            dest_dir = get_dict_dir()

        else:
            raise SystemExit(
                f"Unsupported file type: {src.suffix} (only .py and .dict allowed)"
            )

        dest = dest_dir / src.name

        # ----------------------------------------
        # Handle existing file
        # ----------------------------------------

        if dest.exists():
            from dennis.utils import get_backup_dir
            from datetime import datetime

            backup_dir = get_backup_dir()
            timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M")

            kind = "plugin" if src.suffix == ".py" else "dict"

            backup_name = f"{kind}__{dest.name}.backup_{timestamp}"
            backup_path = backup_dir / backup_name

            shutil.move(dest, backup_path)

            print(f"[Dennis] Backup created: {backup_path}")

        # ----------------------------------------
        # Copy file
        # ----------------------------------------

        shutil.copy2(src, dest)

        print(f"[Dennis] Installed: {src.name}")
        print(f"[Dennis] Location: {dest}")

    elif args.command == "key":

        from dennis.core.keys import bootstrap_key, approve_key, list_keys

        if args.key_command == "bootstrap":
            bootstrap_key(Path(args.pub))

        elif args.key_command == "approve":
            approve_key(Path(args.pub), Path(args.signer))

        elif args.key_command == "list":
            list_keys()
        
        elif args.key_command == "debug-identity":
            debug_identity(args.pub)
            return

        else:
            raise SystemExit("Unknown key command")

    elif args.command == "login":
        import urllib.request
        import json
        import getpass

        from dennis.forge.config import save_config

        # ----------------------------------------
        # PASSWORD PROMPT (secure)
        # ----------------------------------------
        password = getpass.getpass("Password: ")

        server = args.server.rstrip("/")
        
        
        url = server + api_prefix + "/auth/login"

        payload = json.dumps({
            "email": args.email,
            "password": password
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(payload))
            }
        )

        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())

        except Exception as e:
            raise SystemExit(f"Login failed: {e}")

        token = result.get("access_token")

        if not token:
            raise SystemExit("Login failed: no token returned")

        save_config({
            "server": server,
            "auth": {
                "token": token
            }
        })

        if args.token:
            save_config({
                "server": server,
                "auth": {
                    "token": args.token
                }
            })

            print("✔ Token stored")
            return

        print("✔ Logged in successfully\n")
        print(token)


    elif args.command == "logout":
        from dennis.forge.config import load_config, save_config

        config = load_config()

        if "auth" in config:
            config["auth"] = {}

        save_config(config)

        print("✔ Logged out successfully")

    # --------------------------------------------------------
    # DIFF COMMANDS
    # --------------------------------------------------------
    elif args.command == "git-diff":
        from dennis.dex.canonical_diff import generate_observed_diff_git
        from dennis.utils.time import timestamp
        import json


        print("Generating diff from git changes...")
        diff_artifact = generate_observed_diff_git()

        if not diff_artifact['payload']['files']:
            print("No changes detected in git.")
            return

        now = timestamp()
        filename = f"diff-git-{now}.json"

        with open(filename, 'w') as f:
            json.dump(diff_artifact, f, indent=2)

        file_count = len(diff_artifact['payload']['files'])
        change_count = sum(len(f['changes']) for f in diff_artifact['payload']['files'])

        print(f"✓ Git diff generated: {file_count} files, {change_count} changes")
        print(f"  Saved to: {filename}")

    elif args.command == "diff-directories":
        
        from pathlib import Path
        from datetime import datetime, timezone
        import json

        def ts():
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

        source_dir = Path(args.source_dir)
        target_dir = Path(args.target_dir)

        if not source_dir.exists():
            raise SystemExit(f"Source directory does not exist: {source_dir}")

        if not target_dir.exists():
            raise SystemExit(f"Target directory does not exist: {target_dir}")

        print(f"Comparing directories...")
        print(f"  Source: {source_dir}")
        print(f"  Target: {target_dir}")

        diff_artifact = generate_observed_diff_directories(source_dir, target_dir, verbose=args.verbose)

        if not diff_artifact['payload']['files']:
            print("No differences detected.")
            return

        # Create .dennis output directory and save with consistent naming
        dennis_dir = Path(".dennis")
        dennis_dir.mkdir(exist_ok=True)

        timestamp = ts()
        filename = dennis_dir / f"dennis-observed-{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(diff_artifact, f, indent=2)

        file_count = len(diff_artifact['payload']['files'])
        change_count = sum(len(f['changes']) for f in diff_artifact['payload']['files'])

        print(f"✓ Directory diff generated: {file_count} files, {change_count} changes")
        print(f"  Saved to: {filename}")
        print(f"  Observed hash: {diff_hash(diff_artifact)}")


    elif args.command == "compare":
        from dennis.dex.canonical_diff import generate_reconciliation_diff
        from pathlib import Path
        from datetime import datetime, timezone
        import json

        def ts():
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

        planned_path = Path(args.planned_diff)
        observed_path = Path(args.observed_diff)

        if not planned_path.exists():
            raise SystemExit(f"Planned diff file does not exist: {planned_path}")

        if not observed_path.exists():
            raise SystemExit(f"Observed diff file does not exist: {observed_path}")

        print("Loading diff artifacts...")
        planned_diff = json.loads(planned_path.read_text())
        observed_diff = json.loads(observed_path.read_text())

        print("Generating reconciliation...")
        reconciliation = generate_reconciliation_diff(planned_diff, observed_diff)

        # Save to file
        timestamp = ts()
        filename = f"reconciliation-{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(reconciliation, f, indent=2)

        summary = reconciliation['payload']['reconciliation_summary']
        print("✓ Reconciliation complete:")
        print(f"  Files: {summary['total_files']}")
        print(f"  Matched: {summary['matched_changes']}")
        print(f"  Missing: {summary['missing_changes']}")
        print(f"  Unexpected: {summary['unexpected_changes']}")
        print(f"  Saved to: {filename}")

        # Show trust assessment
        total_changes = summary['matched_changes'] + summary['missing_changes'] + summary['unexpected_changes']
        if total_changes > 0:
            match_rate = summary['matched_changes'] / total_changes
            if match_rate >= 0.95:
                print("  🎉 High confidence: Plan executed as expected")
            elif match_rate >= 0.80:
                print("  ⚠️ Moderate confidence: Some deviations detected")
            else:
                print("  ❌ Low confidence: Significant deviations from plan")
        return
    
    elif args.command == "verify-execution":
        from pathlib import Path
        import json

        expected_path = Path(args.expected)
        observed_path = Path(args.observed)

        if not expected_path.exists():
            raise SystemExit(f"Expected diff file does not exist: {expected_path}")

        if not observed_path.exists():
            raise SystemExit(f"Observed diff file does not exist: {observed_path}")

        print("Loading diff artifacts...")
        expected_diff = json.loads(expected_path.read_text())
        observed_diff = json.loads(observed_path.read_text())

        print("Verifying execution...")

        expected_files = {f["path"] for f in expected_diff["payload"]["files"]}
        observed_files = {f["path"] for f in observed_diff["payload"]["files"]}

        unexpected_files = observed_files - expected_files
        missing_files = expected_files - observed_files

        if unexpected_files:
            print("\n[Dennis] WARNING: Unexpected files detected (not in plan):")
            for f in sorted(unexpected_files):
                print(f"  - {f}")

        if missing_files:
            print("\n[Dennis] WARNING: Planned files missing from execution:")
            for f in sorted(missing_files):
                print(f"  - {f}")

        if unexpected_files or missing_files:
            print("\n[Dennis] Possible causes:")
            print("  • .gitignore mismatch")
            print("  • Different source/target directories")
            print("  • Unintended global transformations")
            if args.strict:
                print("\n[Dennis] ERROR: Scope mismatch detected (strict mode)")
                raise SystemExit(1)

        expected_hash = diff_hash(expected_diff)
        observed_hash = diff_hash(observed_diff)
        match = expected_hash == observed_hash

        result = {
            "match": match,
            "expected_hash": expected_hash,
            "observed_hash": observed_hash,
            "expected_files": len(expected_files),
            "observed_files": len(observed_files)
        }

        print("\n[Dennis] Execution Verification")
        print(f"  Expected hash:  {expected_hash}")
        print(f"  Observed hash:  {observed_hash}")
        print(f"  Match: {'✓ YES' if match else '✗ NO'}")
        print(f"  Expected files: {result['expected_files']}")
        print(f"  Observed files: {result['observed_files']}")

        if not match:
            print("\n[INFO] Hashes do not match. Running detailed reconciliation...")
            from dennis.dex.canonical_diff import generate_reconciliation_diff
            
            reconciliation = generate_reconciliation_diff(expected_diff, observed_diff)
            summary = reconciliation['payload']['reconciliation_summary']
            
            print(f"\n  Files: {summary['total_files']}")
            print(f"  Matched: {summary['matched_changes']}")
            print(f"  Missing: {summary['missing_changes']}")
            print(f"  Unexpected: {summary['unexpected_changes']}")
            
            raise SystemExit(1)
        else:
            print("\n✓ Execution matches expected transformation")
            return
    
    elif args.command == "test-diff":

        from dennis.diff_conformance import run_case
        import sys
        import json

        BASE_DIR = Path("tests/diff_conformance")

        if not BASE_DIR.exists():
            raise SystemExit("tests/diff_conformance directory not found")

        print("\n[ Dennis Diff Conformance ]\n")

        cases = sorted([p for p in BASE_DIR.iterdir() if p.is_dir()])

        if args.case:
            cases = [BASE_DIR / args.case]
            if not cases[0].exists():
                raise SystemExit(f"Case not found: {args.case}")

        failed = 0

        for case in cases:

            expected_json_path = case / "expected.json"
            expected_hash_path = case / "expected.hash"

            # -----------------------------
            # INIT MODE
            # -----------------------------
            if args.init:
                if not expected_json_path.exists():
                    print(f"✖ {case.name:30} missing expected.json")
                    failed += 1
                    continue

                try:
                    expected = json.loads(expected_json_path.read_text(encoding="utf-8"))
                    h = diff_hash(expected)
                    expected_hash_path.write_text(h + "\n", encoding="utf-8")
                    print(f"✔ {case.name:30} hash generated")
                except Exception as e:
                    print(f"✖ {case.name:30} error: {e}")
                    failed += 1
                continue

            # -----------------------------
            # VALIDATION MODE
            # -----------------------------
            errors, canonical, expected, actual_hash, expected_hash = run_case(case)

            if not errors:
                print(f"✔ {case.name:30} OK")
            else:
                failed += 1
                print(f"✖ {case.name:30} FAIL")

                for err in errors:
                    if err == "canonical_mismatch":
                        print("  → Canonical mismatch")

                        if args.verbose and canonical and expected:
                            show_diff(expected, canonical)

                    elif err == "hash_mismatch":
                        print("  → Hash mismatch")
                        print(f"    expected: {expected_hash}")
                        print(f"    actual:   {actual_hash}")

                    else:
                        print(f"  → {err}")

                print()

        if failed:
            raise SystemExit(f"\n✖ {failed} test(s) failed\n")

        print("\n✔ All conformance tests passed\n")

        #--------------------------------------------------------
    # SCOPE COMMANDS
    #--------------------------------------------------------

    elif args.command == "scope":

        if args.scope_command == "export":

            root_dir = Path(args.root).resolve()

            files = collect_project_files(root_dir)

            scope_file = root_dir / ".dexscope"

            preserved_comments = []
            excluded_paths = set()

            if scope_file.exists():

                for raw_line in scope_file.read_text(
                    encoding="utf-8"
                ).splitlines():

                    if raw_line.lstrip().startswith("#"):

                        # Skip generated header
                        if raw_line.strip() == "# Dennis Scope v1":
                            continue

                        preserved_comments.append(raw_line)

                        candidate = raw_line.lstrip()[1:].strip()

                        if candidate:
                            excluded_paths.add(candidate)

            lines = [
                "# Dennis Scope v1",
                ""
            ]

            for file_path in files:

                rel_path = str(
                    file_path.relative_to(root_dir)
                )

                # User previously commented this out
                if rel_path in excluded_paths:
                    continue

                lines.append(rel_path)

            if preserved_comments:

                lines.append("")
                lines.extend(preserved_comments)

            scope_file.write_text(
                "\n".join(lines) + "\n",
                encoding="utf-8"
            )

            print(
                f"[Dennis] Scope exported → {scope_file}"
            )

            return

        elif args.scope_command == "inspect":

            print(
                "[Dennis] Scope inspect not implemented yet."
            )

            return
        
        elif args.scope_command == "json":

            export_dexscope_json(
                Path(args.root).resolve()
            )

            return

        elif args.scope_command == "refresh":

            refresh_dexscope(
                Path(args.root).resolve()
            )

            return