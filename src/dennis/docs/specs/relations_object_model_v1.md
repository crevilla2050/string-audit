# Relationship Object Model

**Version:** 1.0
**Status:** Proposed Standard
**Protocol:** Chronicle Protocol v1.0

---

# 1. Purpose

This specification defines the canonical logical representation of a Relationship.

Relationships preserve intentional semantic connections between Scrolls.

Relationships provide the structural graph from which institutional knowledge may be navigated, analyzed, and reasoned about.

---

# 2. Scope

This specification defines:

- Relationship structure
- Relationship semantics
- Relationship ownership
- Protocol invariants

This specification intentionally does NOT define:

- serialization
- graph algorithms
- visualization
- graph traversal
- database representation
- Workspace projections

Those concerns belong to independent Ilpresim specifications.

---

# 3. Definition

A Relationship is a semantic assertion connecting one Scroll to another.

Relationships describe how preserved reasoning relates to other preserved reasoning.

Relationships are canonical content.

---

# 4. Object Model

Every Relationship consists of four logical sections.

```
Relationship

├── Source
├── Target
├── Type
└── Metadata
```

Relationships intentionally possess no independent identity.

Their meaning is completely defined by their constituent fields.

---

# 5. Source

The Source identifies the originating Scroll.

Every Relationship SHALL reference exactly one source Scroll.

---

# 6. Target

The Target identifies the destination Scroll.

Every Relationship SHALL reference exactly one target Scroll.

---

# 7. Type

The Type defines the semantic meaning of the relationship.

Relationship types SHALL be defined by the Relationship Type Registry.

Examples include:

- relates_to
- clarifies
- supersedes
- caused_by
- references

Future protocol revisions MAY extend the registry.

---

# 8. Metadata

Relationship metadata SHALL contain:

- author
- created_at

Metadata records the intentional creation of the relationship.

Relationship metadata participates in the canonical representation of the enclosing Scroll.

---

# 9. Directionality

Relationships are directional.

```
A ----clarifies----> B
```

is not equivalent to

```
B ----clarifies----> A
```

Implementations SHALL preserve relationship direction.

---

# 10. Ownership

Relationships SHALL belong to exactly one Scroll.

Relationships SHALL NOT exist independently.

Relationships SHALL participate in the canonical content of the enclosing Scroll.

---

# 11. Lifecycle

Relationships inherit the lifecycle of their enclosing Scroll.

While the enclosing Scroll remains WORKING:

- relationships MAY be created
- relationships MAY be modified
- relationships MAY be removed

Once the enclosing Scroll becomes COMMITTED:

- relationships SHALL become immutable

---

# 12. Canonical Participation

Relationships participate in the canonical representation of the enclosing Scroll.

The following fields SHALL participate in canonical hashing:

- source
- target
- type
- metadata

Relationships SHALL NOT possess independent canonical hashes.

---

# 13. Protocol Invariants

Every Relationship SHALL satisfy the following invariants.

- A Relationship connects exactly two Scrolls.
- A Relationship is directional.
- A Relationship possesses no independent identity.
- A Relationship has no independent lifecycle.
- A Relationship participates in the canonical hash of the enclosing Scroll.
- A Relationship preserves semantic structure rather than reasoning.

---

# Guiding Principle

Annotations preserve reasoning.

Relationships preserve structure.

Together they transform preserved knowledge into an explorable institutional graph.