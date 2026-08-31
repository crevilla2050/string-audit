from pathlib import Path

from dennis.hound import sniff_file
from dennis.watsons import utf8


def inspect_file(path: Path) -> dict:
    """
    Mickey decides whether a file is admitted into Dennis.

    Mickey does not inspect the file's contents himself.
    He relies on The Hound's report.

    The final decision is deliberately simple:
    valid files are admitted; invalid files are rejected.
    """

    report = sniff_file(path)

    if report.get("valid") is True:
        data = path.read_bytes()
        text = utf8.decode(data)

        return {
            "admitted": True,
            "report": report,
            "text": text,
        }

    return {
        "admitted": False,
        "report": report,
    }