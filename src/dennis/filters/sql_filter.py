import re
from dennis.utils import load_dictionary


# --------------------------------------------------------
# Load dictionary (dynamic, core + user)
# --------------------------------------------------------
SQL_WORDS = load_dictionary("sql.dict")


# --------------------------------------------------------
# Keyword tiers (important for reducing false positives)
# --------------------------------------------------------
STRONG_WORDS = {
    "select", "insert", "update", "delete",
    "create", "drop", "alter"
}

STRUCTURAL_WORDS = {
    "from", "where", "join", "order", "group",
    "by", "limit", "values", "into", "set"
}


# --------------------------------------------------------
# Tokenizer (simple, deterministic)
# --------------------------------------------------------
def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z_]+", text.lower())


# --------------------------------------------------------
# Main detection
# --------------------------------------------------------
def is_sql(text: str) -> bool:

    if not text:
        return False

    tokens = tokenize(text)

    if not tokens:
        return False

    # --------------------------------------------------------
    # Dictionary-based counts
    # --------------------------------------------------------
    sql_tokens = [t for t in tokens if t in SQL_WORDS]

    strong_count = sum(1 for t in sql_tokens if t in STRONG_WORDS)
    structural_count = sum(1 for t in sql_tokens if t in STRUCTURAL_WORDS)
    total_count = len(sql_tokens)

    # --------------------------------------------------------
    # RULE 1: Strong + Structural
    # --------------------------------------------------------
    if strong_count >= 1 and structural_count >= 1:
        return True

    # --------------------------------------------------------
    # RULE 2: Multiple SQL tokens + SQL symbols
    # --------------------------------------------------------
    if total_count >= 2:
        if any(sym in text for sym in ["=", "?", "(", ")", "*", ","]):
            return True

    # --------------------------------------------------------
    # RULE 3: Strong keyword + SQL-like structure
    # --------------------------------------------------------
    if strong_count >= 1:
        if "(" in text and ")" in text:
            return True

    # --------------------------------------------------------
    # FALLBACK: legacy heuristics (keep your original safety net)
    # --------------------------------------------------------
    upper = text.upper()

    if any(x in upper for x in [
        "SELECT ",
        "INSERT INTO",
        "UPDATE ",
        "DELETE FROM",
        "CREATE TABLE",
        "ALTER TABLE",
        "DROP TABLE"
    ]):
        return True

    return False

def looks_like_sql_strict(text: str) -> bool:
    t = text.upper()

    # classic SQL patterns
    if any(x in t for x in [
        " = ?",
        "WHERE ",
        "ORDER BY",
        "GROUP BY",
        "INSERT INTO",
        "SELECT ",
        "UPDATE ",
        "DELETE FROM"
    ]):
        return True

    # multiple SQL keywords → strong signal
    count = sum(1 for w in ["SELECT", "FROM", "WHERE", "ORDER", "GROUP"] if w in t)
    if count >= 2:
        return True

    return False