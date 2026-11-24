
"""TLS transport preparation for Dennis timestamp authorities.

This module constructs independently configured TLS contexts.
It performs no network communication, protocol parsing,
timestamp generation, or trust evaluation of timestamp responses.
"""

from __future__ import annotations

import ssl
from dataclasses import dataclass

from dennis.core.timestamp_runtime import (
    READY,
    DISABLED,
    PREPARATION_ERROR,
    AuthorityPreparationResult,
    PreparationDiagnostic,
    RuntimeTimestampAuthority,
)


TRANSPORT_PREPARATION_ERROR = "TRANSPORT_PREPARATION_ERROR"


@dataclass(frozen=True, slots=True)
class AuthorityTransport:
    """Prepared transport resources for one timestamp authority."""

    runtime_authority: RuntimeTimestampAuthority
    tls_context: ssl.SSLContext


@dataclass(frozen=True, slots=True)
class AuthorityTransportPreparationResult:
    """Transport preparation outcome for one authority."""

    id: str
    config_order: int
    outcome: str
    transport: AuthorityTransport | None = None
    diagnostics: tuple[PreparationDiagnostic, ...] = ()


def _build_tls_context(
    authority: RuntimeTimestampAuthority,
) -> ssl.SSLContext:
    """Construct and configure an SSL context for one authority."""

    tls = authority.tls

    try:
        context = ssl.create_default_context(
            purpose=ssl.Purpose.SERVER_AUTH,
            cafile=tls.ca_bundle,
        )
    except (ssl.SSLError, OSError, ValueError):
        raise _TransportFailure(
            "TLS_CA_BUNDLE_INVALID",
            "The configured CA bundle could not be loaded.",
        ) from None

    # Make the intended server-authentication policy explicit.
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True

    if tls.client_certificate is not None:
        try:
            context.load_cert_chain(
                certfile=tls.client_certificate,
                keyfile=tls.client_key,
            )
        except (ssl.SSLError, OSError, ValueError):
            raise _TransportFailure(
                "TLS_CLIENT_CERTIFICATE_KEY_INVALID",
                (
                    "The client certificate and private key could not "
                    "be loaded together. Check their formats, validity, "
                    "and whether the private key matches the certificate."
                ),
            ) from None

    return context


class _TransportFailure(Exception):
    """Internal, safe transport preparation failure."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.diagnostic = PreparationDiagnostic(
            code=code,
            message=message,
        )


def prepare_timestamp_transports(
    preparation_results: list[AuthorityPreparationResult],
) -> list[AuthorityTransportPreparationResult]:
    """Construct TLS transport resources for prepared authorities.

    Disabled and failed runtime preparations are propagated without
    attempting TLS context construction.

    Each READY authority is handled independently. A failure for one
    authority does not prevent subsequent authorities from being prepared.
    """

    if not isinstance(preparation_results, list):
        raise TypeError("preparation_results must be a list")

    results = []

    for preparation in preparation_results:
        if not isinstance(preparation, AuthorityPreparationResult):
            raise TypeError(
                "Each item must be an AuthorityPreparationResult"
            )

        if preparation.outcome == DISABLED:
            results.append(
                AuthorityTransportPreparationResult(
                    id=preparation.id,
                    config_order=preparation.config_order,
                    outcome=DISABLED,
                )
            )
            continue

        if preparation.outcome == PREPARATION_ERROR:
            results.append(
                AuthorityTransportPreparationResult(
                    id=preparation.id,
                    config_order=preparation.config_order,
                    outcome=PREPARATION_ERROR,
                    diagnostics=preparation.diagnostics,
                )
            )
            continue

        if preparation.outcome != READY:
            raise ValueError(
                f"Unsupported runtime preparation outcome: "
                f"{preparation.outcome!r}"
            )

        if preparation.runtime_authority is None:
            raise ValueError(
                "READY preparation result has no runtime authority"
            )

        try:
            context = _build_tls_context(
                preparation.runtime_authority
            )

            transport = AuthorityTransport(
                runtime_authority=preparation.runtime_authority,
                tls_context=context,
            )

            results.append(
                AuthorityTransportPreparationResult(
                    id=preparation.id,
                    config_order=preparation.config_order,
                    outcome=READY,
                    transport=transport,
                )
            )

        except _TransportFailure as exc:
            results.append(
                AuthorityTransportPreparationResult(
                    id=preparation.id,
                    config_order=preparation.config_order,
                    outcome=TRANSPORT_PREPARATION_ERROR,
                    diagnostics=(exc.diagnostic,),
                )
            )

    return results
