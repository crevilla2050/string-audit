"""Online-first trust resolution with a local SQLite fallback.

Only public key identifiers and evidence timestamps are sent to a configured
Tessa endpoint. Payloads, DEX content, and private keys never leave Dennis.
"""
from __future__ import annotations

import base64
import json
import os
import sqlite3
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Callable

import rfc8785
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey


LOOKUP_PROTOCOL = "TESSA-TRUST-LOOKUP/1.0"


class TrustStatus(StrEnum):
    TRUSTED = "TRUSTED"
    UNTRUSTED = "UNTRUSTED"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID_RESPONSE = "INVALID_RESPONSE"


@dataclass(frozen=True)
class TrustConfig:
    mode: str
    servers: tuple[str, ...]
    timeout_seconds: float
    sqlite_fallback: bool
    db_path: Path
    ca_bundle: Path | None = None
    client_certificate: Path | None = None
    client_key: Path | None = None


@dataclass(frozen=True)
class TrustResolution:
    status: TrustStatus
    source: str
    key_id: str
    public_key: bytes | None = None
    authority_id: str | None = None
    observed_at: str | None = None
    expires_at: str | None = None
    freshness_confirmed: bool = False
    error: str | None = None


def load_trust_config(environ: dict[str, str] | None = None) -> TrustConfig:
    env = os.environ if environ is None else environ
    mode = env.get("DENNIS_TRUST_MODE", "online-first").strip().lower()
    if mode not in {"online-first", "offline-only"}:
        raise ValueError("DENNIS_TRUST_MODE must be online-first or offline-only.")
    raw_servers = env.get("DENNIS_TRUST_SERVERS", "")
    servers = tuple(item.strip().rstrip("/") for item in raw_servers.split(",") if item.strip())
    if any(not endpoint.startswith("https://") for endpoint in servers):
        raise ValueError("Trust servers must use HTTPS URLs.")
    try:
        timeout = float(env.get("DENNIS_TRUST_TIMEOUT_SECONDS", "5"))
    except ValueError as exc:
        raise ValueError("DENNIS_TRUST_TIMEOUT_SECONDS must be numeric.") from exc
    if timeout <= 0:
        raise ValueError("DENNIS_TRUST_TIMEOUT_SECONDS must be positive.")
    fallback = env.get("DENNIS_TRUST_SQLITE_FALLBACK", "true").strip().lower() in {"1", "true", "yes"}
    db_path = Path(env.get("DENNIS_TRUST_DB_PATH", "~/.dennis_keys.db")).expanduser()
    def optional_path(name: str) -> Path | None:
        raw = env.get(name, "").strip()
        return Path(raw).expanduser() if raw else None
    certificate = optional_path("DENNIS_TRUST_CLIENT_CERT")
    client_key = optional_path("DENNIS_TRUST_CLIENT_KEY")
    if (certificate is None) != (client_key is None):
        raise ValueError("Client certificate and key must be configured together.")
    return TrustConfig(mode, servers, timeout, fallback, db_path, optional_path("DENNIS_TRUST_CA_BUNDLE"), certificate, client_key)


def _local_key(db_path: Path, key_id: str) -> bytes | None:
    if not db_path.exists():
        return None
    with sqlite3.connect(db_path) as connection:
        row = connection.execute("SELECT public_key FROM trusted_keys WHERE key_id=?", (key_id,)).fetchone()
    if row is None or not row[0]:
        return None
    value = row[0]
    try:
        data = json.loads(value)
        value = data["public_key"]
    except (TypeError, ValueError, KeyError):
        pass
    try:
        return base64.b64decode(value)
    except Exception:
        return None


def _request(endpoint: str, payload: dict, timeout: float, config: TrustConfig | None = None) -> dict:
    request = urllib.request.Request(
        endpoint + "/api/v1/trust/keys/resolve",
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST",
    )
    context = ssl.create_default_context(cafile=str(config.ca_bundle) if config and config.ca_bundle else None)
    if config and config.client_certificate and config.client_key:
        context.load_cert_chain(str(config.client_certificate), str(config.client_key))
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ConnectionError("Trust service unavailable.") from exc


