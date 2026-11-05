"""
Dennis timestamp coordination.

This module handles timestamp evidence aggregation and canonical
timestamp selection. Network communication and protocol parsing
belong to separate modules.
"""

import re
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4


TIMESTAMP_EVIDENCE_SCHEMA = "dennis.timestamp-evidence.v1"

ACCEPTED_OUTCOMES = {
    "ACCEPTED",
}

VALID_OUTCOMES = {
    "ACCEPTED",
    "UNUSABLE",
    "UNREACHABLE",
    "TIMEOUT",
    "TLS_ERROR",
    "AUTH_ERROR",
    "HTTP_ERROR",
    "909_ERROR",
}

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

RFC3339_PATTERN = re.compile(
    r"^"
    r"(?P<date>\d{4}-\d{2}-\d{2})"
    r"T"
    r"(?P<time>\d{2}:\d{2}:\d{2})"
    r"(?P<fraction>\.\d+)?"
    r"(?P<timezone>Z|[+-]\d{2}:\d{2})"
    r"$"
)


def _parse_timestamp(value: str) -> tuple[datetime, Decimal]:
    """
    Parse a timezone-aware RFC 3339 timestamp.

    Returns:
        A UTC datetime for whole-second comparison and a Decimal
        containing the fractional second.

    Decimal preserves precision beyond Python datetime's
    microsecond resolution.
    """

    if not isinstance(value, str):
        raise ValueError("Timestamp must be a string")

    match = RFC3339_PATTERN.fullmatch(value)

    if not match:
        raise ValueError("Timestamp must be valid RFC 3339 with timezone")

    timezone_text = match.group("timezone")

    normalized = value.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(normalized)
        parsed_utc = parsed.astimezone(timezone.utc)

        fraction_text = match.group("fraction")

        fraction = (
            Decimal("0" + fraction_text)
            if fraction_text
            else Decimal("0")
        )

    except (ValueError, InvalidOperation) as exc:
        raise ValueError("Invalid timestamp") from exc

    return parsed_utc.replace(microsecond=0), fraction


def _timestamp_sort_key(value: str) -> tuple[datetime, Decimal]:
    return _parse_timestamp(value)


def _normalize_timestamp_utc(value: str) -> str:
    """
    Normalize an RFC 3339 timestamp to UTC while preserving
    its original fractional-second precision.
    """

    match = RFC3339_PATTERN.fullmatch(value)

    if not match:
        raise ValueError("Timestamp must be valid RFC 3339 with timezone")

    utc_datetime, _ = _parse_timestamp(value)

    fraction = match.group("fraction") or ""

    return (
        utc_datetime.strftime("%Y-%m-%dT%H:%M:%S")
        + fraction
        + "Z"
    )


def build_timestamp_report(
    plan_digest: str,
    plan_created_at: str,
    authority_results: list[dict],
    authority_config_snapshot: list[dict] | None = None,
) -> dict:
    """
    Build the common timestamp evidence report.

    Selects the latest accepted external timestamp.
    Falls back to the existing plan creation timestamp when
    no accepted external timestamp exists.

    Does not mutate the supplied authority results.
    """

    if not isinstance(plan_digest, str):
        raise ValueError("Plan digest must be a string")

    if not SHA256_PATTERN.fullmatch(plan_digest):
        raise ValueError("Plan digest must be a lowercase SHA-256 hex digest")

    if not isinstance(authority_results, list):
        raise ValueError("Authority results must be a list")

    # Validate the local timestamp even if an external timestamp
    # is available. It remains part of the plan metadata.
    _parse_timestamp(plan_created_at)

    authorities = deepcopy(authority_results)

    accepted = []

    for authority in authorities:

        if not isinstance(authority, dict):
            raise ValueError("Authority result must be an object")

        outcome = authority.get("outcome")

        if outcome not in VALID_OUTCOMES:
            raise ValueError(
                f"Unknown authority outcome: {outcome!r}"
            )

        if outcome != "ACCEPTED":
            continue

        parsed = authority.get("parsed")

        if not isinstance(parsed, dict):
            raise ValueError(
                "Accepted authority result must contain parsed data"
            )

        timestamp = parsed.get("timestamp_utc")

        if timestamp is None:
            timestamp = parsed.get("gen_time")

        if timestamp is None:
            timestamp = parsed.get("timestamp")

        if timestamp is None:
            raise ValueError(
                "Accepted authority result has no timestamp"
            )

        sort_key = _timestamp_sort_key(timestamp)

        configuration_order = authority.get("configuration_order")

        if (
            not isinstance(configuration_order, int)
            or isinstance(configuration_order, bool)
            or configuration_order < 0
        ):
            raise ValueError(
                "Accepted authority must have a valid configuration_order"
            )

        accepted.append(
            (
                sort_key,
                configuration_order,
                authority.get("authority_id"),
                timestamp,
                _normalize_timestamp_utc(timestamp),
            )
        )

    selected = None

    if accepted:
        # Latest timestamp wins.
        # For identical timestamps, lower configuration order wins.
        selected = max(
            accepted,
            key=lambda item: (item[0], -item[1]),
        )

    if selected:
        selected_authority_id = selected[2]
        selected_timestamp_original = selected[3]
        selected_timestamp = selected[4]
        fallback_used = False
        provenance = "EXTERNAL_TSA"
        fallback_timestamp = None

    else:
        selected_authority_id = None
        selected_timestamp_original = None
        selected_timestamp = None
        fallback_used = True
        provenance = "INTERNAL_CLOCK"
        fallback_timestamp = plan_created_at

    configuration_snapshot = deepcopy(
        authority_config_snapshot
        if authority_config_snapshot is not None
        else []
    )

    return {
        "schema": TIMESTAMP_EVIDENCE_SCHEMA,
        "run_id": str(uuid4()),

        "plan_digest": {
            "algorithm": "sha256",
            "value": plan_digest,
        },

        "configuration_snapshot": configuration_snapshot,

        "authorities": authorities,

        "selection": {
            "rule": "LATEST_ACCEPTED",
            "candidate_count": len(accepted),
            "selected_authority_id": selected_authority_id,
            "selected_timestamp": selected_timestamp,
            "selected_timestamp_original": selected_timestamp_original,
        },

        "fallback": {
            "used": fallback_used,
            "provenance": provenance,
            "timestamp": fallback_timestamp,
            "warning_required": fallback_used,
            "warning_code": (
                "EXTERNAL_TIMESTAMP_UNAVAILABLE"
                if fallback_used
                else None
            ),
        },

        "tsa_canonical_time": selected_timestamp,
        "timestamp_provenance": provenance,
    }