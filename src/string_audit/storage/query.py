# storage/query.py

def normalize_sql(sql: str, flavor: str) -> str:
    """
    Convert SQLite-style placeholders to the target backend.
    """
    if flavor == "mysql":
        return sql.replace("?", "%s")
    return sql