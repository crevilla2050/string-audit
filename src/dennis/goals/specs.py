from datetime import datetime, timezone

def timestamp():
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H-%M-%S"
    )

def validate_goal_discovery(artifact: dict) -> None:

    if not isinstance(artifact, dict):
        raise ValueError(
            "Goal Discovery artifact must be a dictionary"
        )

    meta = artifact.get("meta")

    if not meta:
        raise ValueError(
            "Missing meta section"
        )

    if meta.get("format") != "goal-discovery":
        raise ValueError(
            "Expected artifact format 'goal-discovery'"
        )

    goals = artifact.get("goals")

    if not isinstance(goals, list):
        raise ValueError(
            "Goal Discovery goals must be a list"
        )
    
SPEC_RULES = {
    "INTERNATIONALIZE_STRINGS": {
        "requirements": [
            "Extract human-readable strings",
            "Create translation keys",
            "Externalize messages",
        ]
    },

    "EXTRACT_CONSTANTS": {
        "requirements": [
            "Replace repeated literals with constants",
        ]
    },

    "EXTERNALIZE_CONFIGURATION": {
        "requirements": [
            "Move URLs into configuration",
        ]
    },

    "MANUAL_REVIEW_REQUIRED": {
        "requirements": [
            "Review unknown observations",
        ]
    },
}

def discover_specs(goal_artifact: dict) -> dict:

    validate_goal_discovery(goal_artifact)

    specs = []

    for goal in goal_artifact.get("goals", []):

        goal_name = goal.get("goal")

        rule = SPEC_RULES.get(goal_name)

        if not rule:
            continue

        specs.append(
            {
                "intent": goal_name,

                "requirements": rule["requirements"],

                "evidence": goal.get(
                    "evidence",
                    {},
                ),
            }
        )

    return {
        "meta": {
            "format": "spec-discovery",
            "version": 1,
            "generated_at": timestamp(),
        },

        "specs": specs,

        "lineage": {
            "derived_from": []
        },
    }

def validate_spec_discovery(artifact: dict) -> None:

    if not isinstance(artifact, dict):
        raise ValueError(
            "Spec Discovery artifact must be a dictionary"
        )

    meta = artifact.get("meta")

    if not meta:
        raise ValueError(
            "Missing meta section"
        )

    if meta.get("format") != "spec-discovery":
        raise ValueError(
            "Expected artifact format 'spec-discovery'"
        )

    specs = artifact.get("specs")

    if not isinstance(specs, list):
        raise ValueError(
            "Spec Discovery specs must be a list"
        )