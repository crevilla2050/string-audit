import json
import sys
import tempfile
from pathlib import Path

import pytest

from dennis.cli import main


def test_verify_execution_scope_mismatch_strict(monkeypatch, capsys):
    expected = {
        "type": "dennis.diff.v1",
        "payload": {
            "files": [
                {
                    "path": "a.txt",
                    "status": "modified",
                    "changes": [
                        {
                            "type": "replace",
                            "start_line": 1,
                            "end_line": 1,
                            "before": ["old"],
                            "after": ["new"]
                        }
                    ]
                }
            ]
        }
    }

    observed = {
        "type": "dennis.diff.v1",
        "payload": {
            "files": [
                {
                    "path": "a.txt",
                    "status": "modified",
                    "changes": [
                        {
                            "type": "replace",
                            "start_line": 1,
                            "end_line": 1,
                            "before": ["old"],
                            "after": ["new"]
                        }
                    ]
                },
                {
                    "path": "b.txt",
                    "status": "added",
                    "changes": [
                        {
                            "type": "insert",
                            "start_line": 1,
                            "end_line": 1,
                            "before": [],
                            "after": ["extra"]
                        }
                    ]
                }
            ]
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        expected_path = Path(tmpdir) / "expected.json"
        observed_path = Path(tmpdir) / "observed.json"
        expected_path.write_text(json.dumps(expected), encoding="utf-8")
        observed_path.write_text(json.dumps(observed), encoding="utf-8")

        monkeypatch.setattr(sys, "argv", [
            "dennis",
            "verify-execution",
            "--expected",
            str(expected_path),
            "--observed",
            str(observed_path),
            "--strict"
        ])

        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 1

        captured = capsys.readouterr()
        assert "Unexpected files detected" in captured.out
        assert "Scope mismatch detected" in captured.out
