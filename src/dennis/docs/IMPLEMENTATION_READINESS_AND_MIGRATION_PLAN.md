# Dennis / Ilpresim Trust
# Implementation Readiness and Migration Plan

**Document status:** Working baseline — ready for implementation inventory  
**Version:** 1.0  
**Date:** 2026-11-12

---

## 1. Purpose

This document establishes the transition from the existing Dennis Keygen, signing, verification, and provenance implementations toward the agreed Dennis / Ilpresim Trust Signing Authority architecture.

The objective is not to redesign Dennis from scratch.

We already have:

- An existing Dennis Keygen implementation.
- Existing signing and verification code.
- Existing key and trust-management operations.
- Existing DEX validation and provenance mechanisms.
- An agreed Signing Authority architecture.
- An approved portable evidence format.
- A defined key lifecycle and authorization model.
- A defined TSA and Signing Server responsibility boundary.

The remaining preparation is to establish precisely what is implemented, identify discrepancies, and define a controlled implementation sequence.

**No implementation changes should begin until the implementation inventory and test baseline have been reviewed.**

## 2. Governing principles

All implementation work must respect the following principles.

### 2.1 German Rule

*Wenn es nicht kaputt ist, repariere es nicht.*

Existing functionality should not be changed without a demonstrated architectural or operational reason.

### 2.2 Golden Rule

Never compromise determinism.

Never silently alter historical cryptographic facts, historical artifact meaning, or verification semantics.

No deletions without explicit approval.

### 2.3 Vespene Gas Rule

Do not generate or modify code before the relevant design and implementation scope are understood.

### 2.4 Development principles

- CLI-first.
- Offline-first where applicable.
- Reproducible behavior.
- Explicit versioning.
- Deterministic serialization and verification.
- Clear separation of responsibilities.
- No silent fallback or substitution.
- No unnecessary compatibility complexity during beta.
- Historical evidence must remain verifiable.

### 2.5 Beta compatibility policy

Dennis is still in beta.

Existing implementation details, interfaces, and signature representations may be redefined when necessary.

Backward compatibility is not yet an unconditional commitment.

However, historical cryptographic integrity and reproducibility are not disposable beta concerns.

We may change representation, implementation, and architecture without silently changing what a historical signature meant or whether it can be verified.

---

## 3. Target architecture

### 3.1 Signing Authority

The Signing Authority is the canonical cryptographic authority.

It owns:

- Key registration.
- Key lifecycle.
- Key activation authorization.
- Private-key access.
- Signing operations.
- Evidence construction.
- Evidence signing.
- Evidence persistence.
- Registry operations.
- Cryptographic verification.

Only authorized ACTIVE keys may perform new signing operations.

The Signing Authority must never depend on the public TSA gateway to perform its internal cryptographic responsibilities.

### 3.2 TSA Gateway

The public TSA is a gateway.

It owns:

- External HTTPS communication.
- Client authentication.
- Public request validation.
- Internal request forwarding.
- Signing Server response validation.
- Relay of authoritative signed evidence.

It does not own:

- Timestamp generation.
- Clock-health decisions.
- Canonical evidence construction.
- Signing-key management.
- Canonical registry persistence.

### 3.3 Signing Server

The Signing Server is the canonical Timestamp Authority.

It owns:

- System-clock health verification.
- Timestamp generation.
- Canonical evidence construction.
- Evidence signing.
- Evidence persistence.
- Registry lookup.
- Evidence verification.

Timestamps originate from the Signing Server's operating-system clock.

If the clock is unhealthy, issuance must fail.

There must be no fallback timestamp, fabricated timestamp, clamping, or monotonic adjustment intended to conceal clock problems.

### 3.4 Protocol separation

Two independently versioned protocols exist:

1. Public client ↔ TSA Gateway.
2. TSA Gateway ↔ Signing Server.

The internal protocol uses JSON over HTTPS and mutual TLS.

TLS 1.2 is the minimum; TLS 1.3 is preferred.

The internal service must not rely on network isolation alone for authentication.

---

## 4. Databases and data ownership

The architecture uses three distinct databases with separate responsibilities.

### Database 1 — Operational Signing Authority database

Owns operational signing authority information, including:

