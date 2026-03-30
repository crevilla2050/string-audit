import re
from dennis.utils import load_dictionary


# --------------------------------------------------------
# Optional dictionary (user extensible)
# --------------------------------------------------------
CODE_WORDS = load_dictionary("code.dict")


# --------------------------------------------------------
# Known technical tokens (core, stable across languages)
# --------------------------------------------------------
COMMON_CODE_WORDS = {
    "id", "uid", "uuid", "json", "xml", "html", "sql",
    "api", "url", "uri", "http", "https",
    "sha1", "sha256", "md5",
    "true", "false", "null",
    "int", "float", "string", "bool",
    "var", "let", "const",
    "function", "class", "return",
    "select", "insert", "update", "delete"
}

# --------------------------------------------------------
# CamelCase detector
# --------------------------------------------------------
CAMEL_CASE = re.compile(r"^[a-z]+[A-Za-z0-9]*$")


# --------------------------------------------------------
# Snake case detector
# --------------------------------------------------------
SNAKE_CASE = re.compile(r"^[a-z0-9_]+$")


# --------------------------------------------------------
# CONSTANT_CASE detector
# --------------------------------------------------------
CONSTANT_CASE = re.compile(r"^[A-Z0-9_]+$")


# --------------------------------------------------------
# Looks like code
# --------------------------------------------------------
def is_code(text: str) -> bool:
    if not text:
        return False

    t = text.strip()

    # ----------------------------------------
    # Dictionary match (user-defined)
    # ----------------------------------------
    if CODE_WORDS:
        if t.lower() in CODE_WORDS:
            return True

    # ----------------------------------------
    # Common known tokens
    # ----------------------------------------
    if t.lower() in COMMON_CODE_WORDS:
        return True

    # ----------------------------------------
    # CONSTANT_CASE (VERY strong signal)
    # ----------------------------------------
    if CONSTANT_CASE.fullmatch(t) and len(t) > 3:
        return True

    # ----------------------------------------
    # snake_case identifiers
    # ----------------------------------------
    if SNAKE_CASE.fullmatch(t) and "_" in t:
        return True

    # ----------------------------------------
    # camelCase identifiers
    # ----------------------------------------
    if CAMEL_CASE.fullmatch(t) and t[0].islower():
        return True

    # ----------------------------------------
    # function-like
    # ----------------------------------------
    if t.endswith("()"):
        return True

    # ----------------------------------------
    # looks like file / endpoint
    # ----------------------------------------
    if "/" in t and not " " in t:
        return True

    # ----------------------------------------
    # short technical tokens
    # ----------------------------------------
    if len(t) <= 4 and t.isalpha():
        return True

    return False


# --------------------------------------------------------
# Filter
# --------------------------------------------------------
def filter_code(mapping: dict) -> dict:
    cleaned = {}

    for k, v in mapping.items():
        if is_code(v):
            continue
        cleaned[k] = v

    return cleaned

def looks_like_code(text: str) -> bool:
    if not text:
        return False

    if any(x in text for x in [
        "<?php", "?>", "<?= ",
        "$", "->", "::",
        "function(", "return ",
        "{", "}", ";"
    ]):
        return True

    return False