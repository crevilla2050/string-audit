from copy import deepcopy

import pytest
from jsonschema import ValidationError

from dennis.core.invert import invert_plan
from dennis.core.schema import validate_plan
from dennis.i18n.plan import generate_plan


def replacement_change():
    return {
        "file": "src/example.py",
        "line": 3,
        "original": 'print("hello")',
        "replacement": 'print(messages["HELLO"])',
        "token": "HELLO",
    }


def plan_with(*changes):
    return {
        "meta": {
            "tool": "dennis",
            "version": "0.9.3",
            "generated_at": "2026-10-23T12:00:00Z",
            "project_root": "/work/project",
            "dictionary": "dictionary.json",
        },
        "changes": list(changes),
    }


def helper_change():
    return {
        "type": "helper",
        "helper_id": "extract_messages",
        "file": "src/example.py",
        "line": 1,
        "helper_ref": "helpers/extract_messages.py",
        "helper_source": "tools/extract_messages.py",
    }


def test_valid_generated_plan_passes_schema_validation(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    dictionary = tmp_path / "dictionary.json"

    plan = generate_plan(source, dictionary)

    assert plan["meta"]["tool"] == "dennis"
    assert plan["meta"]["version"] == "0.9.3"
    assert validate_plan(plan) is None


def test_supported_operation_forms_pass_schema_validation():
    plan = plan_with(replacement_change(), helper_change())

    validate_plan(plan)

    inverted = invert_plan(plan)
    assert inverted["meta"]["operation"] == "invert"
    assert inverted["changes"][0]["type"] == "helper_remove"
    validate_plan(inverted)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda plan: plan.pop("meta"),
        lambda plan: plan["meta"].pop("tool"),
        lambda plan: plan["meta"].__setitem__("version", ""),
        lambda plan: plan["meta"].__setitem__("generated_at", "not-a-timestamp"),
        lambda plan: plan["changes"][0].__setitem__("line", 0),
        lambda plan: plan["changes"][0].__setitem__("type", "replace"),
    ],
)
def test_invalid_plan_raises_validation_error(mutate):
    plan = plan_with(replacement_change())
    mutate(plan)

    with pytest.raises(ValidationError):
        validate_plan(plan)


@pytest.mark.parametrize(
    ("change", "missing_field"),
    [
        (replacement_change(), "original"),
        (helper_change(), "helper_source"),
        (
            {
                "type": "helper_remove",
                "helper_id": "extract_messages",
                "file": "src/example.py",
                "line": 1,
                "helper_ref": "helpers/extract_messages.py",
            },
            "helper_ref",
        ),
    ],
)
def test_operation_specific_required_fields_are_enforced(change, missing_field):
    change = deepcopy(change)
    change.pop(missing_field)

    with pytest.raises(ValidationError):
        validate_plan(plan_with(change))


def test_unknown_operation_type_is_rejected():
    change = replacement_change()
    change["type"] = "rename"

    with pytest.raises(ValidationError):
        validate_plan(plan_with(change))
