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
        inv = dict(c)

        inv["original"], inv["replacement"] = c["replacement"], c["original"]

        if "id" in inv:
            inv["id"] = f"{inv['id']}-inv"

        inverted.append(inv)

    new_plan["changes"] = sort_changes(inverted)

    # --------------------------------------
    # invert helper patches
    # --------------------------------------

    patches = plan.get("patches")

    if patches and "helpers" in patches:

        new_plan["patches"] = {
            "remove_helpers": patches["helpers"]
        }
       
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
