"""
DEX Manifest Validation
Dennis v1
"""

import json
from pathlib import Path
from importlib import resources

import jsonschema


def load_schema():
    """
    Load the DEX manifest JSON schema.
    """

    with resources.files("dennis.schemas").joinpath("dex.manifest.schema.json").open("r") as f:
        return json.load(f)


def validate_manifest(manifest):
    """
    Validate a manifest dictionary against schema.
    """

    schema = load_schema()

    jsonschema.validate(
        instance=manifest,
        schema=schema
    )


def validate_manifest_file(path):
    """
    Validate a manifest file from disk.
    """

    path = Path(path)
    manifest = json.loads(path.read_text())
    validate_manifest(manifest)

    return True