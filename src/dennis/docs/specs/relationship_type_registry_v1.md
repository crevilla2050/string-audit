# Relationship Type Registry

**Version:** 1.0
**Status:** Proposed Standard
**Protocol:** Chronicle Protocol v1.0

---

# 1. Purpose

This specification defines the canonical registry of relationship types used by the Chronicle Protocol.

Relationship types define the semantic meaning of the connection between two Scrolls.

The registry is independent from serialization, programming language, database technology, and visualization.

---

# 2. Design Principles

Relationship types SHALL:

- describe semantic meaning
- remain deterministic
- remain implementation independent
- remain stable over time
- preserve backward compatibility

Relationship types are protocol data.

They participate in canonical hashing.

---

# 3. Representation

Relationship types are represented by stable protocol-defined numeric identifiers.

Each Relationship SHALL possess exactly one relationship type.

Relationship types are mutually exclusive.

---

# 4. Version 1 Registry

| ID | Name | Description |
|---:|------|-------------|
| 1 | relates_to | General semantic association. |
| 2 | clarifies | Explains or clarifies another Scroll. |
| 3 | caused_by | Indicates causal dependency. |
| 4 | supersedes | Replaces an earlier Scroll while preserving history. |
| 5 | references | Cites another Scroll as supporting context. |
| 6 | derives_from | Represents intentional derivation. |
| 7 | duplicates | Indicates substantially equivalent reasoning. |

Future protocol revisions MAY extend this registry.

---

# 5. Directionality

Relationship types are directional.

For example,

```
A --clarifies--> B
```

is not equivalent to

```
B --clarifies--> A
```

Implementations SHALL preserve relationship direction.

---

# 6. Unknown Relationship Types

Implementations SHALL preserve unknown relationship identifiers.

Implementations MAY present unknown relationship types as implementation-defined labels.

Unknown types SHALL NOT invalidate a Relationship.

---

# 7. Registry Evolution

Future revisions SHALL:

- preserve existing numeric identifiers
- never reuse retired identifiers
- only allocate previously unused identifiers

Existing semantic meanings SHALL never change.

---

# 8. Protocol Invariants

Every implementation SHALL preserve the following invariants.

- Every Relationship possesses exactly one type.
- Relationship types are immutable once committed.
- Numeric identifiers SHALL never be reassigned.
- Relationship semantics SHALL remain stable across protocol versions.

---

# Guiding Principle

Relationships preserve semantic structure.

Their type expresses one intentional semantic assertion between two preserved units of institutional reasoning.