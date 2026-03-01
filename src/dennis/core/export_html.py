from html import escape
from datetime import datetime


def export_html(plan: dict, fp):
    """
    Export a Dennis plan into minimal semantic HTML.

    Philosophy:
    - Zero styling
    - Deterministic ordering
    - Human readable
    """

    changes = sorted(plan.get("changes", []), key=lambda c: (c["file"], c["line"]))

    def w(line=""):
        fp.write(line + "\n")

    # Header
    w("<!DOCTYPE html>")
    w("<html>")
    w("<head>")
    w('<meta charset="utf-8">')
    w("<title>Dennis Plan</title>")
    w("</head>")
    w("<body>")

    w("<h1>Dennis Plan</h1>")
    w(f"<p><i>Generated: {escape(plan.get('meta', {}).get('generated_at', 'unknown'))}</i></p>")
    w("<hr>")

    # Changes
    for change in changes:
        w('<div class="change">')

        token = escape(change.get("token", ""))
        file_ = escape(change.get("file", ""))
        line = change.get("line", "")
        original = escape(change.get("original", ""))
        replacement = escape(change.get("replacement", ""))

        w(f"<h3>{token}</h3>")
        w(f"<p><b>File:</b> {file_}</p>")
        w(f"<p><b>Line:</b> {line}</p>")
        w(f"<p><b>Original:</b> {original}</p>")
        w(f"<p><b>Replacement:</b> {replacement}</p>")
        w("<hr>")
        w("</div>")

    # Footer
    w("<p><i>Forged by Dennis the Forge</i></p>")
    w("</body>")
    w("</html>")