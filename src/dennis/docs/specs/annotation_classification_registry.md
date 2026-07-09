# Annotation Classification Registry

**Version:** 1.0
**Status:** Proposed Standard
**Protocol:** Chronicle Protocol v1.0

---

# 1. Purpose

This specification defines the canonical semantic classification registry for Annotations.

The registry provides deterministic classification values that implementations SHALL use when preserving Annotation semantics.

The registry is independent from serialization, programming language, database technology, and user interface.

---

# 2. Design Principles

Annotation classifications SHALL:

- preserve semantic meaning
- remain deterministic
- be implementation independent
- support efficient querying
- support multiple simultaneous classifications
- remain backward compatible

Classification values are protocol data.

They SHALL participate in canonical hashing.

---

# 3. Representation

Classifications are represented as a binary bitmap.

Each bit represents one semantic classification.

Multiple classifications MAY coexist within a single Annotation.

Example:

```
QUESTION | WARNING
```

or

```
RATIONALE | DECISION
```

---

# 4. Version 1 Registry

| Bit | Hex | Name | Description |
|----:|----:|------|-------------|
| 0 | 0x00000001 | QUESTION | Raises an unresolved question. |
| 1 | 0x00000002 | RATIONALE | Explains why a decision exists. |
| 2 | 0x00000004 | DECISION | Records an intentional decision. |
| 3 | 0x00000008 | WARNING | Identifies risk or caution. |
| 4 | 0x00000010 | REFERENCE | Refers to supporting material. |
| 5 | 0x00000020 | TODO | Identifies future work. |
| 6 | 0x00000040 | OBSERVATION | Records a factual observation. |

Additional values SHALL be assigned only by future revisions of this registry.

---

# 5. Combination Rules

Annotations MAY combine any number of classifications.

Examples:

QUESTION + TODO

RATIONALE + DECISION

REFERENCE + OBSERVATION

The protocol intentionally imposes no restrictions on valid combinations.

---

# 6. Unknown Classifications

Implementations SHALL preserve unknown classification bits.

Implementations MAY ignore unknown bits for presentation.

Unknown bits SHALL NOT invalidate an Annotation.

---

# 7. Registry Evolution

Future registry revisions SHALL:

- preserve existing numeric assignments
- never reuse assigned bits
- only allocate previously unused bits

Existing semantic meanings SHALL never change.

---

# 8. Protocol Invariants

Every registry implementation SHALL preserve the following invariants.

- Classification values are immutable once assigned.
- Numeric assignments SHALL never be recycled.
- Multiple classifications MAY coexist.
- Classifications preserve semantics rather than presentation.
- Unknown classifications SHALL remain preservable.

---

# Guiding Principle

An Annotation describes reasoning.

Its classifications describe the semantic nature of that reasoning.

Meaning is preserved through stable semantic identifiers rather than presentation.