- Registered key identities.
- Public-key records.
- Key lifecycle state.
- Authorization requests and decisions.
- Signing-key metadata.
- Signing operations and their relationships to evidence.
- Operational authority configuration.

Private keys are centrally controlled by the Signing Authority.

The database must support multiple keys and standard key representations.

The database must not contain the independent secrets required to decrypt protected private-key material.

### Database 2 — Historical and trust records

Owns historical key and trust information, including:

- Legacy key identities.
- Historical public keys.
- Historical lifecycle information where available.
- Historical authorization records where available.
- Historical signing relationships.
- Migration records.
- Associations with existing DEX artifacts.
- Canonical timestamps establishing the migration baseline.

Legacy key identities are interpreted as RETIRED for new operational purposes.

They remain available for historical verification.

Unknown historical facts must remain explicitly unknown.

### Database 3 — Evidence and registry database

Owns canonical issued evidence and registry information.

Responsibilities include:

- Evidence persistence.
- Evidence identifiers.
- Authority identifiers.
- Request identifiers.
- Payload hashes.
- Timestamps.
- Evidence signatures and associated metadata.
- Registry lookup.
- Retention policy.

Retention is enabled by default, including Enterprise deployments.

Enterprise administrators may explicitly opt out.

Disabling retention affects persistence only. It does not disable clock checks, timestamp generation, evidence construction, signing, or returning signed evidence.

A persistence failure when retention is enabled prevents successful retained issuance.

### Database separation principle

The three databases must not become interchangeable repositories.

Each database has an explicit data owner and responsibility boundary.

The final physical deployment and exact schema remain implementation decisions to be established during the inventory and detailed interface design.

---

## 5. Key generation and management

### 5.1 Key Generation

Existing Dennis Keygen is the starting point.

It must be reviewed and adapted rather than discarded without investigation.

The target implementation must:

- Generate standard Ed25519 keypairs.
- Use secure random key generation.
- Protect private-key material.
- Support standard key representations.
- Produce stable public-key identities.
- Avoid persistent plaintext private-key exports.
- Support the Signing Authority's centralized key-management model.

The existing separation between raw cryptographic generation and file-oriented CLI behavior should be preserved where appropriate.

Key generation must precede key registration in the implementation sequence.

### 5.2 Key identity

A key ID must identify the cryptographic public key.

It must not be an arbitrary alias supplied by a caller.

The final fingerprint derivation must be deterministic and based on a clearly specified representation of the public-key bytes.

Existing implementations use different derivation approaches. This discrepancy must be resolved during the inventory.

### 5.3 Key registration

Registration creates a key identity within an organization and associates its public-key material with that identity.

Registration does not authorize signing.

### 5.4 Two-person activation authorization

For Ilpresim-managed keys, activation requires two distinct authorized actors.

1. An organization administrator registers the key and requests activation.
2. A Signing Authority administrator independently reviews and authorizes activation.

The identities and decisions of both actors must be recorded.

No implicit, inherited, or self-approval is permitted.

The authorization history must preserve:

- Key fingerprint.
- Organization identity.
- Requesting administrator identity.
- Authorizing administrator identity.
- Timestamps.
- Decisions.
- Rejections and their recorded outcomes.

Changing the public key creates a new cryptographic identity and requires a new activation process.

This governance requirement applies to Ilpresim-managed keys. It must not be imposed automatically on external key providers.

### 5.5 Key lifecycle

Accepted lifecycle states:

| State | Meaning |
|---|---|
| REGISTERED | Registered, not authorized to sign |
| PENDING_AUTHORIZATION | Awaiting activation approval |
| ACTIVE | Authorized to sign |
| SUSPENDED | Temporarily prevented from signing |
| RETIRED | Permanently withdrawn from new signing |
| REVOKED | Permanently withdrawn for a security or trust reason |
| EXPIRED | Permanently inactive after configured expiration |

Only ACTIVE keys may sign.

Lifecycle state must remain distinct from verification results.

For example, SIGNATURE_VALID is a verification result, not a key lifecycle state.

Retired keys remain available for historical verification.

---

## 6. Historical migration strategy

### 6.1 Historical signature verification

Historical signatures must remain verifiable.

This is necessary to preserve the relationship between historical signing activity and the corresponding DEX artifacts.

Historical verification must preserve the original cryptographic material and the information necessary to reconstruct the original verification input.

