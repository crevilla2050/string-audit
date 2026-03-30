import json


def serialize_bundle(bundle: dict) -> bytes:
    return json.dumps(
        bundle,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")