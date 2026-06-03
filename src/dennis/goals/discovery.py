from collections import Counter
from datetime import datetime, timezone

def ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

GOAL_RULES = {
    "HUMAN": [
        "INTERNATIONALIZE_STRINGS",
    ],

    "SQL": [
        "EXTRACT_CONSTANTS",
    ],

    "URL": [
        "EXTERNALIZE_CONFIGURATION",
    ],

    "UNKNOWN": [
        "MANUAL_REVIEW_REQUIRED",
    ],
}


def discover_goals(obad: dict) -> dict:
    """
    Goal Discovery v0.1

    Converts observations into goal candidates.
    """

    evidence_counter = Counter()

    validate_obad(obad)

    for finding in obad.get("findings", []):

        semantic_type = finding.get("type")

        for goal in GOAL_RULES.get(semantic_type, []):

            evidence_counter[
                (goal, semantic_type)
            ] += 1

    goals = []

    for (goal, semantic_type), count in sorted(
        evidence_counter.items()
    ):

        goals.append(
            {
                "goal": goal,

                "evidence": {
                    "source_type": semantic_type,
                    "count": count,
                },

                "confidence": 1.0,
            }
        )

    return {
        "meta": {
            "format": "goal-discovery",
            "version": 1,
            "generated_at": ts(),
        },

        "goals": goals,
    }

def validate_obad(obad: dict) -> None:

    if not isinstance(obad, dict):
        raise ValueError("OBAD must be a dictionary")

    meta = obad.get("meta")

    if not meta:
        raise ValueError("Missing meta section")

    if meta.get("format") != "obad":
        raise ValueError(
            "Expected artifact format 'obad'"
        )

    findings = obad.get("findings")

    if not isinstance(findings, list):
        raise ValueError(
            "OBAD findings must be a list"
        )