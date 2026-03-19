import re

SQL_KEYWORDS = [
    "SELECT", "INSERT", "UPDATE", "DELETE",
    "FROM", "WHERE", "JOIN", "VALUES",
    "ORDER BY", "GROUP BY", "LIMIT", "HAVING",
    "CREATE", "ALTER", "DROP", "TABLE",
    "DATABASE", "VIEW", "PROCEDURE", "FUNCTION",
    "TRIGGER", "INDEX", "UNION", "ALL", "DISTINCT"
]

SQL_KEYWORD_PATTERN = re.compile(
    r"\b(" + "|".join(SQL_KEYWORDS) + r")\b",
    re.IGNORECASE
)


def is_sql(text: str) -> bool:

    if not text:
        return False
    
    upper = text.upper()

    # --------------------------------------------------------
    # LEVEL 1 — HARD MATCHES (no false positives)
    # --------------------------------------------------------
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

    # --------------------------------------------------------
    # LEVEL 2 — STRONG KEYWORD COMBINATIONS
    # (this is where your keyword list shines)
    # --------------------------------------------------------
    keyword_hits = [
        k for k in SQL_KEYWORDS
        if re.search(rf"\b{k}\b", upper)
    ]

    if len(keyword_hits) >= 2:
        return True

    # --------------------------------------------------------
    # LEVEL 3 — KEYWORD + STRUCTURE
    # --------------------------------------------------------
    if keyword_hits:
        if "(" in text and ")" in text:
            return True

        if "?" in text or ":" in text:
            return True

        if " = " in text:
            return True
        
        if ";" in text:
            return True

    return False