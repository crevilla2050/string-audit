# src/string_audit/filters/pipeline.py

from .sql_filter import filter_sql
from .css_filter import filter_css
from .url_filter import filter_url
from .code_filter import filter_code


def apply_filters(mapping: dict, filters: list[str]) -> dict:

    # normalize + sort (important for deterministic naming)
    filters = sorted(set(f.lower() for f in filters))

    if "sql" in filters:
        mapping = filter_sql(mapping)

    if "css" in filters:
        mapping = filter_css(mapping)

    if "url" in filters:
        mapping = filter_url(mapping)

    if "code" in filters:
        mapping = filter_code(mapping)

    return mapping, filters # pyright: ignore[reportReturnType]