### 6.2 Legacy key identities

All legacy key identities are treated as RETIRED in the new operational model.

They are:

- Available for historical verification.
- Read-only.
- Ineligible for new signing operations.

Retirement does not invalidate signatures legitimately produced while the key was authorized.

Historical authorization status must not be invented when it cannot be established.

### 6.3 Existing key files

Existing `.key` and `.pub` files will be moved to the legacy archive:

`./dennis/.../old_keys`

The exact path must be established against the existing directory structure before implementation.

Migration requirements:

- Preserve original file contents.
- Preserve existing public-key identities.
- Keep legacy private keys out of the active signing-key discovery mechanism.
- Restrict access to archived private keys.
- Do not automatically import archived private keys as active credentials.
- Verify archive completeness before considering migration successful.

Moving private keys is an archival operation, not a cryptographic revocation mechanism.

### 6.4 Legacy signature representation

Because Dennis remains in beta, the legacy signature representation may be rewritten.

However:

**Rewriting representation must not destroy historical cryptographic verifiability.**

The migration must preserve:

- Original signature bytes.
- Original public key.
- Original key identity.
- Original verification input or sufficient information to reconstruct it.
- Original signature algorithm.
- Available signing-time and trust information.
- Association with the corresponding DEX artifact.

Where necessary, retain the original representation alongside the migrated representation.

### 6.5 DEX coexistence

Historical and newly signed DEX artifacts must coexist.

The verifier must identify the applicable signature/evidence format and apply the appropriate verification rules.

New artifacts use the approved Ilpresim evidence model.

Historical artifacts remain verifiable according to their preserved historical cryptographic rules.

There is no requirement to rewrite every existing DEX artifact merely to make it conform to the new format.

### 6.6 Historical records and canonical timestamps

Historical key and trust records are preserved in Database 2.

The TSA interface is used to establish a canonical timestamp for the historical migration record or registry snapshot.

The resulting TSA evidence must be associated with the relevant historical records.

Two separate facts must be preserved:

- `historical_effective_time`: when an original event occurred, if known.
- `canonical_recorded_time`: when the historical record was submitted to and timestamped by the TSA.

A TSA timestamp establishes that the submitted record existed no later than the issued timestamp.

It does not independently prove that an earlier historical authorization event occurred on that date.

Unknown historical dates remain unknown.

The initial historical trust and key registry snapshot should be timestamped as a migration baseline.

### 6.7 Migration integrity

The migration process must be:

- Explicit.
- Auditable.
- Repeatable where possible.
- Non-destructive.
- Independently verifiable.

It must not silently change historical key identities, signatures, DEX relationships, or trust decisions.

---

## 7. Portable Ilpresim Evidence Document

The approved portable evidence document uses the following structure:

- `document_version`
- `document_type`
- `evidence`
- `signature`
- `verification`

### 7.1 Evidence

Evidence version 1.0 uses:

- `evidence_version`
- `canonicalization`
- `evidence_id`
- `authority_id`
- `protocol`
- `request_id`
- `payload_hash`
- `timestamp`
- `clock_health`

Canonicalization is JCS (RFC 8785).

The signature input is exactly the UTF-8 encoding of the JCS serialization of the evidence object.

### 7.2 Signature envelope

The signature envelope contains:

- `signature_version`
- `algorithm`
- `key_id`
- `signature`

Algorithm: Ed25519.

The signature is a 64-byte Ed25519 signature encoded as unpadded Base64URL.

The signature authenticates the evidence object, not the mutable verification report.

### 7.3 Verification report

The verification report distinguishes:

- Schema validity.
- Cryptographic signature validity.
- Key trust.
- Registry status.

A valid signature does not automatically establish key trust.

A registry miss does not automatically mean that a signature is invalid.

The verifier must independently evaluate these properties.

### 7.4 Versioning

Outer document, evidence, and signature envelope versions are independent.

Changes to incompatible outer structure require a new document version.

Changes to evidence semantics require a new evidence version.

Changes to signature-envelope semantics require a new envelope version.

Historical interpretation must remain stable.

---

## 8. Verification architecture

The verifier consists of:

1. A shared verification library.
2. A standalone CLI using that same library.

There must not be separate, divergent verification implementations.

Verification responsibilities include:

