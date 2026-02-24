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

    rehydrate = sub.add_parser("rehydrate", help="CSV → JSON canonical")
    rehydrate.add_argument("csv", help="Input CSV")
    rehydrate.add_argument("--out", required=True, help="Output plan JSON")

    validate = sub.add_parser("validate", help="Validate plan against schema")
    validate.add_argument("plan", help="Plan JSON file")

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

    elif args.command == "validate":
        from string_audit.core.schema import validate_plan
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        validate_plan(plan)
        print("Plan is valid ✔")

    elif args.command == "rehydrate":
        from string_audit.core.csvio import read_csv_changes
        from string_audit.core.rehydrate import rehydrate_from_csv
        from string_audit.core.serialize import dump_json

        changes = read_csv_changes(args.csv)
        plan = rehydrate_from_csv(changes)
        dump_json(plan, open(args.out, "w"))
        print(f"Rehydrated plan written to: {args.out}")

    elif args.command == "export":
        from string_audit.core.csvio import write_csv_from_plan
        from string_audit.core.export_js import export_js

        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))

        if args.csv:
            write_csv_from_plan(plan, args.csv)
            print(f"CSV exported to: {args.csv}")

        if args.js:
            export_js(plan, open(args.js, "w"))
            print(f"JS exported to: {args.js}")