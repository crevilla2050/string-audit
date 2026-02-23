# core/schema.py
import json
from importlib import resources

def validate_plan(plan):
    with resources.files("string_audit.schemas").joinpath("plan.schema.json").open("r") as f:
        schema = json.load(f)