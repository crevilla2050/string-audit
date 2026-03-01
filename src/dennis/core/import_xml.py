import xml.etree.ElementTree as ET


def import_xml(fp) -> dict:
    """
    Import a Dennis XML plan into canonical JSON structure.
    """

    tree = ET.parse(fp)
    root = tree.getroot()

    if root.tag != "dennis":
        raise ValueError("Not a Dennis XML file")

    version = root.attrib.get("version", "unknown")

    # --- Meta ---
    meta_node = root.find("meta")
    generated_at = meta_node.attrib.get("generated_at", "unknown") if meta_node is not None else "unknown"

    plan = {
        "meta": {
            "tool": "dennis",
            "version": version,
            "generated_at": generated_at,
        },
        "changes": [],
    }

    # --- Changes ---
    changes_node = root.find("changes")
    if changes_node is None:
        return plan

    for ch in changes_node.findall("change"):
        change = {
            "id": ch.attrib.get("id"),
            "token": ch.attrib.get("token"),
            "file": _text(ch, "file"),
            "line": int(_text(ch, "line") or 0),
            "original": _text(ch, "original"),
            "replacement": _text(ch, "replacement"),
        }
        plan["changes"].append(change)

    return plan


def _text(parent, tag):
    node = parent.find(tag)
    return node.text if node is not None else ""