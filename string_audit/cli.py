import argparse
from pathlib import Path

from .scanner import scan_directory
from .reporters.human import print_human_report
from .reporters.json_reporter import write_json_report

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="string-audit")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan a directory")
    scan.add_argument("path", help="Directory to scan")
    scan.add_argument("--json", dest="json_out", help="Write JSON report")

    return parser

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scan":
        root = Path(args.path)
        findings = scan_directory(root)

        print_human_report(findings)

        if args.json_out:
            write_json_report(findings, args.json_out)
