Dennis — DEX Artifact Identity Model v1

Status: Stable Candidate

This specification defines how Dennis identifies transformation artifacts and distinguishes between:

* transformation identity
* artifact container identity
* trust state

1. Motivation

A DEX artifact contains multiple layers:

DEX
 ├ manifest.json
 ├ payload/
 │   └ plan.json
 └ signatures/

Different users may:

* sign the artifact
* repackage it
* distribute it
* store it in registries

Therefore, identity must be defined carefully.

Dennis separates identity into three levels.

2. Identity Layers

Dennis defines three distinct identifiers.

Identity	What it represents	Mutability
payload_hash	transformation identity	immutable
artifact_hash	container identity	mutable
signature_set_hash	trust state identity	mutable

Each exists for a different purpose.

3. Payload Identity
payload_hash

Definition:

payload_hash = SHA256(canonical_payload)

Where:

canonical_payload = canonical JSON serialization of payload/plan.json
according to canonical_hash_v1.md

Rules are defined in:

canonical_hash_v1.md

Properties:

* deterministic
* content-addressed
* immutable

Two DEX artifacts with the same payload_hash represent the same transformation.

Even if:

* signatures differ
* metadata differs
* compression differs

Example:

payload_hash = 3fa4b5...
This is the canonical identity of the transformation.

payload_hash MUST be stored inside manifest.json

This identity is useful for:

* transformation identity
* content-addressed storage
* caching
* deduplication

4. Artifact Container Identity
artifact_hash

Definition:

artifact_hash = SHA256(full raw DEX file bytes)

Where:

full_dex_bytes = gzip(tar(container))

This represents the exact binary artifact.

Properties:

* changes if artifact is repackaged
* changes if signatures are added
* changes if metadata changes

This identity is useful for:

* registry storage
* caching
* deduplication

Example:
artifact_hash = 91e8c3...


5. Signature Set Identity
signature_set_hash

Definition:

signature_set_hash = SHA256(canonical_signature_manifest)

Where:

canonical_signature_manifest =
canonical JSON of manifest.signatures

signatures must be sorted lexicographically by:

(key_id, created_at)

Before hashing, signatures MUST be sorted by:

1. key_id
2. created_at

Properties:
* changes when signatures are added
* independent of payload identity
* tracks trust state evolution

Example:

signature_set_hash = f3a98b...

This allows Dennis to say:

Same transformation
but
different trust chain

6. Relationship Between Identities

Example scenario:

artifact A
payload_hash = X
signature_set_hash = A
artifact_hash = M

Later:

artifact B
payload_hash = X
signature_set_hash = B
artifact_hash = N

Interpretation:

- Same transformation
- Different signatures
- Different container

Dennis UI will show:

- Transformation: identical
- Signatures: changed
- Artifact container: different


7. Registry Indexing
Dennis Forge should index artifacts primarily by:

payload_hash

Because that represents the transformation identity.

Example storage layout:

storage/
  payloads/
    ab/cd/ef/<payload_hash>/
        artifact_1.dex
        artifact_2.dex

This allows multiple containers with identical payloads.
Registries SHOULD index artifacts by payload_hash and MAY additionally index by artifact_hash.

8. Artifact Deduplication
During ingestion:

if payload_hash already exists:
    link artifact to existing payload
else:
    store new payload

This reduces storage.

9. Trust Evolution
Signatures accumulate over time.

Example history:

artifact v1
payload_hash = X
signatures = [dev]

artifact v2
payload_hash = X
signatures = [dev, security_team]

artifact v3
payload_hash = X
signatures = [dev, security_team, auditor]

Each stage produces a new:

signature_set_hash
artifact_hash

But payload_hash remains constant.

10. CLI Verification

Dennis CLI verification checks:

* payload_hash
* signature validity
* signature_set integrity

Optional registry verification may check:

* transparency log inclusion
* registry snapshot
* signature trust chains

Example:

dennis verify file.dex

or

dennis verify --remote-registry https://forge.dennis.dev file.dex


11. Security Model
Separating identities prevents several classes of attack.

Signature rewriting attacks
→ Cannot change payload_hash

Artifact repackaging
→ Changes artifact_hash but not payload_hash

Signature stripping
→ Detected via signature_set_hash

12. UX Implications

Dennis UI can display:

* Transformation
* Payload hash
* Signature history
* Artifact lineage

Example:

Transformation ID:
3fa4b5...

Signatures:
dev
security-team
auditor

Containers:
artifact_1.dex
artifact_2.dex
artifact_3.dex

This creates a transparent provenance chain.

13. Future Extensions

The identity model supports:

* artifact lineage graphs
* supply-chain verification
* registry transparency logs
* Merkle proof inclusion

Without breaking v1 compatibility.