import re
from dennis.classifiers.sql import is_sql
from dennis.classifiers.url import is_url

def contains_dict_words(text: str, words: set[str]) -> int:
    upper = text.upper()

    matches = 0

    for w in words:
        if w in upper:
            matches += 1

    return matches


def looks_css(text: str) -> bool:
    if not text:
        return False

    t = text.strip().lower()

    if t.startswith("."):
        return True

    if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)+", t):
        return True

    if " " in t:
        parts = t.split()
        if all(re.fullmatch(r"[a-z0-9\-]+", p) for p in parts):
            return True

    if any(t.startswith(p) for p in [
        "btn", "col", "row", "container",
        "d-", "mt-", "mb-", "pt-", "pb-",
        "display", "flex", "block", "inline",
        "padding", "margin", "color", "background",
        "font", "border", "width", "height",
        "align-items", "justify-content", "gap", "font", "div", "div style", "class", "style",
        "flex:", "background-color", "align-items", "justify-content", "div class", "span class",
        "div id", "span id", "text-align", "display:", "position:", "top:", "left:", "right:", "bottom:",
        "overflow:", "z-index:", "float:", "clear:", "cursor:", "visibility:", "opacity:"
    ]):
        return True

    return False


def looks_code(text: str) -> bool:
    if not text:
        return False

    if text.isidentifier():
        return True

    if re.fullmatch(r"[A-Z0-9_]+", text) and len(text) > 4:
        return True

    if re.fullmatch(r"[a-z0-9_]+", text) and "_" in text:
        return True

    if text.endswith("()"):
        return True

    return False


def compute_score(text: str, dict_words: set[str]) -> int:
    score = 0

    dict_hits = contains_dict_words(text, dict_words)

    # ----------------------------------------
    # HARD RULE (your new idea)
    # ----------------------------------------
    if dict_hits >= 2:
        return 999  # immediate drop

    if dict_hits == 1:
        score += 2

    if is_sql(text):
        score += 3

    if is_url(text):
        score += 3

    if looks_css(text):
        score += 2

    if looks_code(text):
        score += 2

    if " " not in text:
        score += 1

    if len(text) > 80:
        score += 2

    if sum(1 for c in text if not c.isalnum() and c not in " .,!?") > 5:
        score += 2

    if text.upper() == text and len(text) > 10:
        score += 2

    return score


def is_human_text(text: str) -> bool:
    if not text:
        return False

    # must contain letters
    if not any(c.isalpha() for c in text):
        return False

    # must have natural spacing or mixed casing
    if " " not in text and not any(c.islower() for c in text):
        return False

    return True
    

def clean_mapping(mapping: dict, dict_words: set[str]) -> dict:
    cleaned = {}

    for k, v in mapping.items():

        score = compute_score(v, dict_words)

        if score >= 3:
            continue

        if not is_human_text(v):
            continue

        cleaned[k] = v

    return cleaned