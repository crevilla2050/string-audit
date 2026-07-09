# Canonical Serialization

**Version:** 1.0
**Status:** Proposed Standard
**Protocol:** Chronicle Protocol v1.0

---

# 1. Purpose

This specification defines the canonical serialization rules for Chronicle Protocol objects.

Canonical serialization guarantees that equivalent protocol objects always produce identical serialized representations, regardless of implementation language or platform.

Deterministic serialization is a prerequisite for canonical hashing.

---

# 2. Scope

This specification defines:

- canonical serialization rules
- deterministic ordering
- structural completeness
- forward compatibility
- backward compatibility

This specification intentionally does NOT define:

- specific programming languages
- implementation classes
- storage engines
- transport protocols

JSON Version 1 is defined by an independent specification.

---

# 3. Design Goals

Canonical serialization SHALL:

- be deterministic
- be implementation independent
- be human-readable
- preserve protocol semantics
- produce identical serialized representations for identical protocol objects

Canonical serialization is a logical transformation rather than a presentation format.

---

# 4. Canonical Structure

Every serialized object SHALL preserve its complete logical structure.

Optional fields SHALL remain present.

When no value exists, the field SHALL contain an explicit `null` value.

Example:

```json
{
    "description": null
}
```

Omitting optional fields is NOT canonical.

---

# 5. Field Ordering

Every protocol object SHALL serialize its fields using the protocol-defined canonical order.

Implementations SHALL NOT reorder fields.

Future protocol revisions MAY define additional fields.

Existing field ordering SHALL remain stable.

---

# 6. Collection Ordering

Collections SHALL be serialized deterministically.

Implementations SHALL use protocol-defined ordering rules for every collection.

Equivalent collections SHALL always serialize identically.

---

# 7. Unknown Fields

Unknown fields SHALL be preserved whenever possible.

Implementations MAY ignore unknown fields for presentation.

Unknown fields SHALL NOT invalidate canonical serialization.

---

# 8. Versioning

Every serialized Chronicle SHALL explicitly identify the protocol version.

Version identifiers participate in canonical serialization.

---

# 9. Deterministic Encoding

Canonical serialization SHALL produce identical byte sequences for equivalent protocol objects.

Equivalent protocol objects SHALL produce identical canonical hashes.

---

# 10. Canonical Participation

Only protocol-defined canonical fields participate in canonical serialization.

Runtime state SHALL NOT participate.

Examples include:

- authentication tokens
- session identifiers
- temporary object identifiers
- implementation-specific metadata

---

# 11. Forward Compatibility

Future protocol revisions MAY introduce additional optional fields.

Version 1 implementations SHALL ignore unknown fields unless explicitly required by a future protocol revision.

---

# 12. Protocol Invariants

Every canonical serializer SHALL satisfy the following invariants.

- Serialization is deterministic.
- Field ordering is deterministic.
- Collection ordering is deterministic.
- Optional fields remain structurally present.
- Runtime state is never serialized.
- Equivalent protocol objects produce identical serialized representations.

---

# Guiding Principle

Canonical serialization preserves protocol semantics rather than implementation details.

Different implementations shall serialize the same institutional knowledge into the same canonical representation.