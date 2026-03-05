import argparse
import json
from pathlib import Path
from datetime import datetime

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

from .i18n.plan import generate_plan, write_plan, default_plan_filename
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


def banner():
    return "Dennis the Forge — deterministic codemods"


# ============================================================
# ARGPARSE
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dennis", description=banner())
    sub = parser.add_subparsers(dest="command", required=True)

    # PLAN
    plan = sub.add_parser("plan")
    plan.add_argument("root")
    plan.add_argument("--dict", required=True)
    plan.add_argument("--out")

    # EXPORT
    export = sub.add_parser("export")
    export.add_argument("plan")
    export.add_argument("--csv")
    export.add_argument("--js")
    export.add_argument("--html")
    export.add_argument("--xml")

    # REHYDRATE
    rehydrate = sub.add_parser("rehydrate")
    rehydrate.add_argument("csv")
    rehydrate.add_argument("--out", required=True)

    # VALIDATE
    validate = sub.add_parser("validate")
    validate.add_argument("plan")

    # HASH
    hash_cmd = sub.add_parser("hash")
    hash_cmd.add_argument("file")

    # PUSH
    push_cmd = sub.add_parser("push")
    push_cmd.add_argument("remote")
    push_cmd.add_argument("plan")
    push_cmd.add_argument("--qr", action="store_true")
    push_cmd.add_argument("--qr-path")

    # PULL
    pull_cmd = sub.add_parser("pull")
    pull_cmd.add_argument("remote")
    pull_cmd.add_argument("hash")
    pull_cmd.add_argument("--out", default="pulled-plan.json")

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

    return parser


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # --------------------------------------------------------
    # PLAN
    # --------------------------------------------------------
    if args.command == "plan":
        from string_audit.forge.hash.canonical import canonical_hash

        root = Path(args.root)
        dict_path = Path(args.dict)
        output = Path(args.out) if args.out else Path(default_plan_filename())

        plan = generate_plan(root, dict_path)
        write_plan(plan, output)
        print(f"Plan written → {output}")
        print(f"Plan hash: {canonical_hash(plan)}")

    # --------------------------------------------------------
    # HASH
    # --------------------------------------------------------
    elif args.command == "hash":
        from string_audit.forge.hash.canonical import canonical_hash

        obj = json.loads(Path(args.file).read_text())
        print(canonical_hash(obj))

    # --------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------
    elif args.command == "export":
        from dennis.core.csvio import write_csv_from_plan
        from dennis.core.export_js import export_js

        plan = json.loads(Path(args.plan).read_text())

        if args.csv:
            write_csv_from_plan(plan, args.csv)
            print(f"CSV → {args.csv}")

        if args.js:
            export_js(plan, open(args.js, "w"))
            print(f"JS → {args.js}")

        if args.html:
            export_html(plan, open(args.html, "w"))
            print(f"HTML → {args.html}")

        if args.xml:
            export_xml(plan, open(args.xml, "w"))
            print(f"XML → {args.xml}")

    # --------------------------------------------------------
    # PUSH
    # --------------------------------------------------------
    elif args.command == "push":
        import urllib.request
        from string_audit.forge.hash.canonical import canonical_hash

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
    # PULL
    # --------------------------------------------------------
    elif args.command == "pull":
        import urllib.request

        url = args.remote.rstrip("/") + f"/{args.hash}"
        with urllib.request.urlopen(url) as resp:
            data = resp.read()

        Path(args.out).write_bytes(data)
        print(f"Pulled → {args.out}")

    # --------------------------------------------------------
    # QR GENERATION
    # --------------------------------------------------------
    elif args.command == "qr":
        from string_audit.qr.encode import make_qr_uri, generate_ascii_qr, generate_png_qr
        from string_audit.forge.hash.canonical import canonical_hash

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