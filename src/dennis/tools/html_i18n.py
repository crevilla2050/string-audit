from bs4 import BeautifulSoup
import json
from pathlib import Path
from typing import Dict, Iterable


# ---------------------------------------------------------
# Core extraction logic
# ---------------------------------------------------------

def extract_from_html_file(path: Path) -> Dict[str, str]:
    """Extract i18n strings from a single HTML file."""
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    result: Dict[str, str] = {}

    for el in soup.select("[data-i18n]"):
        key = el.get("data-i18n")
        text = el.get_text(strip=True)

        if key:
            result[key] = text

    return result

def collect_html_files(source: Path, recursive: bool) -> Iterable[Path]:
    """Return HTML files from source."""
    if source.is_file():
        yield source
        return

    pattern = "**/*.html" if recursive else "*.html"
    yield from source.glob(pattern)

# ---------------------------------------------------------
# Public API (Dennis-friendly)
# ---------------------------------------------------------

def extract_html_i18n(source: Path, out: Path, recursive: bool = False) -> Dict[str, str]:
    """Extract i18n keys from HTML files into a JSON file."""
    source = Path(source)
    out = Path(out)

    if not source.exists():
        raise FileNotFoundError(f"Source not found: {source}")

    merged: Dict[str, str] = {}

    files = list(collect_html_files(source, recursive))

    for file in files:
        extracted = extract_from_html_file(file)

        # Later we can add collision detection here
        merged.update(extracted)

    # Deterministic ordering
    merged = dict(sorted(merged.items()))

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Extracted {len(merged)} strings from {len(files)} file(s) → {out}")
    return merged


# ---------------------------------------------------------
# CLI entry (standalone usage)
# ---------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract i18n strings from HTML")
    parser.add_argument("source", help="HTML file or directory")
    parser.add_argument("--out", default="i18n/en.json", help="Output JSON file")
    parser.add_argument("--recursive", action="store_true", help="Scan directories recursively")

    args = parser.parse_args()

    extract_html_i18n(
        Path(args.source),
        Path(args.out),
        recursive=args.recursive
    )