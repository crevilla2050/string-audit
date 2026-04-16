import os
import tarfile
import json
import tempfile


def validate_plan_from_artifact(path: str) -> dict:
    """
    Validate transformation plan inside a DEX artifact
    """

    errors = []
    warnings = []

    if not os.path.exists(path):
        return {
            "valid": False,
            "errors": ["Artifact not found"],
            "warnings": []
        }

    with tempfile.TemporaryDirectory() as tmp:

        try:
            with tarfile.open(path, "r:gz") as tar:
                tar.extractall(tmp)
        except Exception:
            return {
                "valid": False,
                "errors": ["Invalid or corrupted DEX archive"],
                "warnings": []
            }

        plan_path = os.path.join(tmp, "payload", "plan.json")

        if not os.path.exists(plan_path):
            return {
                "valid": False,
                "errors": ["Missing payload/plan.json"],
                "warnings": []
            }

        with open(plan_path) as f:
            plan = json.load(f)

        changes = plan.get("changes", [])

        if not changes:
            errors.append("Plan has no changes")

        seen = set()
        helper_refs = set()

        for idx, change in enumerate(changes):

            file = change.get("file")
            line = change.get("line")
            ctype = change.get("type", "replace")

            # --- basic structure ---
            if not file:
                errors.append(f"Change {idx}: missing 'file'")

            if line is None:
                errors.append(f"Change {idx}: missing 'line'")

            # --- duplicate detection ---
            key = (file, line, ctype)

            if key in seen:
                errors.append(f"Duplicate change at {file}:{line} ({ctype})")
            else:
                seen.add(key)

            # --- type-specific checks ---
            if ctype == "replace":
                if "replacement" not in change:
                    errors.append(f"{file}:{line} missing replacement")

            elif ctype == "helper":
                ref = change.get("helper_ref") or change.get("helper_id")

                if not ref:
                    errors.append(f"{file}:{line} helper missing reference")
                else:
                    helper_refs.add(ref)

        # --- helper existence check ---
        helpers_dir = os.path.join(tmp, "payload", "helpers")

        if os.path.exists(helpers_dir):
            available_helpers = set(os.listdir(helpers_dir))

            for ref in helper_refs:
                ref_name = os.path.basename(ref)

                if ref_name not in available_helpers:
                    errors.append(f"Missing helper file: {ref}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "changes": len(changes),
                "files": len(set(c.get("file") for c in changes if c.get("file")))
            }
        }