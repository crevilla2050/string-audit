
"""
Dennis timestamp authority configuration validation.

This module validates timestamp authority configuration without
performing network operations or resolving credentials.
"""

from copy import deepcopy
from urllib.parse import urlparse
import math


class TimestampConfigurationError(ValueError):
    """Raised when timestamp authority configuration is invalid."""


SUPPORTED_PROTOCOLS = {
    "rfc3161",
    "http-json",
}

SUPPORTED_AUTHENTICATION = {
    "none",
    "basic",
    "bearer",
}

REQUIRED_AUTHORITY_FIELDS = {
    "id",
    "enabled",
    "protocol",
    "endpoint",
    "timeout_seconds",
    "authentication",
    "tls",
}

REQUIRED_TLS_FIELDS = {
    "ca_bundle",
    "client_certificate",
    "client_key",
}


def _validate_endpoint(endpoint: object, authority_id: str) -> None:
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise TimestampConfigurationError(
            f"Authority {authority_id!r}: endpoint must be a nonempty URL"
        )

    parsed = urlparse(endpoint)

    if (
        parsed.scheme.lower() != "https"
        or not parsed.netloc
        or parsed.hostname is None
    ):
        raise TimestampConfigurationError(
            f"Authority {authority_id!r}: endpoint must be an absolute HTTPS URL"
        )

    if parsed.username is not None or parsed.password is not None:
        raise TimestampConfigurationError(
            f"Authority {authority_id!r}: credentials must not be embedded in the endpoint URL"
        )

    try:
        parsed.port
    except ValueError as exc:
        raise TimestampConfigurationError(
            f"Authority {authority_id!r}: endpoint contains an invalid port"
        ) from exc


def _validate_timeout(timeout: object, authority_id: str) -> None:
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or timeout <= 0
        or math.isnan(timeout)
        or math.isinf(timeout)
    ):
        raise TimestampConfigurationError(
            f"Authority {authority_id!r}: timeout_seconds must be a positive number"
        )


def _validate_authentication(
    authentication: object,
    authority_id: str,
) -> None:
    if not isinstance(authentication, dict):
        raise TimestampConfigurationError(
            f"Authority {authority_id!r}: authentication must be an object"
        )

    auth_type = authentication.get("type")

    if auth_type not in SUPPORTED_AUTHENTICATION:
        raise TimestampConfigurationError(
            f"Authority {authority_id!r}: unsupported authentication type {auth_type!r}"
        )

    if auth_type == "none":
        return

    if auth_type == "basic":
        required = ("username_env", "password_env")
    else:
        required = ("token_env",)

    for field in required:
        value = authentication.get(field)

        if not isinstance(value, str) or not value.strip():
            raise TimestampConfigurationError(
                f"Authority {authority_id!r}: authentication requires a nonempty {field}"
            )


def _validate_tls(tls: object, authority_id: str) -> None:
    if not isinstance(tls, dict):
        raise TimestampConfigurationError(
            f"Authority {authority_id!r}: tls must be an object"
        )

    missing = REQUIRED_TLS_FIELDS - tls.keys()

    if missing:
        raise TimestampConfigurationError(
            f"Authority {authority_id!r}: missing TLS fields: "
            + ", ".join(sorted(missing))
        )

    for field in REQUIRED_TLS_FIELDS:
        value = tls[field]

        if value is not None and (
            not isinstance(value, str) or not value.strip()
        ):
            raise TimestampConfigurationError(
                f"Authority {authority_id!r}: TLS field {field!r} "
                "must be a nonempty path or null"
            )

    certificate = tls["client_certificate"]
    private_key = tls["client_key"]

    if (certificate is None) != (private_key is None):
        raise TimestampConfigurationError(
            f"Authority {authority_id!r}: client_certificate and "
            "client_key must be configured together"
        )


def _validate_authority(authority: object) -> None:
    if not isinstance(authority, dict):
        raise TimestampConfigurationError(
            "Each timestamp authority must be an object"
        )

    missing = REQUIRED_AUTHORITY_FIELDS - authority.keys()

    if missing:
        raise TimestampConfigurationError(
            "Timestamp authority is missing required fields: "
            + ", ".join(sorted(missing))
        )

    authority_id = authority["id"]

    if not isinstance(authority_id, str) or not authority_id.strip():
        raise TimestampConfigurationError(
            "Timestamp authority id must be a nonempty string"
        )

    if not isinstance(authority["enabled"], bool):
        raise TimestampConfigurationError(
            f"Authority {authority_id!r}: enabled must be a boolean"
        )

    protocol = authority["protocol"]

    if protocol not in SUPPORTED_PROTOCOLS:
        raise TimestampConfigurationError(
            f"Authority {authority_id!r}: unsupported protocol {protocol!r}"
        )

    _validate_endpoint(authority["endpoint"], authority_id)
    _validate_timeout(authority["timeout_seconds"], authority_id)
    _validate_authentication(authority["authentication"], authority_id)
    _validate_tls(authority["tls"], authority_id)


def validate_timestamp_authorities(config: dict) -> list[dict]:
    """
    Validate and return configured timestamp authorities.

    The returned configuration is a deep copy preserving the
    original authority order and values.

    This function performs no network access and does not resolve
    environment variables or credentials.
    """

    if not isinstance(config, dict):
        raise TimestampConfigurationError(
            "Dennis configuration must be an object"
        )

    authorities = config.get("timestamp_authorities", [])

    if not isinstance(authorities, list):
        raise TimestampConfigurationError(
            "timestamp_authorities must be a list"
        )

    result = deepcopy(authorities)
    seen_ids = set()

    for authority in result:
        _validate_authority(authority)

        authority_id = authority["id"]

        if authority_id in seen_ids:
            raise TimestampConfigurationError(
                f"Duplicate timestamp authority id: {authority_id!r}"
            )

        seen_ids.add(authority_id)

    return result
