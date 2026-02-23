# core/rehydrate.py
from datetime import datetime
from .sort import sort_changes

def rehydrate_from_csv(changes):
    return {
        "meta": {
            "tool": "dennis",
            "version": "0.1",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source_plan": "rehydrated-from-csv"
        },
        "changes": sort_changes(changes)
    }