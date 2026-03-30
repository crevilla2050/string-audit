import re
from dennis.utils import load_dictionary


# --------------------------------------------------------
# Optional dictionary (future-ready, safe if missing)
# --------------------------------------------------------
CSS_WORDS = load_dictionary("css.dict")


# --------------------------------------------------------
# Human language shield (CRITICAL)
# --------------------------------------------------------
STOPWORDS = {
    "the", "and", "is", "of", "to", "for", "with",
    "your", "please", "this", "that", "you"
}


def looks_human_sentence(text: str) -> bool:
    words = text.split()

    if len(words) < 3:
        return False

    # contains stopwords → strong signal
    if any(w.lower() in STOPWORDS for w in words):
        return True

    # contains normal capitalization (sentence-like)
    if any(w[0].isupper() for w in words if w):
        return True

    return False


# --------------------------------------------------------
# CSS detection
# --------------------------------------------------------
def is_css(text: str) -> bool:
    if not text:
        return False

    t = text.strip()

    # ----------------------------------------
    # Dot-prefixed (.btn, .alert)
    # ----------------------------------------
    if t.startswith("."):
        return True

    tokens = t.lower().split()

    # ----------------------------------------
    # Dictionary match (if user provided css.dict)
    # ----------------------------------------
    if CSS_WORDS:
        if any(tok in CSS_WORDS for tok in tokens):
            return True

    # ----------------------------------------
    # Multiple CSS tokens (btn btn-primary)
    # ----------------------------------------
    if len(tokens) >= 2:
        if all(re.fullmatch(r"[a-z0-9\-]+", tok) for tok in tokens):
            return True

    # ----------------------------------------
    # Single token (col-md-6, mt-3)
    # ----------------------------------------
    if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)+", t):
        return True

    # ----------------------------------------
    # Common CSS prefixes
    # ----------------------------------------
    if any(t.startswith(prefix) for prefix in [
        "btn", "col", "row", "container",
        "alert", "card", "d-", "mt-", "mb-",
        "pt-", "pb-", "text-", "bg-"
    ]):
        return True

    return False


# --------------------------------------------------------
# Filter
# --------------------------------------------------------
def filter_css(mapping: dict) -> dict:
    cleaned = {}

    for k, v in mapping.items():

        if is_css(v):
            if looks_human_sentence(v):
                cleaned[k] = v  # keep
            else:
                continue  # drop
        else:
            cleaned[k] = v

    return cleaned