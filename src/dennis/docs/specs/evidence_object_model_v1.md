# Evidence Object Model

**Version:** 1.0
**Status:** Proposed Standard
**Protocol:** Chronicle Protocol v1.0

---

# 1. Purpose

This specification defines the canonical logical representation of an Evidence Reference.

Evidence provides supporting material for preserved reasoning without duplicating the referenced information.

---

# 2. Scope

This specification defines:

- Evidence structure
- Evidence ownership
- Protocol invariants

This specification intentionally does NOT define:

- storage mechanisms
- serialization
- database representation
- file formats
- transport protocols

Those concerns belong to independent Ilpresim specifications.

---

# 3. Definition

Evidence is a reference to supporting material intentionally associated with a Scroll.

Evidence SHALL preserve the existence of supporting material rather than duplicate the supporting material itself.

---

# 4. Object Model

Every Evidence Reference consists of three logical sections.

```
Evidence

├── Locator
├── Metadata
└── Description
```

---

# 5. Locator

The Locator uniquely identifies the referenced material.

The protocol intentionally does not define the locator format.

Possible implementations include:

- relative artifact paths
- canonical hashes
- URIs
- protocol-defined identifiers

Future protocol revisions MAY define additional locator schemes.

---

# 6. Metadata

Metadata SHALL contain:

- author
- created_at

Metadata records the intentional inclusion of the evidence.

---

# 7. Description

Description contains optional human-readable context explaining why the evidence is relevant.

Description SHALL NOT replace the referenced evidence.

---

# 8. Ownership

Evidence SHALL belong to exactly one Scroll.

Evidence SHALL NOT exist independently.

Evidence participates in the canonical representation of its enclosing Scroll.

---

# 9. Lifecycle

Evidence inherits the lifecycle of its enclosing Scroll.

While the enclosing Scroll remains WORKING:

- evidence MAY be added
- evidence MAY be modified
- evidence MAY be removed

Once the enclosing Scroll becomes COMMITTED:

- evidence SHALL become immutable.

---

# 10. Canonical Participation

The following fields participate in canonical hashing:

- locator
- metadata
- description

Evidence SHALL NOT possess an independent canonical identity.

Evidence SHALL NOT possess an independent canonical hash.

---

# 11. Protocol Invariants

Every Evidence Reference SHALL satisfy the following invariants.

- Evidence belongs to exactly one Scroll.
- Evidence has no independent lifecycle.
- Evidence has no independent canonical identity.
- Evidence references supporting material rather than duplicating it.
- Evidence participates in the canonical hash of its enclosing Scroll.

---

# Guiding Principle

Evidence preserves traceability.

The Chronicle preserves reasoning.

Supporting material remains referenced rather than replicated.