- Structural and schema validation.
- Canonicalization.
- Cryptographic signature verification.
- Key trust evaluation.
- Registry lookup where available.
- DEX/evidence payload-hash association.

Offline cryptographic verification may be possible using a supplied public key.

However, possession of a public key embedded in an artifact does not establish trust.

Trust requires an independently established trust anchor or an authorized trust source.

### Organization boundaries

Key validation and registry access must respect organization boundaries.

An organization must not be able to enumerate another organization's keys or discover whether an arbitrary key belongs to another organization.

`dennis validate-key <public.key>` must operate within the authenticated user's organization.

The same principle applies to Enterprise deployments.

---

## 9. Security and persistence requirements

### 9.1 Private-key protection

Private signing keys remain exclusively controlled by the Signing Authority for centrally managed keys.

Applications never receive centrally managed private keys.

Encryption keys, signing keys, and registry indexing secrets must remain separate.

The database must not contain the independent secrets needed to decrypt private-key material.

Transient in-memory decryption for signing is permitted.

### 9.2 Evidence encryption

Sensitive evidence fields must be encrypted at rest.

Candidate AEAD algorithms:

- AES-256-GCM.
- ChaCha20-Poly1305.

The final algorithm selection remains open.

Encryption keys must support versioning and rotation.

Encrypted backups must be stored separately from the keys needed to decrypt them.

### 9.3 Ledger integrity

Authenticated encryption protects encrypted content against modification, but does not independently detect missing, reordered, or rolled-back records.

Ledger integrity requires separate consideration of:

- Append-only history.
- Hash chaining.
- Independently protected checkpoints.
- Backup integrity.
- Recovery procedures.

A hash chain alone does not prevent a database administrator from rewriting the entire history and recomputing the chain.

### 9.4 Operational logging

Operational logs must not unnecessarily contain:

- Complete request bodies.
- Authentication headers.
- Secrets.
- Unnecessary payload hashes.
- Unnecessary personal or business information.

Operational logs and canonical evidence are separate concerns.

---

## 10. Implementation inventory

Before modifying code, complete a read-only review of the existing implementation.

For each relevant component, establish:

| Field | Required information |
|---|---|
| Component | Module, class, function or CLI command |
| Current behavior | What the code actually does |
| Dependencies | What calls it and what it calls |
| Tests | Existing test coverage and observed results |
| Architectural requirement | What the agreed design expects |
| Discrepancy | Difference between actual and intended behavior |
| Planned action | Retain, adapt, replace, introduce or exclude |

### 10.1 Priority review areas

**A. Key Generation**

- Raw key generation.
- Ed25519 handling.
- KDF and private-key encryption.
- Key ID derivation.
- Public identity document.
- File permissions.
- CLI configuration updates.
- Error handling and atomicity.

**B. Key Registration and Trust**

- Existing trust database.
- Key registration functions.
- Approval operations.
- Root-key bootstrap behavior.
- Trust delegation.
- Authorization identity.
- Transaction boundaries.
- Actual CLI exposure.

No `dennis trust` CLI workflow should be assumed to exist.

**C. Signing**

- Private-key loading.
- Signature input serialization.
- Key ID consistency.
- Signature metadata.
- Artifact writing.
- Atomicity.
- Legacy signature compatibility.

**D. Verification**

- DEX loading.
- Signature verification.
- External and embedded public keys.
- Trust evaluation.
- Organization boundaries.
- Error handling.
- Historical verification.

**E. Provenance**

- Provenance data structures.
- Hash computation.
- Persistence.
- Manifest integration.
- Validation.
- Historical associations.

Existing provenance mechanisms must not be assumed to provide authenticated or immutable history merely because they contain a hash.

**F. File-admission infrastructure**

Review the Hound, Mickey, and Watsons responsibilities and their actual call paths.

Establish whether the uploaded implementations are connected through the expected interfaces.

In particular, resolve the apparent `utf8.decode()` versus `decode_text()` interface discrepancy by inspecting the actual package facade and exports.

General file-admission infrastructure remains outside the cryptographic Signing Authority boundary.

**G. TSA and Signing Server**

- Existing timestamp implementation.
- Clock-health inspection.
- Evidence construction.
- Signing.
- Persistence.
- Internal transport.
- Authentication.
- Gateway response verification.

