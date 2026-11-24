# Dennis 0.9.4 — Timestamp Contract

**Status:** Proposed for approval and freeze  
**Scope:** Dennis CLI, DEX artifacts and XDEX encryption lifecycle  
**Target release:** 0.9.4  
**Future extension:** 0.9.6 plugin infrastructure

---

## 1. Purpose

This contract defines how Dennis generates, records, preserves and handles timestamps throughout the artifact lifecycle.

The objectives are:

- Maintain complete timestamp provenance.
- Preserve atomicity and artifact self-containment.
- Support offline-first operation.
- Allow optional external timestamp authorities.
- Preserve reproducibility and deterministic artifact identity.
- Provide future extensibility through plugins without expanding the 0.9.4 implementation scope.

## 2. Fundamental principles

The following principles are normative:

1. Timestamps are informational metadata, not cryptographic identity.
2. Timestamp changes alone must never change an artifact's canonical identity.
3. Dennis must retain all relevant timestamp information inside the DEX.
4. External timestamp authorities are optional.
5. The local system clock is the universal fallback.
6. Dennis Core does not independently verify TSA cryptographic signatures in 0.9.4.
7. Timestamp authority responses must never be silently discarded.
8. Timestamp handling must not compromise offline operation.

## 3. Timestamp definitions

Dennis maintains two distinct timestamp concepts.

### 3.1 Plan creation timestamp

`plan_created_at`

- Generated when the user executes `dennis plan`.
- Obtained from the local system clock.
- Represented in UTC.
- Supports nanosecond precision.
- Records the highest precision actually available from the source clock.
- Remains unchanged throughout the artifact lifecycle.

This timestamp describes the local system's reported plan creation time.

It is informational and does not constitute independently verified time.

### 3.2 Canonical external timestamp

`tsa_canonical_time`

When one or more configured timestamp authorities return accepted timestamp responses, Dennis selects the most recent reported timestamp.

Rules:

- The selected value is the most recent accepted TSA timestamp.
- All other responses remain preserved.
- The selected authority is explicitly identified.
- Differences of milliseconds or smaller are respected, subject to the precision reported by the authority.
- This timestamp never replaces `plan_created_at`.

If no external timestamp response is accepted, the local clock remains the fallback.

## 4. Timestamp representation and precision

All Dennis lifecycle timestamps use UTC.

The representation must support nanosecond precision.

Dennis must:

- Preserve available precision.
- Never fabricate precision.
- Preserve the original timestamp information supplied by the filesystem for payload files.
- Distinguish timestamp precision from timestamp accuracy.

Timestamp values must be normalized consistently for serialization.

## 5. Payload timestamps

Payload files retain their original modification timestamps.

When a file's timestamp changes, Dennis records the new value.

However:

- Payload timestamps do not participate in canonical inventory digests.
- Payload timestamps do not participate in DEX identity digests.
- Timestamp changes alone do not make otherwise identical content a different artifact.
- File content changes must trigger the appropriate content and inventory recalculations.

Timestamps remain descriptive metadata.

## 6. Timestamp authority configuration

External timestamp authorities are configured through the existing global configuration file:

`~/.dennis/config.json`

Rules:

1. External timestamping is optional.
2. Every explicitly configured authority is considered administrator-approved.
3. No external authority is required for plan generation.
4. Dennis attempts to contact every configured authority.
5. Failure to contact one authority must not prevent attempts to contact the others.
6. An empty authority configuration means local-clock operation.

Configuration trust is an administrative decision. It does not constitute independent cryptographic verification of a response.

Configuration credentials or secrets must not be copied into the artifact.

## 7. Timestamp authority requests

All configured authorities receive a request associated with the same canonical plan-content digest.

The digest represents the normalized plan contents and excludes:

- `plan_created_at`.
- Timestamp authority responses.
- Timestamp evidence.
- Operational diagnostics.

This avoids circular hashing.

The authority's response establishes its own asserted timestamp for the submitted digest.

The TSA-reported time and the locally recorded plan creation time remain separate.

## 7.1 Administrative Trust Boundary

Dennis Core operates as an evidence collection, preservation and presentation system. The administrator is responsible for configuring and governing trusted timestamp authorities and their authentication mechanisms.

Dennis Core records the configured authority, communication outcome, original response, interpreted timestamp and available provenance. It does not independently establish or adjudicate the enterprise's trust policy.

