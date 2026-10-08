import json
import tempfile
from pathlib import Path
import pytest

from dennis.dex.canonical_diff import generate_planned_diff, normalize_plan_path
from dennis.dex.pack import collect_project_files


def test_normalize_plan_path_ignores_payload_subdir():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "payload").mkdir()
        (root / "hello.py").write_text('print("Hello world.")\n', encoding="utf-8")

        normalized = normalize_plan_path("hello.py", root)

        assert normalized == Path("hello.py")


def test_generate_planned_diff_applies_replacements_and_helpers():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        helper_dir = root / "helpers"
        helper_dir.mkdir()

        # Original file state in snapshot
        (root / "hello.py").write_text('print("Hello world.")\n', encoding="utf-8")
        (helper_dir / "helper_test.py").write_text('def helper():\n    return True\n', encoding="utf-8")

        plan = {
            "meta": {
                "generated_at": "2026-04-30T00:00:00Z",
                "project_root": str(root),
                "dictionary": "dictionary.json",
            },
            "changes": [
                {
                    "file": "hello.py",
                    "line": 1,
                    "original": 'print("Hello world.")',
                    "replacement": 'print(messages["HELLO_WORLD"])',
                    "token": "HELLO_WORLD"
                },
                {
                    "type": "helper",
                    "file": "hello.py",
                    "line": 1,
                    "helper_ref": "helpers/helper_test.py",
                    "helper_source": "helper_test.py",
                    "helper_id": "testhelper"
                }
            ]
        }

        artifact = generate_planned_diff(plan, base_dir=root)

        assert artifact["type"] == "dennis.diff.v1"
        assert artifact["payload"]["files"]

        file_paths = {f["path"]: f for f in artifact["payload"]["files"]}
        target_file = plan["changes"][0]["file"]

        assert target_file in file_paths
        assert file_paths[target_file]["status"] == "modified"
        assert any(change["type"] in {"insert", "replace"} for change in file_paths[target_file]["changes"])

        # Helper injection should be wrapped with marker lines like apply()
        helper_changes = file_paths[target_file]["changes"]
        assert any(
            ["# >>> DENNIS HELPER START: testhelper"] == change.get("after", [])[:1]
            for change in helper_changes
        )

        assert "helpers/helper_test.py" in file_paths
        assert file_paths["helpers/helper_test.py"]["status"] == "added"
        assert file_paths["helpers/helper_test.py"]["changes"][0]["type"] == "insert"
        assert file_paths["helpers/helper_test.py"]["changes"][0]["after"] == ['def helper():', '    return True']


def test_generate_planned_diff_preserves_scheduler_replacements_after_helper_insertion():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        helper_dir = root / "helpers"
        helper_dir.mkdir()

        (root / "hello.py").write_text(
            'print("Before helper")\n'
            'print("Hello world.")\n'
            'print("Goodbye")\n',
            encoding="utf-8"
        )
        (helper_dir / "helper_test.py").write_text(
            'def helper():\n    return True\n',
            encoding="utf-8"
        )

        plan = {
            "meta": {
                "generated_at": "2026-04-30T00:00:00Z",
                "project_root": str(root),
                "dictionary": "dictionary.json",
            },
            "changes": [
                {
                    "type": "helper",
                    "file": "hello.py",
                    "line": 1,
                    "helper_ref": "helpers/helper_test.py",
                    "helper_source": "helper_test.py",
                    "helper_id": "testhelper"
                },
                {
                    "file": "hello.py",
                    "line": 3,
                    "original": 'print("Goodbye")',
                    "replacement": 'print(messages["GOODBYE"])',
                    "token": "GOODBYE"
                }
            ]
        }

        artifact = generate_planned_diff(plan, base_dir=root)
        file_paths = {f["path"]: f for f in artifact["payload"]["files"]}
        hello_file = file_paths["hello.py"]

        assert hello_file["status"] == "modified"
        assert any(
            'print(messages["GOODBYE"])' in change.get("after", [])
            for change in hello_file["changes"]
        )


def test_generate_planned_diff_loads_helper_from_helper_source_if_not_in_snapshot():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Original source contains no helpers directory
        (root / "hello.py").write_text('print("Hello world.")\n', encoding="utf-8")
        (root / "helper_test.py").write_text('def helper():\n    return True\n', encoding="utf-8")

        plan = {
            "meta": {
                "generated_at": "2026-04-30T00:00:00Z",
                "project_root": str(root),
                "dictionary": "dictionary.json",
            },
            "changes": [
                {
                    "file": "hello.py",
                    "line": 1,
                    "original": 'print("Hello world.")',
                    "replacement": 'print(messages["HELLO_WORLD"])',
                    "token": "HELLO_WORLD"
                },
                {
                    "type": "helper",
                    "file": "hello.py",
                    "line": 1,
                    "helper_ref": "helpers/helper_test.py",
                    "helper_source": "helper_test.py",
                    "helper_id": "testhelper"
                }
            ]
        }

        artifact = generate_planned_diff(plan, base_dir=root)

        file_paths = {f["path"]: f for f in artifact["payload"]["files"]}

        assert "helpers/helper_test.py" in file_paths
        assert file_paths["helpers/helper_test.py"]["status"] == "added"
        assert file_paths["helpers/helper_test.py"]["changes"][0]["type"] == "insert"
        assert file_paths["helpers/helper_test.py"]["changes"][0]["after"] == ['def helper():', '    return True']


def test_collect_project_files_requires_dennis_directory(tmp_path):
    project_file = tmp_path / "hello.txt"
    project_file.write_text("hello", encoding="utf-8")

    with pytest.raises(
        RuntimeError,
        match="Dennis project context not found"
    ):
        collect_project_files(tmp_path)

def test_collect_project_files_includes_dennis_context(tmp_path):
    project_file = tmp_path / "hello.txt"
    project_file.write_text("hello", encoding="utf-8")

    dennis_dir = tmp_path / ".dennis"
    dennis_dir.mkdir()

    provenance = dennis_dir / "provenance.json"
    provenance.write_text("{}", encoding="utf-8")

    files = collect_project_files(tmp_path)

    assert project_file in files
    assert provenance in files

def test_collect_project_files_honors_gitignore(tmp_path):
    (tmp_path / ".gitignore").write_text(
        "ignored.txt\n",
        encoding="utf-8"
    )

    ignored = tmp_path / "ignored.txt"
    ignored.write_text("ignore me", encoding="utf-8")

    dennis_dir = tmp_path / ".dennis"
    dennis_dir.mkdir()

    provenance = dennis_dir / "provenance.json"
    provenance.write_text("{}", encoding="utf-8")

    files = collect_project_files(tmp_path)

    assert ignored not in files
    assert provenance in files

def test_collect_project_files_dennis_overrides_gitignore(tmp_path):
    (tmp_path / ".gitignore").write_text(
        ".dennis/\n",
        encoding="utf-8"
    )

    dennis_dir = tmp_path / ".dennis"
    dennis_dir.mkdir()

    provenance = dennis_dir / "provenance.json"
    provenance.write_text("{}", encoding="utf-8")

    files = collect_project_files(tmp_path)

    assert provenance in files

def test_collect_project_files_excludes_dex_artifacts(tmp_path):
    dex = tmp_path / "old-artifact.dex"
    dex.write_bytes(b"not project input")

    dennis_dir = tmp_path / ".dennis"
    dennis_dir.mkdir()

    provenance = dennis_dir / "provenance.json"
    provenance.write_text("{}", encoding="utf-8")

    files = collect_project_files(tmp_path)

    assert dex not in files