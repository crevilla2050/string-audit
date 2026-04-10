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

def import_plan_csv(csv_path: Path, baseline=None, out=None) -> None:
    import csv, json
    from datetime import datetime, timezone

    def ts():
        return datetime.now(timezone.utc).isoformat()

    changes = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:

            file = row.get("file")
            line = row.get("line")

            if not file or not line:
                continue

            try:
                line = int(line)
            except ValueError:
                continue

            change_type = row.get("type") or "replace"

            if change_type == "helper":
                changes.append({
                    "type": "helper",
                    "helper_id": row.get("helper_id"),
                    "helper_ref": row.get("helper_path"),
                    "file": file,
                    "line": line,
                })
            else:
                changes.append({
                    "type": "replace",
                    "file": file,
                    "line": line,
                    "original": row.get("original"),
                    "replacement": row.get("replacement"),
                    "token": row.get("token"),
                })

    plan = {
        "meta": {
            "generated_at": ts(),
            "source": str(csv_path),
        },
        "changes": changes
    }

    if baseline:
        plan["meta"]["baseline"] = baseline

    output = Path(out) if out else csv_path.with_suffix(".json")

    output.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    print(f"[Dennis] Plan imported → {output}")