Operational acceptance of a timestamp response must never be represented as an independent judgment of authority authenticity or trustworthiness.

## 8. TSA response handling

Dennis Core 0.9.4 does not implement independent cryptographic verification of TSA signatures or certificate chains.

Instead, Core:

1. Sends the request.
2. Receives the response.
3. Preserves the response.
4. Interprets the timestamp where supported.
5. Records the outcome.
6. Reports communication and interpretation errors.

The response must not be described as cryptographically verified by Dennis Core.

### 8.1 Response status vocabulary

The following statuses distinguish operational outcomes:

| Status | Meaning |
|---|---|
| `RECEIVED` | A response was obtained. |
| `ACCEPTED` | The response was interpretable and supplied a usable timestamp. |
| `UNUSABLE` | A response was obtained but could not be interpreted or used. |
| `UNREACHABLE` | The authority could not be contacted. |
| `ERROR` | Another operational or processing error occurred. |

`ACCEPTED` is not equivalent to cryptographically `VALID`.

### 8.2 Response preservation

Dennis records:

- Authority identifier.
- Configured endpoint.
- Request digest.
- Original response or signed timestamp token.
- Parsed timestamp, where available.
- Response status.
- Error information.
- Selected canonical authority and timestamp, where applicable.

No response may be silently discarded because another authority supplied a later timestamp.

## 9. Canonical TSA timestamp selection

When multiple authorities return accepted timestamps:

1. Dennis compares the reported timestamps.
2. The most recent timestamp becomes `tsa_canonical_time`.
3. Dennis records which authority supplied it.
4. Every other authority response remains part of the artifact.

If all configured authorities fail or return unusable responses, Dennis uses the internal-clock fallback.

Dennis does not manufacture consensus, average timestamps or silently substitute one authority's response for another.

## 10. Local-clock fallback and FAT warning

The internal clock is always available as the universal fallback.

When no external TSA timestamp is accepted, Dennis:

- Retains `plan_created_at`.
- Records timestamp provenance as `INTERNAL_CLOCK`.
- Records the absence of accepted external timestamp evidence.
- Continues plan generation normally.
- Displays a prominent FAT warning.

The warning must be oversized, unmistakable, bold and direct.

Suggested CLI presentation:

**WARNING — UNVERIFIED TIME SOURCE**

**LOCAL SYSTEM CLOCK**

THIS TIMESTAMP WAS GENERATED USING THE LOCAL SYSTEM CLOCK.

It has NOT been independently verified by a trusted timestamping authority.

Its accuracy and authenticity cannot be independently guaranteed.

**DO NOT INTERPRET THIS TIMESTAMP AS UNIVERSALLY CANONICAL TIME.**

This is a warning, not an error. It must not prevent normal operation.

Ordinary verbosity settings must not silently suppress this warning.

## 11. Atomic DEX timestamp metadata

A DEX must contain all relevant timestamp information necessary to understand its timestamp history independently of the original machine.

This includes:

- Original plan creation timestamp.
- Timestamp provenance.
- Canonical plan-content digest submitted to authorities.
- Configured authority identifiers and relevant configuration snapshot.
- All authority responses received.
- All operational outcomes and errors.
- Parsed timestamps.
- Canonical TSA timestamp and its authority, if available.
- Relevant policy and format identifiers.

Where an authority does not respond, the corresponding failure must still be represented.

No separate diagnostic file may be required to reconstruct the recorded timestamp history.

Secrets and authentication credentials are excluded.

## 12. Determinism and reproducibility

Timestamp metadata is explicitly excluded from canonical artifact identity.

Consequently:

- Different creation timestamps do not create different semantic artifact identities.
- Different TSA responses do not create different semantic artifact identities.
- Operational diagnostics do not alter canonical content digests.
- Timestamp metadata must not be included accidentally in canonical hash projections.

The following distinction is mandatory:

**Canonical identity:** determined by the artifact's defined semantic content.

**Atomicity:** all relevant timestamp evidence is preserved inside the artifact.

**Serialization reproducibility:** identical normalized content and identical evidence must produce identical serialized output under the same serialization contract.

Dennis does not promise byte-for-byte identical DEX packages across separate executions when external TSA responses or operational diagnostics differ.

## 13. XDEX integration

Timestamp information is private artifact data.

When creating XDEX1:

