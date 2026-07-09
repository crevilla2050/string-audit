# Annotation Object Model

**Version:** 1.0
**Status:** Proposed Standard
**Protocol:** Chronicle Protocol v1.0

---

# 1. Purpose

This specification defines the canonical logical representation of an Annotation.

Annotations preserve intentionally recorded human reasoning that contributes to the institutional memory of a Scroll.

Annotations SHALL exist only as part of a Scroll.

---

# 2. Scope

This specification defines:

- Annotation structure
- Annotation classification
- Object responsibilities
- Protocol invariants

This specification intentionally does NOT define:

- serialization
- database schemas
- editing interfaces
- collaboration systems
- comment systems

Those concerns belong to independent Ilpresim specifications.

---

# 3. Definition

An Annotation is a human-authored unit of preserved reasoning.

Annotations provide contextual knowledge that humans intentionally decide to preserve as part of a Scroll.

Annotations are canonical content.

---

# 4. Object Model

Every Annotation consists of three logical sections.

```
Annotation

├── Identity
├── Metadata
└── Content
```

---

# 5. Identity

Annotations MAY possess temporary implementation-defined identifiers while a Scroll remains in the WORKING state.

Annotations SHALL NOT possess independent canonical identities.

Their canonical identity is inherited from the enclosing Scroll.

---

# 6. Metadata

Metadata SHALL contain:

- author
- created_at
- classification

The classification SHALL be represented as a binary semantic bitmap.

A single Annotation MAY possess multiple semantic classifications simultaneously.

Future protocol revisions MAY extend the classification registry without breaking backward compatibility.

---

# 7. Annotation Classification

Annotation classifications describe the semantic meaning of preserved reasoning.

Classifications are protocol data.

They are NOT presentation metadata.

Version 1 defines the classification registry independently from this specification.

Example classifications include:

```
QUESTION
RATIONALE
DECISION
WARNING
REFERENCE
TODO
OBSERVATION
```

Implementations SHALL represent classifications using the protocol-defined bitmap registry.

---

# 8. Content

The Content section SHALL contain:

- text

The protocol intentionally defines no formatting language.

Implementations MAY support Markdown or other presentation formats provided the canonical representation remains deterministic.

---

# 9. Ownership

Annotations SHALL belong to exactly one Scroll.

Annotations SHALL NOT exist independently.

Removing, modifying, or adding an Annotation modifies the canonical content of the enclosing Scroll.

---

# 10. Lifecycle

Annotations inherit the lifecycle of their enclosing Scroll.

While the enclosing Scroll remains in the WORKING state:

- annotations MAY be added
- annotations MAY be modified
- annotations MAY be removed

Once the enclosing Scroll becomes COMMITTED:

- annotations SHALL become immutable

---

# 11. Canonical Participation

Annotations participate in the canonical representation of the enclosing Scroll.

The following Annotation fields SHALL participate in canonical hashing:

- classification
- author
- created_at
- content

Annotations SHALL NOT possess independent canonical hashes.

---

# 12. Protocol Invariants

Every Annotation SHALL satisfy the following invariants.

- An Annotation belongs to exactly one Scroll.
- An Annotation has no independent lifecycle.
- An Annotation has no independent canonical identity.
- An Annotation participates in the canonical hash of its enclosing Scroll.
- Annotation classifications preserve semantics rather than presentation.
- Multiple semantic classifications MAY coexist within a single Annotation.

---

# Guiding Principle

Annotations preserve human reasoning.

Their classifications preserve the semantic meaning of that reasoning.

Together they enrich institutional memory without becoming independent institutional objects.