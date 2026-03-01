# core/sort.py

def sort_changes(changes):
    def key(c):
        return (
            c.get("file", ""),
            int(c.get("line", 0)),
            c.get("id", "")
        )
    return sorted(changes, key=key)