- `plan_created_at` is included in the encrypted contents.
- `tsa_canonical_time` is included when available.
- All TSA responses and relevant timestamp diagnostics are included.
- Timestamp evidence is not exposed in public metadata unless explicitly authorized by the public metadata policy.

XDEX2 encrypts the complete serialized XDEX1 package according to the existing XDEX lifecycle contract.

Encryption does not modify the original timestamp values or evidence.

## 14. Verification responsibilities

In 0.9.4, Dennis Core verifies the structural consistency and integrity of the recorded timestamp information according to the artifact's existing verification mechanisms.

This includes checking:

- The recorded plan digest against the canonical plan contents.
- The association between requests and stored responses.
- The consistency of the selected canonical TSA timestamp with accepted recorded responses.
- The completeness and integrity of the stored timestamp records.

Dennis Core does not independently verify TSA cryptographic signatures or certificate chains in this release.

A response must not be presented as cryptographically authenticated merely because it was received from a configured authority.

## 15. Future plugin extensibility

TSA cryptographic verification is reserved for the plugin architecture planned for 0.9.6.

The 0.9.4 artifact format must preserve sufficient original evidence for future plugins to perform independent verification.

The future verification interface must support these standardized outcomes:

| Result | Meaning |
|---|---|
| `VALID` | Cryptographic authenticity and digest binding verified. |
| `INVALID` | Verification failed. |
| `UNSUPPORTED` | Plugin cannot handle the authority or response format. |
| `ERROR` | Verification could not be completed. |

An unsupported or errored verification must never be interpreted as successful.

### 15.1 Reference plugin

A reference verification plugin using Dennis-generated keys will demonstrate:

- Plugin registration and discovery.
- TSA response handling.
- Key resolution.
- Signature verification.
- Digest binding verification.
- Standardized result reporting.

Third-party developers can use it as a reference when implementing verification for their own timestamp authorities and key formats.

Plugins extend verification capabilities. They do not assume responsibility for Dennis artifact identity, trust policy or lifecycle authorization.

## 16. Release boundaries

### Dennis 0.9.4

Included:

- Local plan timestamp generation.
- UTC and nanosecond-capable representation.
- Optional TSA configuration.
- Requests to all configured authorities.
- Canonical plan-content digest submission.
- Response collection and preservation.
- Canonical external timestamp selection.
- Local-clock fallback.
- FAT warning.
- Atomic timestamp metadata in DEX.
- Timestamp preservation through the artifact lifecycle.
- Timestamp inclusion in XDEX1 encrypted contents.
- Structural timestamp evidence consistency checks.
- Defined future verification interface requirements.

Excluded:

- General plugin infrastructure.
- Third-party TSA cryptographic verification plugins.
- General-purpose certificate and key-format ingestion engines.
- Quorum or consensus mechanisms.

### Dennis 0.9.6

Planned:

- General plugin infrastructure.
- Reference verification plugin using Dennis-generated keys.
- Third-party TSA verification plugins.
- Support for additional authority-specific verification and key formats.

## 17. Acceptance criteria

The timestamp contract is considered implemented when:

1. `dennis plan` creates exactly one immutable plan creation timestamp.
2. Subsequent lifecycle operations preserve that timestamp.
3. Payload timestamps are preserved as informational metadata.
4. Timestamp changes alone do not affect canonical artifact identity.
5. All configured timestamp authorities are attempted.
6. All received responses and operational failures are recorded.
7. The most recent accepted TSA timestamp is selected.
8. The internal clock remains the universal fallback.
9. The FAT warning is displayed when external timestamp assurance is unavailable.
10. Timestamp evidence is completely contained in the DEX.
11. Timestamp information is protected inside XDEX1.
12. Structural verification does not falsely claim cryptographic TSA verification.
13. The artifact retains enough original evidence for future independent verification.
14. Serialization and canonical identity remain consistent with the existing determinism contract.
15. No unrelated files are created or modified as a side effect of timestamp handling.

---

## 18. Governing principle

> Dennis records time, preserves provenance and protects evidence. It does not pretend that a locally observed timestamp is universally authoritative, nor does it claim cryptographic verification it has not performed.
>
> External authorities provide additional timestamp evidence. Dennis preserves that evidence atomically and leaves room for independent verification through future plugins.
>
> **The artifact remains self-contained. Its identity remains deterministic. Its provenance remains inspectable.**