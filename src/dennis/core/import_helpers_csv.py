import csv


def load_helpers_from_csv(path):
    helpers = []

    with open(path, newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            helpers.append({
                "helper": row["helper_file"],
                "target": row["target_file"],
                "line": int(row["line"]),
            })

    return helpers