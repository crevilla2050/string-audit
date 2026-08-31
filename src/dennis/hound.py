from pathlib import Path

from dennis.watsons import utf8


def sniff_file(path: Path) -> dict:
    """
    The Hound examines a file and reports what he can determine.

    The Hound name comes from the Sherlock Holmes story "The Hound of the Baskervilles".

    The Hound does not decide whether a file is admitted.
    That decision belongs to Mickey.
    """

    try:
        data = path.read_bytes()
    except Exception as exc:
        return {
            "valid": False,
            "kind": "unknown",
            "reason": "read_error",
            "error": str(exc),
        }

    result = utf8.inspect(data)

    if result["valid"]:
        return {
            "valid": True,
            "kind": "text",
            "encoding": result["encoding"],
            "watson": "utf8",
        }

    return {
        "valid": False,
        "kind": "unknown",
        "reason": result.get(
            "reason",
            "no_known_encoding",
        ),
    }
