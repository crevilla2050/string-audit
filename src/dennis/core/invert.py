from copy import deepcopy
from .sort import sort_changes
import json
import sys
from .serialize import dump_json


def invert_plan(plan: dict) -> dict:
    new_plan = deepcopy(plan)

    # meta adjustments
    meta = new_plan.setdefault("meta", {})
    meta["source_plan"] = meta.get("source_plan") or "inverted"
    meta["generated_at"] = meta.get("generated_at")

    inverted = []
    for c in plan["changes"]:
        inv = dict(c)
        inv["original"], inv["replacement"] = c["replacement"], c["original"]

        # Optional lineage
        if "id" in inv:
            inv["id"] = f"{inv['id']}-inv"

        inverted.append(inv)

    new_plan["changes"] = sort_changes(inverted)
    return new_plan

def cmd_invert(path, stdout=False):
    with open(path) as f:
        plan = json.load(f)

    inv = invert_plan(plan)

    if stdout:
        dump_json(inv, sys.stdout)
    else:
        out = path.replace(".json", ".undo.json")
        with open(out, "w") as f:
            dump_json(inv, f)
        print(f"Generated {out}")