import csv
import json
from pathlib import Path


def export_dictionary_to_csv(dict_path: Path, csv_path: Path) -> None:
    """
    Export dictionary.json → CSV for human editing.
    """

    data = json.loads(dict_path.read_text(encoding="utf-8"))

    with open(csv_path, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)
        writer.writerow(["token", "text"])

        for token, text in sorted(data.items()):
            writer.writerow([token, text])


def import_dictionary_from_csv(csv_path: Path, dict_path: Path) -> None:
    """
    Import edited CSV back into dictionary.json.
    """

    mapping = {}

    with open(csv_path, newline="", encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for row in reader:

            token = row.get("token", "").strip()
            text = row.get("text", "").strip()

            if token:
                mapping[token] = text

    dict_path.write_text(
        json.dumps(mapping, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )