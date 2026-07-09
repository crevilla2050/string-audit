# The Chronicle Protocol

**Version: 1.0
**Status: Proposed Standard
**Protocol: DeCS (Dennis Chronicle System)

---

# 1. Purpose

A Chronicle is the immutable institutional memory of an Ilpresim scope. A scope may represent an artifact, a project, a workspace, or another protocol-defined preservation boundary. The Chronicle Protocol is independent of scope; only the owner of the Chronicle changes.

It preserves intentional human decisions and their supporting context.

History begins only when humans intentionally preserve it.

The Chronicle is independent from the Workspace. The Workspace is mutable; the Chronicle is immutable.

---

# 2. Design Goals

The Chronicle SHALL:

- Be self-contained.
- Be independently verifiable.
- Remain portable across implementations.
- Not require external state for validation.

The Chronicle SHALL be self-contained. Verification and interpretation of a Chronicle SHALL NOT depend upon the availability of an external database. Implementations MAY use databases for indexing, caching, querying, or collaboration services, but such databases SHALL remain non-authoritative.

---

# 3. Terminology

## Workspace

A mutable Decision Space implemented as a contextual projection over normalized knowledge objects.

## Chronicle

The immutable institutional memory associated with an Ilpresim scope.

## Scroll

The atomic unit of preservation.

A Scroll represents one coherent conversation ending in one preserved outcome.

## Annotation

Mutable notes attached to a Working Scroll until preservation.

## Relationship

A typed directional connection between Scrolls.

## Evidence

Any supporting material referenced by a Scroll.

---

# 4. Chronicle Lifecycle

Workspace
↓
Working Scroll
↓
Evidence / Annotations / Relationships
↓
Human Review
↓
Commit
↓
Canonical Scroll Hash
↓
Chronicle Hash
↓
DEX Hash

The Working Scroll is mutable.

After commit it SHALL become immutable.

---

# 5. Scroll Model

Working Scrolls use temporary identities.

Upon commit:

1. A canonical Scroll Hash SHALL be computed.
2. Scroll hashes SHALL compose into the Chronicle Hash.
3. Where applicable, the Chronicle Hash SHALL compose into the enclosing scope hash (e.g., DEX Hash).

Each committed Scroll SHALL contain:

- canonical_hash
- title (optional but recommended)
- outcome
- timestamps
- authors
- annotations
- evidence references
- relationships
- signatures

Possible outcomes include:

- approval
- rejection
- investigation
- observation
- cancellation
- superseded
- no_conclusion

---

# 6. Annotation Model

Annotations belong to a Scroll.

- Mutable while the Scroll is in the Working Chronicle.
- Immutable after commit.
- Included in the canonical hash.

---

# 7. Relationship Model

Relationships are first-class protocol objects.

Each relationship SHALL include:

- source Scroll
- target Scroll
- relationship type

Relationships are directional.

---

# 8. Hashing

Working Scrolls use temporary identities.

Upon commit:

1. Canonical Scroll Hash.
2. Chronicle Hash.
3. DEX Hash.

---

# 9. Serialization

The protocol defines the logical model first.

JSON is the canonical serialization format for Version 1.

---

# 10. Verification

Verification SHALL validate:

- schema
- canonical serialization
- Scroll hashes
- Chronicle hash
- signatures
- relationship integrity

Verification SHALL NOT modify the Chronicle.

---

# 11. Roles

## Workspace

Provides the mutable Decision Space.

## Lantern

Reasons over the Workspace and Chronicle.

Lantern SHALL NEVER preserve history.

## KoR

Produces observations only.

## Humans

Humans alone preserve institutional memory.

---

# 12. Conformance

A conforming implementation:

- Implements the Chronicle lifecycle.
- Produces deterministic canonical hashes.
- Preserves Scroll immutability after commit.
- Stores the Chronicle within its owning scope according to the corresponding Ilpresim specification.
- Does not require a database.
- Never rewrites committed history.

---

# Guiding Principle

Artifacts preserve objects.

The Chronicle preserves institutional memory.

Knowledge grows through intentional preservation, never through rewriting history.
