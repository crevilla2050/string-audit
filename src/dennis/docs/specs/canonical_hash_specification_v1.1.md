# Canonical Hash Specification v1

Status: **Stable --- Do Not Break Once Released**

Stable --- Do Not Break Once Released This document defines how Ilpresim
protocol objects compute their canonical identity.

The hash is the root of: \* sync identity \* deduplication \*
verification \* portability guarantees

## 1. Purpose

Canonical hashing must be deterministic across all platforms.

Two compliant implementations must produce identical hashes for
identical normalized input bytes.

Differences in runtime, architecture, or language must not affect
results.

## 1.1 Guarantees

The canonical hash must guarantee:

-   Identical plans always hash identically
-   Equivalent plans normalize to identical hashes
-   Formatting differences do not affect identity
-   Hashes are reproducible across platforms and languages

This enables:

-   Offline verification
-   Trustless sync
-   Anti-lock-in guarantees
-   Long-term determinism

## 2. Canonical Identity Definition

A protocol object's canonical identity is:

canonical_hash = sha256(canonical_json_bytes)

Where: \* canonical_json_bytes is a strictly normalized byte sequence \*
Encoding is UTF-8 without BOM

This hash is called:

canonical_hash

## 2.1 Canonical Hash Input

The canonical hash is computed over the entire normalized JSON protocol
object.

No fields are excluded.

If future versions introduce metadata that must not affect identity,
those fields must be excluded explicitly by a future hash version.

This is the immutable identity of a plan.

## 3. Canonical JSON Normalization Rules

Normalization must be deterministic across: \* Python \* Node \* Rust \*
Go

Browsers

No runtime-specific behavior allowed.

## 3.1 Encoding

-   UTF-8
-   No BOM
-   Unix newlines (`\n`{=tex}) only

## 3.2 Object Key Ordering

All JSON objects must have:

Lexicographically sorted keys (byte-wise, UTF-8)

Example:

{"a":1,"b":2}

Never:

{"b":2,"a":1}

This is mandatory at every depth.

## 3.3 Whitespace Policy

Canonical JSON must be:

-   No trailing spaces
-   No indentation
-   No pretty printing

Separator rules:

, between elements
:   between key/value

Example:

{"type":"rename","from":"a.js","to":"b.js"}

Not:

{ "type": "rename", "from": "a.js" } \## 3.4 Arrays

Arrays are order-sensitive.

Dennis must never reorder arrays during hashing.

If array ordering semantics change in future schemas, a new hash version
must be introduced.

## 3.5 Numbers

Numbers must follow strict normalization:

-   Integers
-   No leading zeros
-   Base-10 only

Valid:

1 42 0

Invalid:

01 1.0 Floats

Floats are dangerous for determinism.

Rules: \* Floats SHOULD be avoided in plan schemas. When floats are
used, they must be serialized as JSON numbers using the minimal decimal
representation that round-trips exactly in IEEE-754 double precision. \*
No trailing zeros \* Exponential notation is forbidden and MUST NOT be
used

Preferred:

0.5 1.25

Avoid:

0.5000 1.250000 5e-1

## 3.6 Boolean + Null

Must use lowercase JSON literals:

true false null

No language-specific variants allowed.

## 3.7 String Normalization

Normalization must occur BEFORE hashing. Unicode strings must be
normalized to NFC before canonical JSON serialization.

Strings must be:

-   UTF-8
-   NFC normalized (Unicode normalization form C)

This prevents cross-platform mismatches.

Example:

é composed vs decomposed must hash identically

## 3.8 Escaping Rules

Use minimal escaping:

Escape only:

" as \"  as \\

control characters

Do not escape: \* Unicode unnecessarily \* Forward slashes

3.9 Newline Handling Inside Strings If a string contains newlines:

Normalize to `\n`{=tex} Never `\r\n`{=tex}.

## 4. Canonical Byte Serialization

Canonical JSON serialization must produce identical byte sequences for
identical normalized input objects.

Hashing operates on the raw byte sequence, not on parsed structures.
Input JSON documents may contain arbitrary Unicode. Normalization must
be applied before serialization.

The canonical byte sequence must always be valid UTF-8.

After normalization:

Serialize JSON as UTF-8 bytes No trailing newline No BOM No whitespace
padding

This byte stream is hashed directly.

## 5. Hash Function

Algorithm: SHA-256

Output format: hex lowercase

Example: 3f786850e387550fdab836ed7e6dc881de23001b

No base64. No prefixes.

Human-readable and tooling-friendly.

## 6. Versioning Strategy

This is Canonical Hash v1. If normalization rules ever change:

-   Introduce Canonical Hash v2
-   Never retroactively change v1

Plan metadata must include:

{ "hash_version": 1 }

This prevents:

-   silent identity drift
-   cross-version mismatches

## 7. Hash Stability Guarantees

The protocol guarantees:

Hashes remain stable forever under v1 rules Future engines must support
v1 verification v1 hashes remain verifiable even after schema evolution

This is critical for:

-   10+ year reproducibility
-   Legal auditability
-   Archival use

## 8. Cross-Language Determinism Tests

The official Dennis test suite must include:

Golden tests:

plan.json → expected_hash

Implemented in:

-   Python
-   Node
-   Rust (future)
-   WASM (future)

All implementations must produce identical hashes.

## 9. Hash Usage Across the System

The canonical hash is used for:

-   File naming
-   Deduplication
-   Sync identity
-   SaaS storage keys
-   Verification
-   Anti-lock-in guarantees

Example file layout:

plans/ 3f786850e3....json \## 10. Relationship to UUIDs

Implementations MAY use a dual identity model:

canonical_hash = immutable content identity

runtime_uuid = mutable coordination identity (SaaS only)

If conflict occurs:

hash always wins \## 11. Security Considerations

SHA-256 is chosen for:

-   Collision resistance
-   Tooling availability
-   Long-term trust

Version 1 does not require: \* salted hashes \* keyed hashes \*
signatures

Those may be layered later without breaking v1.

## 12. Anti-Lock-In Guarantee

Because hashes are:

-   deterministic
-   offline reproducible
-   content-addressed

Users can:

-   verify SaaS data locally
-   migrate providers
-   archive plans permanently

This specification is the root of the protocol's portability and
sovereignty guarantees.

## 13. Implementation Notes

Recommended libraries:

Python json.dumps(..., separators=(',', ':'), sort_keys=True)

plus manual normalization layers JS

deterministic stringify (not native JSON.stringify) Rust

serde with canonical serializer

## 14. Non-Goals

This specification intentionally does NOT define: \* Plan schema \*
Export formats \* Storage layout \* API behavior

Only identity.

## 15. Stability Promise

Once Canonical Hash v1 is released:

-   It becomes immutable
-   Any breaking change requires v2
-   v1 support must remain indefinitely

This is a core Dennis stability contract.
