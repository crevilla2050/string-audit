def semantic_object(
    obj_type,
    value,
    file=None,
    line=None,
    metadata=None,
):
    return {
        "type": obj_type,
        "value": value,
        "location": {
            "file": file,
            "line": line,
        } if file else None,
        "metadata": metadata or {},
    }