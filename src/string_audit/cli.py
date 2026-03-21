import argparse
from marshal import version
from os import path
import re
from pathlib import Path
from datetime import datetime, timezone

from .scanner import scan_directory
from .reporters.human import print_human_report
from .reporters.json_reporter import write_json_report

from .i18n.generator import (
    load_findings,
    build_dictionary,
    write_en_json,
    write_en_js,
    load_existing_dict,
    merge_dictionaries,
)

from .i18n.plan import (
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
from string_audit.qr import (
    decode_ascii_payload,
    decode_image_qr,
    extract_uri_from_ascii,
    extract_uri_from_image,
)
from string_audit.qr.encode import make_qr_uri, generate_ascii_qr, generate_png_qr
from string_audit.qr.parse import parse_dfp_uri
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

        dennis plan . --dict dictionary.json
        dennis dex pack plan.json artifact.dex
        dennis dex sign artifact.dex --key dev.key
        dennis inspect artifact.dex
        dennis encrypt artifact.dex

        Forged slowly. Built for trust.
    """

    parser.usage = """
        dennis [command] [options]

        Core workflow:
        plan       generate transformation plan
        pack       create DEX artifact
        sign       sign artifact
        inspect    inspect artifact metadata
        verify     verify signatures

        Security:
        encrypt    convert DEX → XDEX
        decrypt    convert XDEX → DEX

        Execution:
        rehydrate  restore project context from artifact
        apply      execute transformation plan
    """

    sub = parser.add_subparsers(dest="command")

    # PLAN & EXPORT
    plan_cmd = sub.add_parser("plan", help="Plan operations")

    plan_sub = plan_cmd.add_subparsers(dest="plan_command")
    plan_cmd.description = "Plan operations:\n  Generate transformation plan or\n  export: export plan to other formats"
    plan_sub.required = False


    # --------------------------------------------------------
    # PLAN RUN (default)
    # --------------------------------------------------------

    plan_run = plan_sub.add_parser(
        "run",
        help="Generate transformation plan"
    )

    plan_run.add_argument(
        "root",
        help="Project root directory"
    )

    plan_run.add_argument(
        "--dict",
        required=True,
        help="Dictionary JSON file"
    )

    plan_run.add_argument(
        "--out",
        help="Output plan filename"
    )

    plan_run.add_argument(
        "--add-helper",
        action="append",
        help="Helper file to insert"
    )

    plan_run.add_argument(
        "--target-file",
        action="append",
        help="Target file for helper"
    )

    plan_run.add_argument(
        "--line",
        action="append",
        type=int,
        help="Insertion line for helper"
    )


    # --------------------------------------------------------
    # PLAN EXPORT
    # --------------------------------------------------------

    plan_export = plan_sub.add_parser(
        "export",
        help="Export plan to other formats"
    )

    plan_export.add_argument(
        "plan",
        help="Plan JSON file"
    )

    plan_export.add_argument(
        "--format",
        choices=["csv", "html", "xml", "txt"],
        default="csv",
        help="Export format"
    )

    plan_export.add_argument(
        "--file",
        help="Output filename"
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

    apply_cmd.add_argument("plan", help="Plan JSON file")

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

    return parser

# ============================================================
# MAIN
# ============================================================

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

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
    
    if args.command == "plan" and args.plan_command is None:
        args.plan_command = "run"

    # --------------------------------------------------------
    # Validate helper arguments
    # --------------------------------------------------------

    if args.command == "plan" and args.plan_command == "run":

        helpers = args.add_helper or []
        targets = args.target_file or []
        lines = args.line or []

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

            # default line numbers
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
    
    if args.version:
        from importlib.metadata import version

        print(f"Dennis Forge {version('dennis')}")
        print("Forged slowly. Built for trust.")
        return
    
    if args.command is None:
        parser.print_help()
        return

    # --------------------------------------------------------
    # PLAN
    # --------------------------------------------------------
    if args.command == "plan":
        from string_audit.forge.hash.canonical import canonical_hash
        from pathlib import Path

        root = Path(args.root)
        dict_path = Path(args.dict)
        output = Path(args.out) if args.out else Path(default_plan_filename())

        helpers = []

        for spec in getattr(args, "helper_specs", []):
            helper = load_helper(Path(spec["helper"]))
            helper["file"] = spec["target"]
            helper["line"] = spec["line"]
            helpers.append(helper)

        plan = generate_plan(root, dict_path, helpers=helpers)
        
        write_plan(plan, output)
        print(f"Plan written → {output}")
        print(f"Plan hash: {canonical_hash(plan)}")

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

            url = args.remote.rstrip("/") + "/api/registry/remotes"

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

            url = args.remote.rstrip("/") + "/api/registry/remotes"

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

            url = args.remote.rstrip("/") + "/api/registry/sync"

            req = urllib.request.Request(url, method="POST")

            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())

            print("Federation sync started")
            print(data)

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------
    elif args.command == "validate":

        from dennis.dex.validate import validate_dex_file

        results = validate_dex_file(args.path)

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

        print()

    # --------------------------------------------------------
    # HASH
    # --------------------------------------------------------
    elif args.command == "hash":
        from string_audit.forge.hash.canonical import canonical_hash
        from pathlib import Path
        import json
        

        obj = json.loads(Path(args.file).read_text())
        print(canonical_hash(obj))

    # --------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------
    elif args.command == "plan" and args.plan_command == "export":

        from pathlib import Path
        import json
        from datetime import datetime, timezone

        from dennis.core.csvio import write_csv_from_plan
        from dennis.core.export_html import export_html
        from dennis.core.export_xml import export_xml
        from dennis.core.export_txt import export_txt

        plan = json.loads(Path(args.plan).read_text())

        def ts():
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

        fmt = args.format

        if args.file:
            out_path = Path(args.file)
        else:
            out_path = Path(f"plan-{ts()}.{fmt}")

        if fmt == "csv":
            write_csv_from_plan(plan, out_path)

        elif fmt == "html":
            export_html(plan, open(out_path, "w"))

        elif fmt == "xml":
            export_xml(plan, open(out_path, "w"))

        elif fmt == "txt":
            export_txt(plan, open(out_path, "w"))

        else:
            raise SystemExit(f"Unsupported format: {fmt}")

        print(f"Plan exported → {out_path}")


    # --------------------------------------------------------
    # PUSH
    # --------------------------------------------------------
    elif args.command == "push":
        import urllib.request
        from string_audit.forge.hash.canonical import canonical_hash
        from pathlib import Path
        import json

        plan = json.loads(Path(args.plan).read_text())
        plan_hash = canonical_hash(plan)

        url = args.remote.rstrip("/") + "/plan"
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
            from string_audit.qr.encode import generate_ascii_qr, generate_png_qr
            out_dir = Path(args.qr_path) if args.qr_path else Path(args.plan).parent
            out_dir.mkdir(parents=True, exist_ok=True)

            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

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
        from string_audit.qr.encode import make_qr_uri, generate_ascii_qr, generate_png_qr
        from string_audit.forge.hash.canonical import canonical_hash
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
    # DEX: sign / verify
    # --------------------------------------------------------
    elif args.command == "dex":
        if args.dex_command == "sign":
            from dennis.dex.sign import sign_dex
            artifact = args.artifact
            key_path = args.key
            key_id = args.key_id
            sign_dex(artifact, key_path, key_id=key_id)
            print(f"Signed: {artifact} (key_id={key_id})")

        elif args.dex_command == "verify":
            from dennis.dex.sign import verify_dex
            artifact = args.artifact

            results = verify_dex(artifact)  # returns list of (key_id, bool) in manifest order

            if not results:
                print("DEX verification FAILED: no signatures present.")
                raise SystemExit(1)

            total = len(results)
            valid_count = sum(1 for _, ok in results if ok)
            authoritative_valid = results[-1][1]  # last signature is authoritative per policy

            # Policy:
            # - if no valid signatures -> fail exit 1
            # - if authoritative valid -> OK exit 0
            # - if authoritative invalid but some legacy valid -> WARNING + exit 0 (do not reveal which ones)
            if valid_count == 0:
                print("DEX verification FAILED: no valid signatures found.")
                raise SystemExit(1)

            if authoritative_valid:
                print("DEX verification OK — authoritative signature valid.")
                if getattr(args, "verbose", False):
                    print(f"{valid_count} of {total} signatures are valid.")
                raise SystemExit(0)
            else:
                # authoritative invalid but at least one legacy valid
                print("WARNING: authoritative signature invalid.")
                print("However, at least one legacy signature is valid.")
                print("Please review the artifact and sign again if appropriate.")
                if getattr(args, "verbose", False):
                    print(f"{valid_count} of {total} signatures are valid (not revealing which).")
                raise SystemExit(0)
            
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

        url = args.remote.rstrip("/") + "/api/artifacts?" + query

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

        artifact_path = Path(args.artifact)

        if not artifact_path.exists():
            raise SystemExit(f"Artifact not found: {artifact_path}")

        url = args.remote.rstrip("/") + "/api/artifacts"

        boundary = uuid.uuid4().hex
        file_bytes = artifact_path.read_bytes()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{artifact_path.name}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}"
            },
        )

        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())

        print(f"Published artifact → {result.get('artifact_hash')}")

    # --------------------------------------------------------
    # PULL
    # --------------------------------------------------------
    elif args.command == "pull":
        import urllib.request
        from pathlib import Path

        artifact_hash = args.hash.strip()

        if len(artifact_hash) != 64:
            raise SystemExit("Error: full artifact hash required (64 hex chars)")

        url = args.remote.rstrip("/") + f"/api/artifacts/{artifact_hash}"
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

                    if header_hash != expected_hash:
                        print("\n[ Dennis ]")
                        print("XDEX header is INVALID. The file may be corrupted or tampered with.")
                        raise SystemExit(1)

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

            url = args.remote.rstrip("/") + f"/api/artifacts/{artifact_hash}/metadata"

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

        url = args.remote.rstrip("/") + f"/api/artifacts/{args.hash}/signatures"

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
        url = args.remote.rstrip("/") + f"/api/artifacts/{args.hash}/lineage"

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
        import json
        from dennis.dex.importer import import_dex

        semantic = not args.ignore_semantics

        manifestA, payloadA = import_dex(args.artifact_a)
        manifestB, payloadB = import_dex(args.artifact_b)

        planA = json.loads(payloadA)
        planB = json.loads(payloadB)

        changesA = index_changes(planA, semantic)
        changesB = index_changes(planB, semantic)

        added = sorted(changesB.keys() - changesA.keys())
        removed = sorted(changesA.keys() - changesB.keys())

        common = changesA.keys() & changesB.keys()

        modified = []

        for cid in sorted(common):

            if changesA[cid] != changesB[cid]:

                diffs = {}

                for k in set(changesA[cid]) | set(changesB[cid]):

                    if changesA[cid].get(k) != changesB[cid].get(k):

                        diffs[k] = {
                            "A": changesA[cid].get(k),
                            "B": changesB[cid].get(k)
                        }

                modified.append({
                    "id": cid,
                    "file": changesA[cid].get("file"),
                    "line": changesA[cid].get("line"),
                    "differences": diffs
                })

        result = {
            "artifact_a": manifestA["payload"]["hash"]["value"],
            "artifact_b": manifestB["payload"]["hash"]["value"],
            "summary": {
                "added": len(added),
                "removed": len(removed),
                "modified": len(modified)
            },
            "added": added,
            "removed": removed,
            "modified": modified
        }

        print(json.dumps(result, indent=2))

    # --------------------------------------------------------
    # PACK
    # --------------------------------------------------------
    elif args.command == "pack":

        from pathlib import Path
        import json
        from dennis.dex.pack import pack_dex
        #from string_audit.forge.hash.canonical import canonical_hash
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

        pack_dex(
            payload_path,
            output_path,
            payload_type=args.type
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
        from dennis.dex.importer import import_dex

        artifact = Path(args.artifact)
        out_dir = Path(args.out)

        out_dir.mkdir(parents=True, exist_ok=True)

        manifest, payload_bytes = import_dex(artifact)
        plan = json.loads(payload_bytes)

        # --------------------------------------------------
        # Write plan
        # --------------------------------------------------

        plan_path = out_dir / "rehydrated-plan.json"

        plan_path.write_text(
            json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
        )

        print(f"Plan restored → {plan_path}")

        # --------------------------------------------------
        # Reconstruct dictionary
        # --------------------------------------------------

        dictionary = {}

        for change in plan.get("changes", []):

            token = change.get("token")
            original = change.get("original")

            if not token or not original:
                continue

            match = re.search(r'["\'](.+?)["\']', original)

            if match:
                dictionary[token] = match.group(1)

        if dictionary:

            dict_path = out_dir / "dictionary.json"

            dict_path.write_text(
                json.dumps(dictionary, indent=2, ensure_ascii=False) + "\n"
            )

            print(f"Dictionary restored → {dict_path}")

        print("\nNext step:")
        print(f"  dennis apply {plan_path.name}")

    elif args.command == "apply":

        from pathlib import Path
        from string_audit.i18n.apply import apply_plan

        plan_path = Path(args.plan)

        changes = apply_plan(plan_path)


    elif args.command == "dict":

        from pathlib import Path
        from string_audit.i18n.csvio import (
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
        from string_audit.utils import (
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
            from string_audit.utils import get_backup_dir
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