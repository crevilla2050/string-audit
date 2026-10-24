# core/schema.py
import json
from importlib import resources

import jsonschema


def _load_schema():
    with resources.files("dennis.schemas").joinpath("plan.schema.json").open(
        "r", encoding="utf-8"
    ) as schema_file:
        return json.load(schema_file)


def validate_plan(plan):
    """Validate a Dennis plan against the packaged canonical schema.

    Valid plans return normally. Invalid plans raise
    :class:`jsonschema.ValidationError`; schema-loading errors deliberately
    propagate to callers.
    """
    jsonschema.validate(
        instance=plan,
        schema=_load_schema(),
        format_checker=jsonschema.FormatChecker(),
    )
