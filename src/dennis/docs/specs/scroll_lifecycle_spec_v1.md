# Scroll Lifecycle Specification

**Version:** 1.0 (Draft)
**Status:** Working Draft
**Protocol:** Chronicle Protocol v1.0

---

# 1. Purpose

This specification defines the lifecycle of a Scroll.

A lifecycle describes the valid states of a Scroll, the permitted transitions between those states, and the invariants that implementations SHALL preserve.

The lifecycle is independent from the meaning, ownership, or storage of a Scroll.

---

# 2. Scope

This specification applies only to individual Scrolls.

It does not define:

- Chronicle ownership
- Workspace behavior
- DEX serialization
- Artifact lineage
- Project lineage

Those are defined by their respective Ilpresim specifications.

---

# 3. Design Principles

The Scroll lifecycle follows the principles of the Chronicle Protocol:

- History begins only when humans intentionally preserve it.
- A Scroll SHALL become immutable once committed.
- Institutional memory SHALL never be rewritten.
- Reasoning SHALL be preserved, including unsuccessful reasoning.
- Abandoned investigations remain valuable institutional knowledge.

---

# 4. Lifecycle States

Version 1 defines two lifecycle states.

## WORKING

A Working Scroll is mutable.

It represents reasoning that has not yet become institutional memory.

Working Scrolls exist only while humans are actively developing knowledge.

---

## COMMITTED

A Committed Scroll is immutable.

It represents preserved institutional memory.

Once committed, a Scroll SHALL never return to the WORKING state.

---

# 5. State Machine

```
Create Scroll
      │
      ▼
+-------------+
|  WORKING    |
+-------------+
      │
      │ Commit
      ▼
+-------------+
| COMMITTED   |
+-------------+
```

The transition from WORKING to COMMITTED is irreversible.

No additional lifecycle transitions are defined by Version 1.

---

# 6. Allowed Operations

## WORKING

Implementations MAY permit unrestricted modification of:

- title
- annotations
- evidence
- relationships
- outcome
- authors
- metadata

The protocol intentionally imposes no restrictions while a Scroll remains in the WORKING state.

---

## COMMITTED

No canonical field SHALL be modified after commitment.

Committed Scrolls MAY only be:

- read
- verified
- referenced
- signed (when supported by the implementation)

---

# 7. Evolution

Additional reasoning SHALL never modify an existing committed Scroll.

Instead:

1. A new Working Scroll SHALL be created.
2. The new Scroll MAY reference previous Scrolls.
3. The previous Scroll SHALL remain unchanged.

Institutional memory grows through addition.

It never grows through modification.

---

# 8. Lifecycle and Outcome

Lifecycle and Outcome are orthogonal concepts.

Lifecycle answers:

> Can this Scroll still change?

Outcome answers:

> What conclusion did this Scroll preserve?

Possible outcomes include:

- approval
- rejection
- investigation
- observation
- inactive
- cancelled
- superseded
- no_conclusion

Changing the Outcome SHALL NOT affect the Lifecycle.

---

# 9. Protocol Invariants

Every implementation SHALL preserve the following invariants.

- Every committed Scroll originated as a Working Scroll.
- Every committed Scroll has exactly one canonical hash.
- Every committed Scroll is immutable.
- Committed Scrolls SHALL never be deleted.
- Institutional memory SHALL never be rewritten.
- Reasoning SHALL be preserved regardless of outcome.

---

# 10. Relationship to Other Specifications

This specification intentionally does not define:

- Chronicle ownership
- Workspace projections
- Artifact lineage
- Chronicle lineage
- DEX packaging

Those concerns belong to independent specifications of the Ilpresim Universe.

---

# Guiding Principle

A Scroll preserves reasoning.

The Chronicle preserves institutional memory.

History grows by preserving knowledge, never by rewriting it.