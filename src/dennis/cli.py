import os
from dennis import server
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.dennis/.env"))

import argparse
from marshal import version
from os import path
import re
from pathlib import Path
import json
from datetime import datetime, timezone

from dennis.scanner import scan_directory
from dennis.reporters.human import print_human_report
from dennis.reporters.json_reporter import write_json_report

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

def timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

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

    # ---------------------------------------------------------
    # IMPORT ARGUMENTS
    # ---------------------------------------------------------

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

    # DEX group (sign / verify)
    dex = sub.add_parser("dex", help="DEX artifact actions")
    dex_sub = dex.add_subparsers(dest="dex_command", required=True)

    dex_sign = dex_sub.add_parser("sign", help="Sign a DEX artifact")
    dex_sign.add_argument("artifact", help="Path to artifact.dex")
    dex_sign.add_argument("--key", required=True, help="Private key file (ed25519)")
    dex_sign.add_argument("--key-id", default="dev", help="Key identifier to store in signatures/<key_id>.pub")

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
    add_format_argument(inspect_cmd)
    
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

    validate_plan_cmd = sub.add_parser(
        "validate-plan",
        help="Validate transformation plan inside artifact"
    )

    validate_plan_cmd.add_argument(
        "input",
        help="Path to artifact.dex"
    )

    login_cmd = sub.add_parser("login", help="Authenticate with Dennis The Forge")

    login_cmd.add_argument("--server", required=True)
    login_cmd.add_argument("--email", required=True)
    login_cmd.add_argument("--token", help="Use existing token (for automation)")

    logout_cmd = sub.add_parser("logout", help="Clear stored authentication")

    return parser

# ============================================================
# MAIN
# ============================================================

