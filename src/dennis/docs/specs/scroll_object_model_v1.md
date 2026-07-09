# Scroll Object Model

**Version:** 1.0
**Status:** Proposed Standard
**Protocol:** Chronicle Protocol v1.0

---

# 1. Purpose

This specification defines the canonical logical representation of a Scroll.

It defines the conceptual object model independently of any programming language, serialization format, database technology, or user interface.

Implementations SHALL conform to this object model regardless of internal implementation details.

---

# 2. Scope

This specification defines:

- Scroll identity
- Scroll structure
- Canonical sections
- Object responsibilities
- Protocol invariants

This specification intentionally does NOT define:

- JSON serialization
- Python implementation
- Database schemas
- User interface behavior
- Workspace behavior
- DEX packaging
- Chronicle ownership

Those concerns are defined by independent specifications of the Ilpresim Universe.

---

# 3. Definition

A Scroll is the atomic unit of institutional memory.

A Scroll preserves one coherent reasoning process that concludes with one intentional outcome.

Once committed, a Scroll becomes immutable.

A Scroll is intentionally self-contained but intentionally not self-sufficient. It preserves institutional reasoning while relying on other Ilpresim protocols to define ownership, packaging, lineage, collaboration, and presentation.

---

# 4. Object Model

Every Scroll consists of four canonical sections.

```
Scroll

├── Identity
├── Header
├── Body
└── Authentication
```

No additional section SHALL participate in canonical hashing unless defined by a future protocol revision.

---

# 5. Identity

Identity uniquely identifies a Scroll.

## Temporary Identity

A Temporary Identity exists while a Scroll remains in the WORKING state.

Properties:

- implementation-defined
- mutable
- non-canonical
- never preserved

Temporary identities exist solely to support editing before commitment.

---

## Canonical Identity

A Canonical Identity is assigned during commitment.

Properties:

- deterministic
- immutable
- globally unique
- derived from canonical content

The Canonical Identity SHALL remain unchanged for the lifetime of the Scroll.

---

# 6. Header

The Header contains metadata describing the preserved reasoning.

The Header SHALL contain:

- title
- outcome
- authors
- created_at
- committed_at

Future protocol revisions MAY extend the Header.

Committed Header fields SHALL remain immutable.

---

# 7. Body

The Body preserves the reasoning itself.

The Body SHALL contain:

- annotations
- evidence
- relationships

The protocol intentionally keeps the Body minimal.

Objects unrelated to preserved reasoning SHALL NOT become part of the Body.

---

# 8. Authentication

Authentication preserves proof of authenticity.

The Authentication section SHALL contain:

- signatures

Future protocol revisions MAY define additional authentication mechanisms.

---

# 9. Canonical Surface

The Canonical Surface of a Scroll is defined as:

```
Identity
+
Header
+
Body
+
Authentication
```

Only the Canonical Surface participates in canonical hashing.

Objects outside the Canonical Surface SHALL NOT affect Scroll identity.

---

# 10. Extension Points

Future protocol revisions MAY extend the Scroll Object Model.

Extensions SHALL:

- preserve backward compatibility
- preserve deterministic hashing
- preserve canonical identity

Version 1 implementations SHALL ignore unknown extension sections unless explicitly required by a future protocol revision.

---

# 11. Protocol Invariants

Every Scroll SHALL satisfy the following invariants.

- A Scroll preserves reasoning rather than implementation details.
- A Scroll is intentionally minimal.
- A Scroll owns no Workspace information.
- A Scroll owns no Project information.
- A Scroll owns no DEX packaging information.
- A Scroll owns no collaboration metadata.
- A Scroll owns no AI-generated reasoning.
- A Scroll SHALL become immutable after commitment.

---

# Guiding Principle

A Scroll preserves one intentional unit of institutional reasoning.

Everything that is not required to preserve that reasoning belongs outside the Scroll and MAY be referenced by other Ilpresim specifications.