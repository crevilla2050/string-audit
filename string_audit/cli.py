import argparse
from pathlib import Path

from .scanner import scan_directory
from .reporters.human import print_human_report
from .reporters.json_reporter import write_json_report

from .i18n.generator import (
    load_findings,
    build_dictionary,
    write_en_json,
    write_en_js,
)

from .i18n.generator import (
    load_existing_dict,
    merge_dictionaries,
)

from .i18n.apply import apply_i18n
from .i18n.plan import generate_plan, write_plan, default_plan_filename


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="string-audit")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan a directory")
    scan.add_argument("path", help="Directory to scan")
    scan.add_argument("--json", dest="json_out", help="Write JSON report")

    gen = sub.add_parser("generate-i18n", help="Generate en.json and en.js from findings JSON")
    gen.add_argument("input", help="Findings JSON file")
    gen.add_argument("--out-dir", default=".", help="Output directory")
    gen.add_argument(
        "--merge",
        nargs="*",
        help="Existing JSON dictionaries to merge into (non-destructive)",
    )

    apply_cmd = sub.add_parser("apply-i18n", help="Replace hardcoded strings with tokens")
    apply_cmd.add_argument("dict", help="Dictionary JSON file (en.json)")
    apply_cmd.add_argument(
        "--target-project-dir",
        "--root",
        dest="target_dir",
        default=".",
        help="Target project directory containing Python files (default: current dir)",
    )
    apply_cmd.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    apply_cmd.add_argument(
        "--result-json",
        help="Generate a reviewable plan JSON instead of applying changes",
    )

    apply_cmd.add_argument(
        "--from-plan",
        help="Apply changes from a previously generated plan JSON",
    )


    return parser

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scan":
        root = Path(args.target_dir)
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

        # Merge mode
        if args.merge:
            existing_dicts = [
                load_existing_dict(Path(p)) for p in args.merge
            ]
            mapping = merge_dictionaries(mapping, *existing_dicts)

        write_en_json(mapping, out_dir / "en.json")
        write_en_js(mapping, out_dir / "en.js")

        print(f"Generated {len(mapping)} translation keys in {out_dir}")

    elif args.command == "apply-i18n":
        # Apply from plan mode
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

        # Planning mode
        if args.result_json:
            output = Path(args.result_json)
        else:
            output = Path(default_plan_filename())

        plan = generate_plan(root, dict_path)
        write_plan(plan, output)

        print(f"Plan written to: {output}")
        print(f"Proposed changes: {len(plan['changes'])}")

