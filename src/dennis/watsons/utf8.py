def inspect(data: bytes) -> dict:
    """
    UTF-8 Watson.

    Determines whether the supplied bytes are valid UTF-8.
    """

    try:
        data.decode("utf-8")

        return {
            "valid": True,
            "encoding": "utf-8",
        }

    except UnicodeDecodeError:
        return {
            "valid": False,
            "encoding": "utf-8",
            "reason": "invalid_encoding",
        }

def decode(data: bytes) -> str:
    """
    Decode bytes as UTF-8.

    Invalid UTF-8 is an error. We deliberately do not use
    error-ignoring or replacement behavior because Dennis
    must preserve the source document exactly.
    """

    return data.decode("utf-8")