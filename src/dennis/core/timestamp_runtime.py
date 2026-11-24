"""Runtime preparation for Dennis timestamp authorities.

This module resolves runtime credentials and prepares TLS file paths.
It performs no network communication, protocol parsing, timestamp
generation, or trust evaluation.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Outcomes
# ---------------------------------------------------------------------------

READY = "READY"
DISABLED = "DISABLED"
PREPARATION_ERROR = "PREPARATION_ERROR"


# ---------------------------------------------------------------------------
# Runtime data structures
# ---------------------------------------------------------------------------

class _ImmutableCredentials:
    """Base class for runtime credentials.

    Credential values are intentionally not dataclasses, so generic
    dataclass serialization cannot recursively extract their contents.
    """

    __slots__ = ()

    def __setattr__(self, name, value):
        raise AttributeError("Credentials are immutable")

    def __delattr__(self, name):
        raise AttributeError("Credentials are immutable")

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self


class BasicCredentials(_ImmutableCredentials):
    """Resolved HTTP Basic credentials."""

    __slots__ = ("_username", "_password")

    def __init__(self, username: str, password: str):
        object.__setattr__(self, "_username", username)
        object.__setattr__(self, "_password", password)

    @property
    def username(self) -> str:
        return self._username

    @property
    def password(self) -> str:
        return self._password

    def __repr__(self) -> str:
        return "BasicCredentials(<redacted>)"


class BearerCredentials(_ImmutableCredentials):
    """Resolved HTTP Bearer token."""

    __slots__ = ("_token",)

    def __init__(self, token: str):
        object.__setattr__(self, "_token", token)

    @property
    def token(self) -> str:
        return self._token

    def __repr__(self) -> str:
        return "BearerCredentials(<redacted>)"


@dataclass(frozen=True, slots=True)
class RuntimeTLSConfiguration:
    """Normalized TLS file paths ready for transport preparation."""

    ca_bundle: Optional[str]
    client_certificate: Optional[str]
    client_key: Optional[str]


@dataclass(frozen=True, slots=True)
class RuntimeTimestampAuthority:
    """Sanitized runtime representation of one timestamp authority."""

    id: str
    config_order: int
    protocol: str
    endpoint: str
    timeout_seconds: int | float
    authentication_type: str
    credentials: Optional[BasicCredentials | BearerCredentials]
    tls: RuntimeTLSConfiguration


@dataclass(frozen=True, slots=True)
class PreparationDiagnostic:
    """Safe, non-secret diagnostic information."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class AuthorityPreparationResult:
    """Preparation result for one configured authority."""

    id: str
    config_order: int
    outcome: str
    runtime_authority: Optional[RuntimeTimestampAuthority] = None
    diagnostics: tuple[PreparationDiagnostic, ...] = ()


# ---------------------------------------------------------------------------
# Internal preparation failure
# ---------------------------------------------------------------------------