### 10.2 Existing discrepancies to resolve

The following are already known from the reviewed implementation:

1. Key ID derivation differs between generation and signing.
2. Caller-supplied key IDs can override derived identities in existing signing code.
3. Existing signature serialization uses sorted JSON rather than genuine RFC 8785 JCS.
4. Existing signing and verification paths do not consistently use the same verification strategy.
5. Existing key approval operations have incomplete authorization semantics.
6. The existing provenance models differ between validation and provenance utilities.
7. Existing provenance hashing is an unkeyed integrity checksum, not authenticated audit history.
8. Existing DEX validation contains suspicious result assignments and inconsistent checks that require further examination.
9. Existing file-admission interfaces need confirmation against the actual package exports.
10. Existing file writes and database operations need an atomicity review.

These are inventory findings, not authorization to rewrite everything.

Each discrepancy must be traced to its actual execution path and tests before deciding on a change.

---

## 11. Test baseline and acceptance criteria

Before implementation:

1. Identify the existing test suite.
2. Run the relevant tests without modifying source files.
3. Record the results.
4. Identify existing failures.
5. Establish which tests cover the target architecture.
6. Identify missing tests.

The implementation must eventually demonstrate the following:

| Area | Acceptance criterion |
|---|---|
| Key generation | Correct standard Ed25519 keypair and secure private-key handling |
| Key identity | Stable deterministic fingerprint from public-key bytes |
| Registration | Registration does not implicitly authorize signing |
| Authorization | Two distinct authorized actors required for Ilpresim key activation |
| Lifecycle | Only ACTIVE keys may sign |
| Retirement | Retired keys remain available for historical verification |
| Signing | Signature verifies against precisely defined canonical bytes |
| Evidence | Strict schema and genuine RFC 8785 canonicalization |
| Clock health | Unhealthy or incomplete clock measurements prevent issuance |
| Persistence | Retained issuance cannot succeed if persistence fails |
| Registry | Lookup respects organization boundaries |
| Verification | Signature validity, key trust and registry status remain distinct |
| Migration | Historical signatures remain verifiable |
| Historical timestamping | Migration records have independently verifiable TSA evidence |
| TSA transport | Gateway never substitutes its own timestamp |
| Failure handling | Deterministic errors and no silent fallback |
| DEX coexistence | Historical and newly signed artifacts can both be verified |

---

## 12. Implementation sequence

Implementation proceeds in controlled stages.

### Stage 0 — Recovery and inventory closure

- Complete the implementation inventory.
- Review actual dependency and execution paths.
- Establish the test baseline.
- Resolve discrepancies between reviewed code and documented architecture.
- Finalize component ownership and interface contracts.

**Exit condition:** We know what exists, what works, what is missing, and what must change.

### Stage 1 — Key Generation

- Recover existing Dennis Keygen.
- Define the canonical public-key identity.
- Adapt private-key protection and key representation.
- Correct file handling and configuration-update ordering.
- Establish secure file permissions.
- Add tests.

**Exit condition:** Key generation produces a valid, correctly identified keypair compatible with the Signing Authority's storage model.

### Stage 2 — Key Registration

- Define registration input and output contracts.
- Register public-key identities.
- Persist registration metadata.
- Enforce organization boundaries.
- Ensure registration cannot authorize signing.

**Exit condition:** Keys can be registered and retrieved without being implicitly activated.

### Stage 3 — Authorization and Lifecycle

- Implement the two-person activation workflow.
- Record authorization decisions.
- Implement lifecycle transitions.
- Enforce signing eligibility.
- Preserve historical state.

**Exit condition:** Only authorized ACTIVE keys can sign, and every relevant transition is auditable.

### Stage 4 — Signing Authority Core

- Implement internal component boundaries.
- Integrate key management and signing.
- Establish canonical evidence construction.
- Enforce clock-health requirements.
- Define deterministic error behavior.

**Exit condition:** The authority can produce valid signed evidence under the approved rules.

### Stage 5 — Evidence Persistence and Registry

- Implement the approved portable evidence format.
- Implement retention policy.
- Persist canonical evidence.
- Implement registry lookup.
- Establish organization isolation.
- Add integrity and recovery mechanisms.

**Exit condition:** Issued evidence can be retained and independently retrieved and verified.

