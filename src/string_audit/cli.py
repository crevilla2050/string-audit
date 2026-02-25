import argparse
import json
from pathlib import Path

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

from .i18n.apply import apply_i18n
from .i18n.plan import generate_plan, write_plan, default_plan_filename
from string_audit.core.export_html import export_html
from string_audit.core.export_xml import export_xml

from string_audit.core.import_xml import import_xml
from string_audit.core.serialize import dump_json

from string_audit.core.export_xsd import export_xsd
from string_audit.core.validate_xml import validate_xml_file

def banner():
    return "Dennis the Forge — deterministic codemods for Git-native projects"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dennis", description=banner())
    parser.add_argument(
        "--tracked-only",
        action="store_true",
        help="Only process Git-tracked files",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -----------------------------
    # EXISTING COMMANDS (UNCHANGED)
    # -----------------------------

    scan = sub.add_parser("scan", help="Scan a directory (legacy)")
    scan.add_argument("path", help="Directory to scan")
    scan.add_argument("--json", dest="json_out", help="Write JSON report")

    gen = sub.add_parser("generate-i18n", help="Generate en.json and en.js from findings JSON (legacy)")
    gen.add_argument("input", help="Findings JSON file")
    gen.add_argument("--out-dir", default=".", help="Output directory")
    gen.add_argument("--merge", nargs="*", help="Existing JSON dictionaries to merge into")

    apply_cmd = sub.add_parser("apply-i18n", help="Replace hardcoded strings with tokens (legacy)")
    apply_cmd.add_argument("dict", help="Dictionary JSON file (en.json)")
    apply_cmd.add_argument("--target-project-dir", "--root", dest="target_dir", default=".")
    apply_cmd.add_argument("--dry-run", action="store_true")
    apply_cmd.add_argument("--result-json", help="Generate a reviewable plan JSON instead of applying changes")
    apply_cmd.add_argument("--from-plan", help="Apply changes from a previously generated plan JSON")

    # -----------------------------
    # DENNIS NATIVE COMMANDS (NEW)
    # -----------------------------

    plan = sub.add_parser("plan", help="Generate deterministic transformation plan")
    plan.add_argument("root", help="Target project directory")
    plan.add_argument("--dict", required=True, help="Dictionary JSON (en.json)")
    plan.add_argument("--out", help="Output plan path")

    export = sub.add_parser("export", help="Export projections (csv/js)")
    export.add_argument("plan", help="Plan JSON file")
    export.add_argument("--csv", help="Export CSV path")
    export.add_argument("--js", help="Export JS path")
    export.add_argument("--html", help="Export HTML projection")
    export.add_argument("--xml", help="Export XML projection")

    rehydrate = sub.add_parser("rehydrate", help="CSV → JSON canonical")
    rehydrate.add_argument("csv", help="Input CSV")
    rehydrate.add_argument("--out", required=True, help="Output plan JSON")

    validate = sub.add_parser("validate", help="Validate plan against schema")
    validate.add_argument("plan", help="Plan JSON file")

    extract_html = sub.add_parser("extract-html-i18n", help="Extract i18n strings from HTML")
    extract_html.add_argument("file", help="HTML file to extract from")
    extract_html.add_argument("--out", default="i18n/en.json", help="Output JSON path")

    imp = sub.add_parser("import", help="Import XML into canonical JSON")
    imp.add_argument("input", help="Input XML file")
    imp.add_argument("--out", help="Output JSON file")

    # XSD export
    xsd = sub.add_parser("export-xsd", help="Export XSD schema")
    xsd.add_argument("--out", default="dennis-plan.xsd", help="Output XSD file")

    # XML validation
    valxml = sub.add_parser("validate-xml", help="Validate XML against Dennis schema")
    valxml.add_argument("xml", help="XML file to validate")

    # -----------------------------
    # SYNC COMMANDS (NEW - ADDITIVE)
    # -----------------------------

    storage_info = sub.add_parser("storage-info", help="Inspect local plan storage")

    # -----------------------------
    # HASH COMMAND (NEW)
    # -----------------------------
    hash_cmd = sub.add_parser("hash", help="Compute canonical hash of a plan")
    hash_cmd.add_argument("file", help="Plan JSON file")

    push_cmd = sub.add_parser("push", help="Push plans to a forge")
    push_cmd.add_argument("remote", help="Forge URL (e.g. http://localhost:8000)")
    push_cmd.add_argument("plan", help="Plan JSON file")

    pull_cmd = sub.add_parser("pull", help="Pull plan from forge")
    pull_cmd.add_argument("remote", help="Forge URL")
    pull_cmd.add_argument("hash", help="Plan hash")
    pull_cmd.add_argument("--out", help="Output file", default="pulled-plan.json")

    return parser

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # -----------------------------
    # LEGACY COMMANDS (UNCHANGED)
    # -----------------------------

    if args.command == "scan":
        root = Path(args.path)
        findings = scan_directory(root)
        print_human_report(findings)
        if args.json_out:
            write_json_report(findings, args.json_out)

    elif args.command == "generate-i18n":
        input_path = Path(args.input)
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        strings = load_findings(input_path)
        mapping = build_dictionary(strings)

        if args.merge:
            existing_dicts = [load_existing_dict(Path(p)) for p in args.merge]
            mapping = merge_dictionaries(mapping, *existing_dicts)

        write_en_json(mapping, out_dir / "en.json")
        write_en_js(mapping, out_dir / "en.js")
        print(f"Generated {len(mapping)} translation keys in {out_dir}")

    elif args.command == "apply-i18n":
        if args.from_plan:
            plan_path = Path(args.from_plan)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            applied = 0

            for change in plan.get("changes", []):
                path = Path(change["file"])
                lines = path.read_text(encoding="utf-8").splitlines()
                idx = change["line"] - 1
                if lines[idx] == change["original"]:
                    lines[idx] = change["replacement"]
                    applied += 1
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            print(f"Applied {applied} planned changes")
            return

        root = Path(args.target_dir)
        dict_path = Path(args.dict)

        if args.result_json:
            output = Path(args.result_json)
        else:
            output = Path(default_plan_filename())

        plan = generate_plan(root, dict_path)
        write_plan(plan, output)

        print(f"Plan written to: {output}")
        print(f"Proposed changes: {len(plan['changes'])}")

    # -----------------------------
    # DENNIS COMMANDS (NEW)
    # -----------------------------

    elif args.command == "plan":
        root = Path(args.root)
        dict_path = Path(args.dict)
        output = Path(args.out) if args.out else Path(default_plan_filename())

        plan = generate_plan(root, dict_path)
        write_plan(plan, output)
        print(f"Plan written to: {output}")
        from string_audit.forge.hash.canonical import canonical_hash
        h = canonical_hash(plan)
        print(f"Plan hash: {h}")

    elif args.command == "validate":
        from string_audit.core.schema import validate_plan
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        validate_plan(plan)
        print("Plan is valid ✔")

    elif args.command == "rehydrate":
        from string_audit.core.csvio import read_csv_changes
        from string_audit.core.rehydrate import rehydrate_from_csv
        from string_audit.forge.canonical.plan_v1 import canonicalize_plan

        changes = read_csv_changes(args.csv)
        plan = rehydrate_from_csv(changes)

        # Canonicalize before writing
        plan = canonicalize_plan(plan)

        dump_json(plan, open(args.out, "w"))
        print(f"Rehydrated plan written to: {args.out}")

        from string_audit.forge.hash.canonical import canonical_hash
        h = canonical_hash(plan)
        print(f"Plan hash: {h}")

    elif args.command == "export":
        from string_audit.core.csvio import write_csv_from_plan
        from string_audit.core.export_js import export_js

        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))

        if args.csv:
            write_csv_from_plan(plan, args.csv)
            print(f"CSV exported to: {args.csv}")

        if args.js:
            export_js(plan, open(args.js, "w", encoding="utf-8"))
            print(f"JS exported to: {args.js}")

        if args.html:
            export_html(plan, open(args.html, "w", encoding="utf-8"))
            print(f"HTML exported to: {args.html}")

        if args.xml:
            export_xml(plan, open(args.xml, "w", encoding="utf-8"))
            print(f"XML exported to: {args.xml}")

    elif args.command == "extract-html-i18n":
        from .tools.html_i18n import extract_html_i18n
        extract_html_i18n(args.file, args.out)

    elif args.command == "import":
        from string_audit.forge.canonical.plan_v1 import canonicalize_plan
        plan = import_xml(args.input)
        plan = canonicalize_plan(plan)
        out = args.out or args.input.replace(".xml", ".json")
        dump_json(plan, open(out, "w", encoding="utf-8"))
        print(f"Imported XML → JSON: {out}")
        from string_audit.forge.hash.canonical import canonical_hash
        h = canonical_hash(plan)
        print(f"Plan hash: {h}")

    elif args.command == "export-xsd":
        with open(args.out, "wb") as f:
            export_xsd(f)
        print(f"XSD exported to: {args.out}")

    elif args.command == "validate-xml":
        validate_xml_file(args.xml)
        print("XML is valid ✔")

    elif args.command == "storage-info":
        from string_audit.forge.instance.paths import default_data_root
        from string_audit.forge.storage.plan_storage import PlanStorage

        root = default_data_root()
        storage = PlanStorage(root)

        plans = list(storage.plans_dir.rglob("*.json"))

        print("Dennis local storage")
        print(f"Root: {root}")
        print(f"Plans stored: {len(plans)}")

    elif args.command == "hash":
        from string_audit.forge.hash.canonical import canonical_hash

        path = Path(args.file)
        obj = json.loads(path.read_text(encoding="utf-8"))
        h = canonical_hash(obj)
        print(h)

    elif args.command == "push":
        import urllib.request
        from string_audit.forge.hash.canonical import canonical_hash

        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        h = canonical_hash(plan)

        url = args.remote.rstrip("/") + "/plan"
        data = json.dumps(plan).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
        print(f"Pushed plan {result['hash']}")

    elif args.command == "pull":
        import urllib.request

        url = args.remote.rstrip("/") + f"/plan/{args.hash}"

        with urllib.request.urlopen(url) as resp:
            data = resp.read()

        Path(args.out).write_bytes(data)
        print(f"Pulled plan → {args.out}")