class _PreparationFailure(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.diagnostic = PreparationDiagnostic(
            code=code,
            message=message,
        )


# ---------------------------------------------------------------------------
# Credential resolution
# ---------------------------------------------------------------------------

def _resolve_environment_variable(
    variable_name: str,
    authority_id: str,
    credential_label: str,
) -> str:
    value = os.environ.get(variable_name)

    if value is None:
        raise _PreparationFailure(
            "CREDENTIAL_ENV_MISSING",
            (
                f"Authority {authority_id!r}: environment variable "
                f"{variable_name!r} is not set "
                f"({credential_label})."
            ),
        )

    if not value:
        raise _PreparationFailure(
            "CREDENTIAL_EMPTY",
            (
                f"Authority {authority_id!r}: environment variable "
                f"{variable_name!r} is empty "
                f"({credential_label})."
            ),
        )

    return value


def _prepare_credentials(
    authority: dict,
    authority_id: str,
) -> tuple[str, Optional[BasicCredentials | BearerCredentials]]:
    authentication = authority["authentication"]
    authentication_type = authentication["type"]

    if authentication_type == "none":
        return authentication_type, None

    if authentication_type == "basic":
        username = _resolve_environment_variable(
            authentication["username_env"],
            authority_id,
            "username",
        )

        password = _resolve_environment_variable(
            authentication["password_env"],
            authority_id,
            "password",
        )

        return authentication_type, BasicCredentials(
            username=username,
            password=password,
        )

    if authentication_type == "bearer":
        token = _resolve_environment_variable(
            authentication["token_env"],
            authority_id,
            "bearer token",
        )

        return authentication_type, BearerCredentials(token=token)

    # The configuration validator should reject unsupported types.
    raise _PreparationFailure(
        "AUTHENTICATION_TYPE_UNSUPPORTED",
        (
            f"Authority {authority_id!r}: unsupported authentication "
            f"type {authentication_type!r}."
        ),
    )


# ---------------------------------------------------------------------------
# TLS path preparation
# ---------------------------------------------------------------------------

def _resolve_tls_file(
    configured_path: Optional[str],
    config_dir: Path,
    authority_id: str,
    role: str,
) -> Optional[str]:
    if configured_path is None:
        return None

    if role == "ca":
        missing_code = "TLS_CA_FILE_NOT_FOUND"
        unreadable_code = "TLS_CA_FILE_UNREADABLE"
        invalid_code = "TLS_CA_FILE_NOT_REGULAR"

        label = "CA bundle"

    elif role == "certificate":
        missing_code = "TLS_CERTIFICATE_FILE_NOT_FOUND"
        unreadable_code = "TLS_CERTIFICATE_FILE_UNREADABLE"
        invalid_code = "TLS_CERTIFICATE_FILE_NOT_REGULAR"

        label = "client certificate"

    elif role == "key":
        missing_code = "TLS_KEY_FILE_NOT_FOUND"
        unreadable_code = "TLS_KEY_FILE_UNREADABLE"
        invalid_code = "TLS_KEY_FILE_NOT_REGULAR"

        label = "client private key"

    else:
        raise ValueError(f"Unknown TLS file role: {role!r}")

    try:
        path = Path(configured_path).expanduser()

        if not path.is_absolute():
            path = config_dir / path

        resolved = path.resolve(strict=True)

    except FileNotFoundError:
        raise _PreparationFailure(
            missing_code,
            (
                f"Authority {authority_id!r}: configured {label} "
                f"does not exist."
            ),
        ) from None

    except (OSError, RuntimeError, ValueError):
        raise _PreparationFailure(
            unreadable_code,
            (
                f"Authority {authority_id!r}: configured {label} "
                f"could not be resolved."
            ),
        ) from None

    try:
        if not stat.S_ISREG(resolved.stat().st_mode):
            raise _PreparationFailure(
                invalid_code,
                (
                    f"Authority {authority_id!r}: configured {label} "
                    f"is not a regular file."
                ),
            )

        # Opening the file verifies that the current process can read it.
        # We deliberately do not read or retain its contents here.
        with resolved.open("rb"):
            pass

    except _PreparationFailure:
        raise

    except OSError:
        raise _PreparationFailure(
            unreadable_code,
            (
                f"Authority {authority_id!r}: configured {label} "
                f"is not readable."
            ),
        ) from None

    return str(resolved)


def _prepare_tls(
    authority: dict,
    authority_id: str,
    config_dir: Path,
) -> RuntimeTLSConfiguration:
    tls = authority["tls"]

    # Validate the pair before touching the filesystem.
    if (tls["client_certificate"] is None) != (
        tls["client_key"] is None
    ):
        raise _PreparationFailure(
            "TLS_CLIENT_CERTIFICATE_KEY_INCOMPLETE",
            (
                f"Authority {authority_id!r}: client certificate "
                f"and client key must be configured together."
            ),
        )

    ca_bundle = _resolve_tls_file(
        tls["ca_bundle"],
        config_dir,
        authority_id,
        "ca",
    )

    client_certificate = _resolve_tls_file(
        tls["client_certificate"],
        config_dir,
        authority_id,
        "certificate",
    )

    client_key = _resolve_tls_file(
        tls["client_key"],
        config_dir,
        authority_id,
        "key",
    )

    return RuntimeTLSConfiguration(
        ca_bundle=ca_bundle,
        client_certificate=client_certificate,
        client_key=client_key,
    )


# ---------------------------------------------------------------------------
# Individual authority preparation
# ---------------------------------------------------------------------------

def _prepare_one_authority(
    authority: dict,
    config_order: int,
    config_dir: Path,
) -> AuthorityPreparationResult:
    authority_id = authority["id"]

    if not authority["enabled"]:
        return AuthorityPreparationResult(
            id=authority_id,
            config_order=config_order,
            outcome=DISABLED,
        )

    try:
        authentication_type, credentials = _prepare_credentials(
            authority,
            authority_id,
        )

        tls = _prepare_tls(
            authority,
            authority_id,
            config_dir,
        )

        runtime_authority = RuntimeTimestampAuthority(
            id=authority_id,
            config_order=config_order,
            protocol=authority["protocol"],
            endpoint=authority["endpoint"],
            timeout_seconds=authority["timeout_seconds"],
            authentication_type=authentication_type,
            credentials=credentials,
            tls=tls,
        )

        return AuthorityPreparationResult(
            id=authority_id,
            config_order=config_order,
            outcome=READY,
            runtime_authority=runtime_authority,
        )

    except _PreparationFailure as exc:
        return AuthorityPreparationResult(
            id=authority_id,
            config_order=config_order,
            outcome=PREPARATION_ERROR,
            diagnostics=(exc.diagnostic,),
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def prepare_timestamp_authorities(
    authorities: list[dict],
    config_dir: Path,
) -> list[AuthorityPreparationResult]:
    """Prepare configured timestamp authorities for runtime use.

    Args:
        authorities:
            Validated authority configurations returned by
            validate_timestamp_authorities().

        config_dir:
            Directory containing ~/.dennis/config.json.
            Relative TLS paths are resolved against this directory.

    Returns:
        One ordered preparation result per configured authority.

    Raises:
        TypeError:
            If the supplied authorities or config_dir have invalid types.

        ValueError:
            If config_dir does not identify an existing directory.

    Individual authority preparation failures are returned as
    PREPARATION_ERROR results. They do not prevent other authorities
    from being prepared.
    """

    if not isinstance(authorities, list):
        raise TypeError("authorities must be a list")

    if not isinstance(config_dir, (str, Path)):
        raise TypeError("config_dir must be a string or Path")

    try:
        resolved_config_dir = Path(config_dir).expanduser().resolve(
            strict=True
        )
    except (OSError, RuntimeError, ValueError):
        raise ValueError(
            "config_dir must identify an existing directory"
        ) from None

    if not resolved_config_dir.is_dir():
        raise ValueError(
            "config_dir must identify an existing directory"
        )

    results = []

    for config_order, authority in enumerate(authorities):
        if not isinstance(authority, dict):
            raise TypeError(
                f"Authority at configuration position {config_order} "
                f"must be a dictionary"
            )

        results.append(
            _prepare_one_authority(
                authority=authority,
                config_order=config_order,
                config_dir=resolved_config_dir,
            )
        )

    return results