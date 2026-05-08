import pytest
from dennis.dex.manifest import build_derived_lineage, build_root_lineage, build_detached_lineage


def test_build_root_lineage():
    payload_hash = "abc123"
    lineage = build_root_lineage(payload_hash)
    assert lineage["lineage_id"] == payload_hash
    assert lineage["parent"] is None
    assert lineage["type"] == "root"


def test_build_derived_lineage():
    parent_manifest = {
        "payload": {
            "hash": {
                "value": "parent_hash_123"
            }
        }
    }
    payload_hash = "child_hash_456"
    lineage = build_derived_lineage(parent_manifest, payload_hash)
    assert lineage["lineage_id"] == payload_hash
    assert lineage["parent"] == "parent_hash_123"
    assert lineage["type"] == "derived"


def test_build_detached_lineage():
    lineage = build_detached_lineage()
    assert lineage["lineage_id"] is None
    assert lineage["parent"] is None
    assert lineage["type"] == "detached"