def main() -> None:
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

        from pathlib import Path
        from datetime import datetime, timezone
        import tempfile
        import json

        def ts():
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

        # ----------------------------------------
        # Detect mode (manual subcommands)
        # ----------------------------------------

        if args.root in ("export", "import"):
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
            
            print("[DEBUG BEFORE CSV]", plan["changes"][-1])
            write_csv_from_plan(plan, output)
            print("[DEBUG BEFORE CSV]", plan["changes"][-1])

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

        root = Path(args.root or ".")

        # ----------------------------------------
        # MODE: BASELINE
        # ----------------------------------------

        if args.baseline:

            from dennis.core.diff import diff_directories
            from dennis.core.serialize import dump_json
            from dennis.core.csvio import write_csv_from_plan
            from dennis.core.rehydrate import rehydrate

            with tempfile.TemporaryDirectory() as tmp_dir:
                baseline_path = Path(tmp_dir)

                print(f"[Dennis] Rehydrating baseline → {args.baseline}")
                rehydrate(args.baseline, output_dir=baseline_path)

                print("[Dennis] Computing diff...")
                changes = diff_directories(baseline_path, root)

            plan = {
                "changes": changes,
                "meta": {
                    "baseline": args.baseline,
                    "generated_at": ts()
                }
            }

            output = Path(args.out) if args.out else Path(f"plan-{ts()}.json")
            csv_path = output.with_suffix(".csv")

            with open(output, "w", encoding="utf-8") as f:
                print("[DEBUG FINAL BEFORE WRITE]", plan["changes"][-1])
                dump_json(plan, f)
            write_csv_from_plan(plan, csv_path)

            print(f"[Dennis] Plan generated → {output}")
            print(f"[Dennis] CSV generated  → {csv_path}")
            return

        # ----------------------------------------
        # MODE: DICTIONARY (DEFAULT)
        # ----------------------------------------

        from dennis.i18n.plan import generate_plan
        from dennis.forge.hash.canonical import canonical_hash

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

        excluded_langs = set()

        if args.exclude_lang:
            excluded_langs = {
                lang.strip() for lang in args.exclude_lang.split(",")
            }

        plan = generate_plan(
            root,
            dict_path,
            helpers=helpers,
            git_mode=git_mode,
            lang=args.lang,
            exclude_langs=excluded_langs
        )

        from dennis.core.serialize import dump_json
        from dennis.core.csvio import write_csv_from_plan
        import copy

        with open(output, "w", encoding="utf-8") as f:
            dump_json(plan, f)

        import copy
        csv_path = output.with_suffix(".csv")
        print("[DEBUG BEFORE CSV]", plan["changes"][-2:])

        write_csv_from_plan(copy.deepcopy(plan), csv_path)

        print("[DEBUG AFTER CSV]", plan["changes"][-2:])

        print(f"Plan written → {output}")
        print(f"CSV written  → {csv_path}")
        print(f"Plan hash: {canonical_hash(plan)}")

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
    # DEX COMMANDS
    # --------------------------------------------------------
    elif args.command == "dex":

        import json

        if args.dex_command == "sign":
            from dennis.dex.sign import sign_dex

            artifact = args.artifact
            key_path = args.key
            key_id = args.key_id

            sign_dex(artifact, key_path, key_id=key_id)

            print(json.dumps({
                "success": True,
                "message": f"Signed: {artifact}",
                "key_id": key_id
            }, indent=2))

            return

        elif args.dex_command == "verify":
            from dennis.dex.sign import verify_dex

            artifact = args.artifact
            results = verify_dex(artifact)

            if not results:
                result = {
                    "verified": False,
                    "signatures": 0,
                    "valid_signatures": 0,
                    "invalid_signatures": 0,
                    "errors": ["No signatures present"],
                    "message": "✖ No signatures found"
                }

                print(json.dumps(result, indent=2))
                raise SystemExit(1)

            total = len(results)
            valid_count = sum(1 for _, ok in results if ok)
            invalid_count = total - valid_count

            if valid_count == 0:
                result = {
                    "verified": False,
                    "signatures": total,
                    "valid_signatures": 0,
                    "invalid_signatures": invalid_count,
                    "errors": ["No valid signatures"],
                    "message": "✖ No valid signatures"
                }

                print(json.dumps(result, indent=2))
                raise SystemExit(1)

            result = {
                "verified": True,
                "signatures": total,
                "valid_signatures": valid_count,
                "invalid_signatures": invalid_count,
                "errors": [],
                "message": "✔ Signature valid"
            }

            print(json.dumps(result, indent=2))
            return


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
        from pathlib import Path
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
        from pathlib import Path
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
        from pathlib import Path
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

        url = server.rstrip("/") + api_prefix + "/artifacts/upload"

        # ----------------------------------------
        # 4. BUILD MULTIPART REQUEST
        # ----------------------------------------
        boundary = uuid.uuid4().hex
        file_bytes = artifact_path.read_bytes()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{artifact_path.name}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()

        # ----------------------------------------
        # 5. SEND REQUEST (AUTHENTICATED)
        # ----------------------------------------
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Authorization": f"Bearer {token}"
            },
        )

        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())

        except urllib.error.HTTPError as e:
            raise SystemExit(f"Upload failed: {e.read().decode()}")

        # ----------------------------------------
        # 6. OUTPUT
        # ----------------------------------------
        status = result.get("status")
        artifact_hash = result.get("artifact_hash")

        if status == "duplicate":
            print("⚠ Artifact already exists")
            print(f"  Hash: {artifact_hash}")
            print("  Use 'dennis inspect <file.dex>' to view details")
            return

        # fallback = success (backward compatible)
        print(f"✔ Published artifact → {artifact_hash}")

    # --------------------------------------------------------
    # PULL
    # --------------------------------------------------------
    elif args.command == "pull":
        import urllib.request
        from pathlib import Path

        artifact_hash = args.hash.strip()

        if len(artifact_hash) != 64:
            raise SystemExit("Error: full artifact hash required (64 hex chars)")

        url = args.remote.rstrip("/") + api_prefix + f"/artifacts/{artifact_hash}"
        print("DEBUG URL:", url)
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
    # INSPECT
    # --------------------------------------------------------
    elif args.command == "inspect":

        import urllib.request
        import json
        import gzip
        import tarfile
        import io
        from pathlib import Path

        target = args.target.strip()

        # --------------------------------------------------------
        # LOCAL FILE INSPECTION
        # --------------------------------------------------------

        if Path(target).exists():

            path = Path(target)

            if not path.is_file():
                raise SystemExit(f"Artifact file not found: {path}")

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

                plan_bytes = files.get("payload/plan.json")
                patch_info = {}

                if plan_bytes:
                    try:
                        plan = json.loads(plan_bytes)
                        patches = plan.get("patches", {})
                        patch_info = {
                            "helpers": len(patches.get("helpers", [])),
                            "remove_helpers": len(patches.get("remove_helpers", []))
                        }
                    except Exception:
                        patch_info = {}

                data = {
                    "artifact_hash": "local-file",
                    "meta": manifest.get("meta", {}),
                    "payload": {
                        "type": manifest.get("payload", {}).get("type"),
                        "hash": manifest.get("payload", {}).get("hash", {}).get("value"),
                        "size_bytes": len(files.get("payload/plan.json", b"")),
                    },
                    "signatures": manifest.get("signatures", []),
                }

            except Exception:
                raise SystemExit("Not a Dennis artifact or unsupported file")

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

        if args.format == "json":
            print(json.dumps(data, indent=2))
            return

        print("\nArtifact")
        print("--------")
        print(f"Hash:        {data.get('artifact_hash')}")

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

        sigs = data.get("signatures", [])

        print("\nSignatures")
        print("----------")

        if not sigs:
            print("None")
        else:
            for s in sigs:
                print(
                    f"{s.get('key_id')}  "
                    f"{s.get('algorithm')}  "
                    f"{s.get('created_at')}"
                )

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
            print("\nPatches")
            print("-------")
            if patch_info.get("helpers"):
                print(f"Helpers:     {patch_info['helpers']}")
            if patch_info.get("remove_helpers"):
                print(f"Removals:    {patch_info['remove_helpers']}")

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

    # --------------------------------------------------------
    # PACK
    # --------------------------------------------------------
    elif args.command == "pack":

        from pathlib import Path
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

        if args.parent:
            from dennis.dex.importer import import_dex

            parent_path = Path(args.parent)

            if not parent_path.exists():
                raise SystemExit(f"[Dennis] Parent artifact not found: {args.parent}")

            parent_manifest, _ = import_dex(parent_path)

        if args.parent and args.detached:
            raise SystemExit("[Dennis] Cannot use --parent and --detached together")

        output = pack_dex(
            payload_path=Path(args.payload),
            output_path=Path(args.out),
            payload_type=args.type,
            parent_manifest=parent_manifest,
            force_detached=args.detached
        )

        print(f"Artifact written → {output_path}")

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

        from pathlib import Path
        import json
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

        from pathlib import Path
        from dennis.i18n.apply import apply_plan
        from dennis.dex.importer import import_dex
        import tempfile
        import json

        plan_path = Path(args.plan)


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

                _context_path().write_text(json.dumps({
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
                tmp_path = Path(tmp.name)

            try:
                changes = apply_plan(tmp_path, confirm=args.confirm)
            finally:
                tmp_path.unlink(missing_ok=True)

        else:
            changes = apply_plan(plan_path, confirm=args.confirm)

    elif args.command == "dict":

        from pathlib import Path
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

        from pathlib import Path
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

        from pathlib import Path
        from dennis.core.keys import bootstrap_key, approve_key, list_keys

        if args.key_command == "bootstrap":
            bootstrap_key(Path(args.pub))

        elif args.key_command == "approve":
            approve_key(Path(args.pub), Path(args.signer))

        elif args.key_command == "list":
            list_keys()

        else:
            raise SystemExit("Unknown key command")

    elif args.command == "login":
        import urllib.request
        import json
        import getpass

        from dennis.forge.config import save_config

        server = args.server.rstrip("/")

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

        print("✔ Logged in successfully")


    elif args.command == "logout":
        from dennis.forge.config import load_config, save_config

        config = load_config()

        if "auth" in config:
            config["auth"] = {}

        save_config(config)

        print("✔ Logged out successfully")
        return