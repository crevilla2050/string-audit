from copy import deepcopy
from .sort import sort_changes
import json
import sys
from .serialize import dump_json
import datetime


def invert_plan(plan: dict) -> dict:

    new_plan = {}

    # --------------------------------------
    # meta
    # --------------------------------------

    meta = deepcopy(plan.get("meta", {}))
    meta["generated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    meta["operation"] = "invert"

    new_plan["meta"] = meta

    # --------------------------------------
    # invert transformations
    # --------------------------------------

    inverted = []

    for c in plan.get("changes", []):
    
        # --------------------------------------
        # Skip helper changes (handled via patches)
        # --------------------------------------
        if c.get("type") == "helper":
            inverted.append({
                "type": "helper_remove",
                "helper_id": c.get("helper_id") or c.get("id"),
                "file": c.get("file"),
                "line": c.get("line"),
                "helper_ref": c.get("helper_ref"),   # ← THIS IS THE FIX
            })
            continue

        inv = dict(c)

        inv["original"], inv["replacement"] = c["replacement"], c["original"]

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
