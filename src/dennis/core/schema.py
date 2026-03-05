# core/schema.py
import json
from importlib import resources


def _load_schema():
    # Prefer Dennis-native location
    try:
        with resources.files("dennis.schemas").joinpath("plan.schema.json").open("r") as f:
            return json.load(f)
    except ModuleNotFoundError:
        # Backward compatibility fallback
        with resources.files("string_audit.schemas").joinpath("plan.schema.json").open("r") as f:
            return json.load(f)
        
def validate_plan(plan):
    with resources.files("dennis.schemas").joinpath("plan.schema.json").open("r") as f:
        schema = _load_schema()