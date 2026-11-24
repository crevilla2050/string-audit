"""Portable Trust Evidence 1.0 support for finalized DEX artifacts.

The DEX payload identity deliberately excludes timestamp evidence.  This
module verifies the separately signed, portable authority statement that is
embedded by the finalization workflow.
"""

from __future__ import annotations

import base64
import hashlib
import gzip
import io
import json
import os
import re
import tarfile
import tempfile
import urllib.request
import urllib.parse
import urllib.error
from dataclasses import dataclass
from typing import Any, Callable

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
import rfc8785


ATTACHMENT_PATH = "evidence/ilpresim-trust-evidence-1.0.json"
PROFILE = "dennis-dex-trust-evidence-1.0"
DOCUMENT_TYPE = "ILP-TRUST-EVIDENCE"
DOCUMENT_VERSION = "1.0"
CANONICALIZATION = "JCS-RFC8785"
FINALIZATION_PROFILE = "dennis-dex-finalization-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TIMESTAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{9}Z$")


class TrustEvidenceError(ValueError):
    """Raised when a portable trust evidence attachment is invalid."""


def finalization_projection(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return the versioned commitment signed for a finalized DEX.

    This is deliberately distinct from the legacy DEX semantic subset: adding
    trust evidence never changes the canonical payload identity or lineage.
    """
    descriptor = manifest.get("trust_evidence")
    if not isinstance(descriptor, dict):
        raise TrustEvidenceError("Finalization requires a trust evidence descriptor.")
    payload = manifest.get("payload", {})
    payload_hash = payload.get("hash", {})
    return {
        "profile": FINALIZATION_PROFILE,
        "payload_hash_algorithm": payload_hash.get("algorithm"),
        "payload_hash_value": payload_hash.get("value"),
        "payload_type": payload.get("type"),
        "lineage": manifest.get("lineage", {}),
        "trust_evidence": descriptor,
    }


def canonicalize_finalization(manifest: dict[str, Any]) -> bytes:
    try:
        return rfc8785.dumps(finalization_projection(manifest))
    except (TypeError, ValueError, OverflowError) as exc:
        raise TrustEvidenceError("Finalization commitment cannot be canonicalized.") from exc


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TrustEvidenceError(f"Duplicate JSON member: {key}")
        result[key] = value
    return result


def load_document(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrustEvidenceError("Evidence attachment is not valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise TrustEvidenceError("Evidence attachment must be a JSON object.")
    return value


def canonicalize_evidence(evidence: dict[str, Any]) -> bytes:
    """Return RFC 8785/JCS canonical UTF-8 bytes for an evidence object."""
    try:
        return rfc8785.dumps(evidence)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TrustEvidenceError("Evidence cannot be canonicalized.") from exc


def _required_exact(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise TrustEvidenceError(f"Invalid {label} members.")


def validate_document(document: dict[str, Any], payload_hash: str) -> dict[str, Any]:
    _required_exact(document, {"document_version", "document_type", "evidence", "signature", "verification"}, "document")
    if document["document_version"] != DOCUMENT_VERSION or document["document_type"] != DOCUMENT_TYPE:
        raise TrustEvidenceError("Unsupported trust evidence document version.")

    evidence = document["evidence"]
    signature = document["signature"]
    verification = document["verification"]
    if not all(isinstance(value, dict) for value in (evidence, signature, verification)):
        raise TrustEvidenceError("Trust evidence sections must be objects.")
    _required_exact(evidence, {"evidence_version", "canonicalization", "evidence_id", "authority_id", "protocol", "request_id", "payload_hash", "timestamp", "clock_health"}, "evidence")
    _required_exact(signature, {"signature_version", "algorithm", "key_id", "signature"}, "signature")
    _required_exact(verification, {"schema_valid", "signature_valid", "key_trusted", "registry_status"}, "verification")
    if evidence["evidence_version"] != "1.0" or evidence["canonicalization"] != CANONICALIZATION:
        raise TrustEvidenceError("Unsupported evidence version or canonicalization.")
    if not all(isinstance(evidence[key], str) and evidence[key] for key in ("evidence_id", "authority_id", "protocol", "request_id")):
        raise TrustEvidenceError("Evidence identifiers must be non-empty strings.")
    payload = evidence["payload_hash"]
    if not isinstance(payload, dict) or set(payload) != {"algorithm", "value"}:
        raise TrustEvidenceError("Invalid evidence payload hash.")
    if payload.get("algorithm") != "SHA-256" or payload.get("value") != payload_hash or not _SHA256.fullmatch(payload_hash):
        raise TrustEvidenceError("Evidence does not bind this DEX payload identity.")
    if not isinstance(evidence["timestamp"], str) or not _TIMESTAMP.fullmatch(evidence["timestamp"]):
        raise TrustEvidenceError("Evidence timestamp is not UTC nanosecond RFC 3339.")
    clock = evidence["clock_health"]
    clock_fields = {"status", "reason", "synchronized", "stratum", "reference_id", "system_offset_seconds", "root_delay_seconds", "root_dispersion_seconds", "estimated_error_seconds", "leap_status"}
    if not isinstance(clock, dict) or set(clock) != clock_fields or clock.get("status") != "HEALTHY" or clock.get("synchronized") is not True:
        raise TrustEvidenceError("Evidence does not contain a healthy clock assessment.")
    if signature.get("signature_version") != "1.0" or signature.get("algorithm") != "Ed25519":
        raise TrustEvidenceError("Unsupported evidence signature.")
    if not isinstance(signature.get("key_id"), str) or not signature["key_id"]:
        raise TrustEvidenceError("Invalid evidence signing key identifier.")
    if not isinstance(signature.get("signature"), str):
        raise TrustEvidenceError("Invalid evidence signature encoding.")
    try:
        raw_signature = base64.urlsafe_b64decode(signature["signature"] + "=" * (-len(signature["signature"]) % 4))
    except Exception as exc:
        raise TrustEvidenceError("Invalid evidence signature encoding.") from exc
    if len(raw_signature) != 64:
        raise TrustEvidenceError("Invalid Ed25519 signature length.")
    return evidence


@dataclass(frozen=True)
class TrustEvidenceResult:
    present: bool
    valid: bool
    signature_valid: bool | None
    key_trusted: bool | None
    evidence_id: str | None = None
    key_id: str | None = None
    error: str | None = None


def verify_attachment(
    manifest: dict[str, Any], files: dict[str, bytes], key_resolver: Callable[[str], bytes | None] | None = None,
) -> TrustEvidenceResult:
    descriptor = manifest.get("trust_evidence")
    if descriptor is None:
        return TrustEvidenceResult(False, True, None, None)
    try:
        expected = {"profile", "path", "document_type", "document_version", "sha256", "evidence_id"}
        if not isinstance(descriptor, dict) or set(descriptor) != expected:
            raise TrustEvidenceError("Invalid trust evidence descriptor.")
        if descriptor["profile"] != PROFILE or descriptor["path"] != ATTACHMENT_PATH or descriptor["document_type"] != DOCUMENT_TYPE or descriptor["document_version"] != DOCUMENT_VERSION:
            raise TrustEvidenceError("Unsupported trust evidence descriptor.")
        data = files.get(ATTACHMENT_PATH)
        if data is None or hashlib.sha256(data).hexdigest() != descriptor["sha256"]:
            raise TrustEvidenceError("Trust evidence attachment hash mismatch.")
        payload_hash = manifest.get("payload", {}).get("hash", {}).get("value", "")
        document = load_document(data)
        evidence = validate_document(document, payload_hash)
        if evidence["evidence_id"] != descriptor["evidence_id"]:
            raise TrustEvidenceError("Evidence identifier mismatch.")
        key_id = document["signature"]["key_id"]
        if key_resolver is None:
            return TrustEvidenceResult(True, True, None, None, evidence["evidence_id"], key_id)
        public_key = key_resolver(key_id)
        if public_key is None:
            return TrustEvidenceResult(True, True, None, False, evidence["evidence_id"], key_id)
        try:
            VerifyKey(public_key).verify(canonicalize_evidence(evidence), base64.urlsafe_b64decode(document["signature"]["signature"] + "=" * (-len(document["signature"]["signature"]) % 4)))
        except (BadSignatureError, ValueError, TypeError):
            return TrustEvidenceResult(True, False, False, True, evidence["evidence_id"], key_id, "Evidence signature is invalid.")
        return TrustEvidenceResult(True, True, True, True, evidence["evidence_id"], key_id)
    except TrustEvidenceError as exc:
        return TrustEvidenceResult(True, False, False, None, error=str(exc))


def attach_document(dex_path: str, document_bytes: bytes) -> TrustEvidenceResult:
    """Atomically embed a verified Portable Trust Evidence 1.0 document.

    This deliberately does not change the DEX payload, its payload hash, or
    lineage.  Callers may only replace the on-disk artifact after the document
    verifies against the original manifest.
    """
    from pathlib import Path

    artifact = Path(dex_path)
    with gzip.open(artifact, "rb") as gz:
        tar_bytes = gz.read()
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r") as tar:
        for member in tar.getmembers():
            stream = tar.extractfile(member)
            if stream is not None:
                files[member.name] = stream.read()
    if "manifest.json" not in files:
        raise TrustEvidenceError("DEX missing manifest.json.")
    manifest = json.loads(files["manifest.json"])
    if manifest.get("trust_evidence") is not None:
        raise TrustEvidenceError("DEX already contains trust evidence.")
    document = load_document(document_bytes)
    payload_hash = manifest.get("payload", {}).get("hash", {}).get("value", "")
    evidence = validate_document(document, payload_hash)
    descriptor = {
        "profile": PROFILE,
        "path": ATTACHMENT_PATH,
        "document_type": DOCUMENT_TYPE,
        "document_version": DOCUMENT_VERSION,
        "sha256": hashlib.sha256(document_bytes).hexdigest(),
        "evidence_id": evidence["evidence_id"],
    }
    manifest["trust_evidence"] = descriptor
    files[ATTACHMENT_PATH] = document_bytes
    files["manifest.json"] = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    outcome = verify_attachment(manifest, files)
    if not outcome.valid:
        raise TrustEvidenceError(outcome.error or "Trust evidence validation failed.")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for name in sorted(files):
            data = files[name]
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = 0
            info.uid = info.gid = 0
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    fd, temporary = tempfile.mkstemp(prefix=f".{artifact.name}.", suffix=".tmp", dir=artifact.parent)
    try:
        with os.fdopen(fd, "wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as gz:
                gz.write(buffer.getvalue())
        os.replace(temporary, artifact)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return outcome


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def safe_issuance_endpoint(endpoint: str) -> str:
    parsed = urllib.parse.urlsplit(endpoint)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment):
        raise TrustEvidenceError("Evidence endpoint must be a credential-free HTTPS URL.")
    return endpoint


def issue_and_attach(dex_path: str, endpoint: str, bearer_token: str, request_id: str, opener=None) -> TrustEvidenceResult:
    """Request portable evidence then atomically attach it to the unchanged DEX.

    Attachment happens only after a complete successful response; a transport or
    validation failure leaves the original artifact byte-for-byte untouched.
    """
    endpoint = safe_issuance_endpoint(endpoint)
    if not isinstance(bearer_token, str) or not bearer_token:
        raise TrustEvidenceError("Bearer credential is required.")
    artifact = Path(dex_path)
    with gzip.open(artifact, "rb") as gz:
        with tarfile.open(fileobj=io.BytesIO(gz.read()), mode="r") as archive:
            manifest = json.loads(archive.extractfile("manifest.json").read())
    payload_hash = manifest.get("payload", {}).get("hash", {}).get("value", "")
    request = urllib.request.Request(endpoint, data=json.dumps({"protocol":"HTSA-HTTP/2.0","request_id":request_id,"payload_hash":{"algorithm":"SHA-256","value":payload_hash}}, separators=(",",":")).encode(), headers={"Content-Type":"application/json","Authorization":f"Bearer {bearer_token}"}, method="POST")
    opener = opener or urllib.request.build_opener(_NoRedirect()).open
    try:
        with opener(request, timeout=10) as response: document = response.read()
    except Exception as exc: raise TrustEvidenceError("Evidence issuance failed; artifact was not modified.") from exc
    return attach_document(str(artifact), document)
