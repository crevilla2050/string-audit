import json


def export_txt(plan, out_file):
    """
    Export plan dictionary as simple TXT key=value format.
    """

    dictionary = {}

    for change in plan.get("changes", []):
        token = change.get("token")
        original = change.get("original")

        if not token or not original:
            continue

        text = original.strip().strip('"').strip("'")
        dictionary[token] = text

    for token, text in sorted(dictionary.items()):
        out_file.write(f"{token}={text}\n")