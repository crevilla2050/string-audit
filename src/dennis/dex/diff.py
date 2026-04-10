import json
from dennis.dex.importer import import_dex

NON_SEMANTIC_FIELDS = {"confidence", "notes"}


def normalize_change(change, semantic=True):
    if not semantic:
        return change

    return {
        k: v for k, v in change.items()
        if k not in NON_SEMANTIC_FIELDS
    }


def index_changes(plan, semantic=True):
    result = {}

    for c in plan.get("changes", []):
        cid = c.get("id")

        if cid is None:
            cid = f"{c.get('file')}:{c.get('line')}:{c.get('original')}"

        result[cid] = normalize_change(c, semantic)

    return result


def diff_dex(artifact_a, artifact_b, ignore_semantics=False):
    semantic = not ignore_semantics

    manifestA, payloadA = import_dex(artifact_a)
    manifestB, payloadB = import_dex(artifact_b)

    planA = json.loads(payloadA)
    planB = json.loads(payloadB)

    helpersA = {
        h.get("id"): h
        for h in planA.get("patches", {}).get("helpers", [])
        if h.get("id")
    }

    helpersB = {
        h.get("id"): h
        for h in planB.get("patches", {}).get("helpers", [])
        if h.get("id")
    }

    changesA = index_changes(planA, semantic)
    changesB = index_changes(planB, semantic)

    added = sorted(changesB.keys() - changesA.keys())
    removed = sorted(changesA.keys() - changesB.keys())

    common = changesA.keys() & changesB.keys()

    modified = []

    helpers_added = sorted(helpersB.keys() - helpersA.keys())
    helpers_removed = sorted(helpersA.keys() - helpersB.keys())

    for cid in sorted(common):
        if changesA[cid] != changesB[cid]:

            diffs = {}

            for k in set(changesA[cid]) | set(changesB[cid]):
                if changesA[cid].get(k) != changesB[cid].get(k):
                    diffs[k] = {
                        "A": changesA[cid].get(k),
                        "B": changesB[cid].get(k)
                    }

            # ----------------------------------------
            # classify change type (NEW)
            # ----------------------------------------
            only_schema = all(
                (v["A"] is None) or (v["B"] is None)
                for v in diffs.values()
            )

            change_type = "schema_drift" if only_schema else "semantic"

            modified.append({
                "id": cid,
                "file": changesA[cid].get("file"),
                "line": changesA[cid].get("line"),
                "change_type": change_type,
                "differences": diffs
            })

    payload_equal = (
        manifestA["payload"]["hash"]["value"]
        == manifestB["payload"]["hash"]["value"]
    )

    meta_diff = {
        "lineage_changed": manifestA.get("lineage") != manifestB.get("lineage"),
        "signatures_changed": manifestA.get("signatures") != manifestB.get("signatures"),
        "type_changed": manifestA.get("lineage", {}).get("type") != manifestB.get("lineage", {}).get("type"),
    }

    lineageA = manifestA.get("lineage", {})
    lineage_typeA = lineageA.get("type")

    if lineage_typeA == "root":
        node_type = "root"
    elif payload_equal:
        node_type = "noop"
    else:
        node_type = "derived"

    return {
        "artifact_a": manifestA["payload"]["hash"]["value"],
        "artifact_b": manifestB["payload"]["hash"]["value"],
        "payload_hash_a": manifestA["payload"]["hash"]["value"],
        "payload_hash_b": manifestB["payload"]["hash"]["value"],
        "payload_equal": payload_equal,
        "node_type": node_type,
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "modified": len(modified),
            "helpers_added": len(helpers_added),
            "helpers_removed": len(helpers_removed)
        },
        "added": added,
        "removed": removed,
        "modified": modified,
        "metadata": {
            "differences": meta_diff
        },
        "helpers": {
            "added": helpers_added,
            "removed": helpers_removed
        }
    }