from xml.sax.saxutils import escape


def export_xml(plan: dict, fp):
    """
    Export a Dennis plan as deterministic XML.
    """

    changes = sorted(plan.get("changes", []), key=lambda c: (c["file"], c["line"]))
    meta = plan.get("meta", {})

    def w(line=""):
        fp.write(line + "\n")

    w('<?xml version="1.0" encoding="UTF-8"?>')
    w(f'<plan version="{escape(str(meta.get("version", "unknown")))}">')

    generated = escape(meta.get("generated_at", "unknown"))
    w(f'  <meta generated_at="{generated}"/>')
    w("")
    w("  <changes>")

    for change in changes:
        token = escape(change.get("token", ""))
        cid = escape(str(change.get("id", "")))

        w(f'    <change id="{cid}" token="{token}">')
        w(f'      <file>{escape(change.get("file", ""))}</file>')
        w(f'      <line>{change.get("line", "")}</line>')
        w(f'      <original>{escape(change.get("original", ""))}</original>')
        w(f'      <replacement>{escape(change.get("replacement", ""))}</replacement>')
        w("    </change>")
        w("")

    w("  </changes>")
    w("</plan>")