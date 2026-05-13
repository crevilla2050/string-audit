import json
from dennis.dex.importer import import_dex

NON_SEMANTIC_FIELDS = {"confidence", "notes"}


def is_helper_op(op):
    return op.get("semantic") is True and "helper_id" in op


def is_helper_add(op):
    return is_helper_op(op) and op.get("type") == "added"


def is_helper_remove(op):
    return is_helper_op(op) and op.get("type") == "removed"


def is_helper_modified(op):
    return is_helper_op(op) and op.get("type") == "modified"


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
            file_path = c.get("file")
            line = c.get("line")
            original = c.get("original")
            change_type = c.get("type")

            helper_id = c.get("helper_id")
            helper_ref = c.get("helper_ref")

            # Prefer semantic identity for helpers
            if helper_id:
                identity = f"helper:{helper_id}"
            elif helper_ref:
                identity = f"helper:{helper_ref}"
            elif original is not None:
                identity = str(original)
            else:
                identity = change_type or "unknown"

            cid = f"{file_path}:{line}:{identity}"

        result[cid] = normalize_change(c, semantic)

    return result


def _parse_change_id(change_id):
    """
    Parse legacy change id format:
      file:line:content
    into structured pieces.
    """
    if not isinstance(change_id, str):
        return None, None, None

    parts = change_id.split(":", 2)

    if len(parts) == 1:
        return parts[0], None, None

    if len(parts) == 2:
        file_path, line_raw = parts
        try:
            line = int(line_raw)
        except (TypeError, ValueError):
            line = None
        return file_path, line, None

    file_path, line_raw, content = parts

    try:
        line = int(line_raw)
    except (TypeError, ValueError):
        line = None
    
    content = content.lstrip()

    return file_path, line, content


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

    # ----------------------------------------
    # Semantic helper lifecycle tracking
    # Canonical source of truth = changes[]
    # ----------------------------------------

    helpers_added = set()
    helpers_removed = set()

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
            # classify change type
            # ----------------------------------------

            only_schema = all(
                (v["A"] is None) or (v["B"] is None)
                for v in diffs.values()
            )

            change_type = (
                "schema_drift"
                if only_schema
                else "semantic"
            )

            modified.append({
                "id": cid,
                "file": changesA[cid].get("file"),
                "line": changesA[cid].get("line"),
                "change_type": change_type,
                "differences": diffs
            })

            # ----------------------------------------
            # Semantic helper lifecycle extraction
            # ----------------------------------------

            type_diff = diffs.get("type", {})

            type_a = type_diff.get("A")
            type_b = type_diff.get("B")

            # Helper removed
            if type_a == "helper" and type_b == "helper_remove":

                helper_ref = (
                    changesA[cid].get("helper_ref")
                    or diffs.get("helper_ref", {}).get("A")
                )

                if helper_ref:
                    helpers_removed.add(helper_ref)

            # Helper added
            elif type_b == "helper" and type_a != "helper":

                helper_ref = (
                    changesB[cid].get("helper_ref")
                    or diffs.get("helper_ref", {}).get("B")
                )

                if helper_ref:
                    helpers_added.add(helper_ref)

    payload_equal = (
        manifestA["payload"]["hash"]["value"]
        == manifestB["payload"]["hash"]["value"]
    )

    meta_diff = {
        "lineage_changed": (
            manifestA.get("lineage")
            != manifestB.get("lineage")
        ),

        "signatures_changed": (
            manifestA.get("signatures")
            != manifestB.get("signatures")
        ),

        "type_changed": (
            manifestA.get("lineage", {}).get("type")
            != manifestB.get("lineage", {}).get("type")
        ),
    }

    lineageA = manifestA.get("lineage", {})
    lineage_typeA = lineageA.get("type")

    if lineage_typeA == "root":
        node_type = "root"

    elif payload_equal:
        node_type = "noop"

    else:
        node_type = "derived"

    # ----------------------------------------
    # Canonical grouped file IR
    # ----------------------------------------

    grouped_files = {}

    def ensure_file(path):

        if path not in grouped_files:

            grouped_files[path] = {
                "path": path,

                "summary": {
                    "added": 0,
                    "removed": 0,
                    "modified": 0
                },

                "operations": [],

                "added": [],
                "removed": [],
                "modified": []
            }
    
    def _enrich_helper_op(op, source_change, change_id=None):
        """
        Attach semantic helper metadata to operation if applicable.
        """
        candidate_a = changesA.get(change_id, {}) if change_id is not None else {}
        candidate_b = changesB.get(change_id, {}) if change_id is not None else {}

        semantic_source = source_change or candidate_a or candidate_b
        if not semantic_source:
            return op

        helper_identity_present = (
            ("helper_id" in semantic_source)
            or ("helper_id" in candidate_a)
            or ("helper_id" in candidate_b)
        )

        if helper_identity_present:
            op["semantic"] = True

            helper_id = (
                semantic_source.get("helper_id")
                or candidate_a.get("helper_id")
                or candidate_b.get("helper_id")
            )
            helper_ref = (
                semantic_source.get("helper_ref")
                or candidate_a.get("helper_ref")
                or candidate_b.get("helper_ref")
            )
            if not helper_ref and helper_id:
                helper_ref = f"helpers/helper_{helper_id}.py"

            if helper_id:
                op["helper_id"] = helper_id

            if helper_ref:
                op["helper_ref"] = helper_ref

        return op

    # ----------------------------------------
    # Added
    # ----------------------------------------
    
    for item in added:

        file_path, line, content = _parse_change_id(item)

        ensure_file(file_path)

        grouped_files[file_path]["added"].append(item)
        op = {
            "type": "added",
            "line": line,
            "content": content
        }

        # Try to recover semantic source from B side
        source_change = changesB.get(item)

        op = _enrich_helper_op(op, source_change, item)

        if op.get("semantic"):
            assert "helper_id" in op
            assert "helper_ref" in op
            op.pop("content", None)

        grouped_files[file_path]["operations"].append(op)

        grouped_files[file_path]["summary"]["added"] += 1

    # ----------------------------------------
    # Removed
    # ----------------------------------------

    for item in removed:

        file_path, line, content = _parse_change_id(item)

        ensure_file(file_path)

        grouped_files[file_path]["removed"].append(item)
        op = {
            "type": "removed",
            "line": line,
            "content": content
        }

        # Try to recover semantic source from A side
        source_change = changesA.get(item)

        op = _enrich_helper_op(op, source_change, item)

        if op.get("semantic"):
            assert "helper_id" in op
            assert "helper_ref" in op
            op.pop("content", None)

        grouped_files[file_path]["operations"].append(op)

        grouped_files[file_path]["summary"]["removed"] += 1

    # ----------------------------------------
    # Modified
    # ----------------------------------------

    for item in modified:

        file_path = item.get("file")

        ensure_file(file_path)

        grouped_files[file_path]["modified"].append(item)
        op = {
            "type": "modified",
            "line": item.get("line"),
            "change_type": item.get("change_type"),
            "differences": item.get("differences"),
            "before": changesA[item["id"]],
            "after": changesB[item["id"]]
        }

        # ----------------------------------------
        # Semantic helper enrichment (modified)
        # ----------------------------------------

        before = changesA[item["id"]]
        after = changesB[item["id"]]

        if (
            before.get("type") in ("helper", "helper_remove") or
            after.get("type") in ("helper", "helper_remove")
        ):
            op["semantic"] = True

            helper_id = (
                before.get("helper_id") or
                after.get("helper_id")
            )

            helper_ref = (
                before.get("helper_ref") or
                after.get("helper_ref")
            )

            if helper_id:
                op["helper_id"] = helper_id

            if helper_ref:
                op["helper_ref"] = helper_ref

        grouped_files[file_path]["operations"].append(op)

        grouped_files[file_path]["summary"]["modified"] += 1

    files_list = list(grouped_files.values())

    for f in grouped_files.values():
        f["operations"] = sorted(
            f["operations"],
            key=lambda op: (
                op.get("line", 0),
                {"removed": 0, "added": 1, "modified": 2}.get(op.get("type"), 99)
            )
        )

    return {

        "protocol": {
            "version": 1
        },

        "artifacts": {

            "a": {
                "artifact_hash": manifestA["payload"]["hash"]["value"],
                "payload_hash": manifestA["payload"]["hash"]["value"]
            },

            "b": {
                "artifact_hash": manifestB["payload"]["hash"]["value"],
                "payload_hash": manifestB["payload"]["hash"]["value"]
            }
        },

        "payload_equal": payload_equal,

        "node_type": node_type,

        "summary": {
            "added": len(added),
            "removed": len(removed),
            "modified": len(modified),
            "helpers_added": len(helpers_added),
            "helpers_removed": len(helpers_removed)
        },

        # ----------------------------------------
        # Canonical grouped diff structure
        # ----------------------------------------

        "files": files_list,

        # ----------------------------------------
        # Transitional compatibility layer
        # ----------------------------------------

        "added": added,
        "removed": removed,
        "modified": modified,

        "metadata": {
            "differences": meta_diff
        },

        "helpers": {
            "added": sorted(helpers_added),
            "removed": sorted(helpers_removed)
        }
    }