### Stage 6 — Historical Migration

- Archive existing `.key` and `.pub` files.
- Register legacy public-key identities as RETIRED historical identities.
- Preserve original signature material.
- Preserve DEX associations.
- Migrate historical metadata where appropriate.
- Establish the canonical TSA timestamp for the migration baseline.
- Verify migrated historical artifacts.

**Exit condition:** Historical signatures remain verifiable, and the migration baseline has canonical timestamp evidence.

### Stage 7 — Verification Library and CLI

- Implement the shared verification library.
- Support the new evidence format.
- Preserve historical verification paths.
- Integrate key trust and registry status.
- Implement the standalone CLI.
- Test online and offline verification behavior.

**Exit condition:** Historical and new DEX artifacts can be independently verified using the agreed trust model.

### Stage 8 — TSA Gateway Integration

- Implement or complete the public HTTPS interface.
- Implement the versioned internal protocol.
- Establish mTLS authentication.
- Validate Signing Server responses.
- Relay authoritative signed evidence.
- Test failure and unavailable-service behavior.

**Exit condition:** The gateway reliably exposes the canonical Signing Server without taking over its responsibilities.

### Stage 9 — End-to-end acceptance

Exercise the entire lifecycle:

1. Generate a key.
2. Register the key.
3. Request activation.
4. Independently authorize activation.
5. Sign an operation.
6. Construct evidence.
7. Persist evidence.
8. Retrieve evidence through the registry.
9. Verify its signature.
10. Verify key trust.
11. Associate evidence with a DEX artifact.
12. Verify the complete artifact.
13. Repeat with historical artifacts.
14. Exercise failure conditions and recovery.

**Exit condition:** The complete issuance-to-verification lifecycle passes the acceptance criteria.

---

## 13. Explicitly excluded from the initial implementation

The following are not part of the immediate Signing Authority implementation:

- Commercial credit management.
- Billing and payment processing.
- Subscription management.
- Customer portal.
- Account history interface.
- Public key directory or public key search.
- Blockchain anchoring.
- RFC 3161 compatibility.
- X.509 timestamp tokens.
- DEX artifact storage as a TSA responsibility.
- HSM implementation.

Future HSM/KMS support remains a desirable architectural capability, not a requirement for the first implementation.

The commercial Ilpresim Trust layer must remain separate from the cryptographic Signing Authority.

---

## 14. Implementation discipline

All implementation work follows these rules:

1. Review before modifying.
2. One controlled change at a time.
3. No unrelated refactoring.
4. No destructive Git operations.
5. Preserve untracked files.
6. Do not delete historical material without explicit approval.
7. Run relevant tests after each meaningful change.
8. Record architectural decisions when new information changes the design.
9. Do not claim a component is implemented merely because a related function exists.
10. Do not claim successful verification without an actual test.

The repository is the implementation source of truth.

This document is the architectural and migration reference, not a substitute for inspecting the actual code.

---

## 15. Current readiness assessment

| Area | Status |
|---|---|
| Target architecture | Defined |
| TSA / Signing Server responsibilities | Defined |
| Portable evidence format | Approved |
| Key lifecycle | Defined |
| Two-person activation | Agreed |
| Database responsibility separation | Defined at architectural level |
| Historical signature preservation | Agreed |
| Legacy key retirement | Agreed |
| Legacy key-file archival | Agreed |
| DEX coexistence | Agreed |
| Historical migration timestamping | Agreed |
| Migration implementation details | Pending inventory |
| Component interface contracts | Pending finalization |
| Implementation inventory | In progress |
| Test baseline | Pending confirmation |
| Implementation | Not started under this plan |

## 16. Immediate next action

Complete **Stage 0 — Recovery and inventory closure**.

The immediate deliverable is an implementation gap matrix identifying:

- Existing components.
- Actual behavior.
- Dependencies and call paths.
- Existing tests and results.
- Architectural discrepancies.
- Required changes.
- Proposed implementation order.

Only after reviewing and agreeing on that matrix should implementation begin.

---

**Final objective**

Evolve Dennis into a deterministic, independently verifiable signing and timestamping system without sacrificing the historical integrity of its existing DEX artifacts.

We are not starting over.

We are preserving what is valuable, correcting what is inconsistent, and building the missing pieces with deliberate architectural control.