def _verify_response(response: dict, requested_key_id: str, local_key: Callable[[str], bytes | None]) -> TrustResolution:
    required = {"protocol", "key_id", "status", "public_key", "authority_id", "observed_at", "expires_at", "signature"}
    if not isinstance(response, dict) or set(response) != required or response.get("protocol") != LOOKUP_PROTOCOL:
        return TrustResolution(TrustStatus.INVALID_RESPONSE, "online", requested_key_id, error="Malformed trust response.")
    if response.get("key_id") != requested_key_id or response.get("status") not in {item.value for item in TrustStatus if item not in {TrustStatus.UNAVAILABLE, TrustStatus.INVALID_RESPONSE}}:
        return TrustResolution(TrustStatus.INVALID_RESPONSE, "online", requested_key_id, error="Invalid trust response status.")
    signature = response["signature"]
    if not isinstance(signature, dict) or set(signature) != {"algorithm", "key_id", "signature"} or signature.get("algorithm") != "Ed25519":
        return TrustResolution(TrustStatus.INVALID_RESPONSE, "online", requested_key_id, error="Unsigned trust response.")
    signer = local_key(signature["key_id"])
    if signer is None:
        return TrustResolution(TrustStatus.INVALID_RESPONSE, "online", requested_key_id, error="Unknown response signing key.")
    signed = {key: value for key, value in response.items() if key != "signature"}
    try:
        expiry = datetime.fromisoformat(response["expires_at"].replace("Z", "+00:00"))
        if expiry <= datetime.now(timezone.utc):
            return TrustResolution(TrustStatus.INVALID_RESPONSE, "online", requested_key_id, error="Expired trust response.")
        encoded = signature["signature"] + "=" * (-len(signature["signature"]) % 4)
        VerifyKey(signer).verify(rfc8785.dumps(signed), base64.urlsafe_b64decode(encoded))
        public_key = base64.b64decode(response["public_key"]) if response["public_key"] else None
    except (BadSignatureError, ValueError, TypeError, KeyError):
        return TrustResolution(TrustStatus.INVALID_RESPONSE, "online", requested_key_id, error="Trust response signature invalid.")
    return TrustResolution(TrustStatus(response["status"]), "online", requested_key_id, public_key, response["authority_id"], response["observed_at"], response["expires_at"], True)


def resolve_trust(key_id: str, *, evidence_timestamp: str | None = None, config: TrustConfig | None = None, fetch: Callable[[str, dict, float], dict] | None = None) -> TrustResolution:
    """Resolve current trust; only unavailability may fall back to SQLite."""
    configuration = config or load_trust_config()
    local = lambda identifier: _local_key(configuration.db_path, identifier)
    request = fetch or (lambda endpoint, payload, timeout: _request(endpoint, payload, timeout, configuration))
    if configuration.mode == "offline-only":
        key = local(key_id)
        return TrustResolution(TrustStatus.TRUSTED if key else TrustStatus.UNKNOWN, "sqlite", key_id, key, freshness_confirmed=False)
    responses: list[TrustResolution] = []
    unavailable = 0
    payload = {"protocol": LOOKUP_PROTOCOL, "key_id": key_id, "evidence_timestamp": evidence_timestamp}
    for endpoint in configuration.servers:
        try:
            result = _verify_response(request(endpoint, payload, configuration.timeout_seconds), key_id, local)
        except ConnectionError:
            unavailable += 1
            continue
        if result.status is TrustStatus.INVALID_RESPONSE:
            return result
        responses.append(result)
    if responses:
        statuses = {result.status for result in responses}
        if len(statuses) != 1:
            return TrustResolution(TrustStatus.INVALID_RESPONSE, "online", key_id, error="Conflicting authoritative trust responses.")
        return responses[0]
    if configuration.sqlite_fallback and (not configuration.servers or unavailable == len(configuration.servers)):
        key = local(key_id)
        return TrustResolution(TrustStatus.TRUSTED if key else TrustStatus.UNKNOWN, "sqlite-fallback", key_id, key, freshness_confirmed=False)
    return TrustResolution(TrustStatus.UNAVAILABLE, "online", key_id, error="No trust service was reachable.")
