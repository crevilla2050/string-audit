# Dennis Diff Specification — v1.0

## Status

Canonical — Unobtanium Freeze Candidate

---

## 1. Purpose

This document defines the canonical representation, generation, normalization, and identity rules for diffs in the Dennis system.

The goal is to ensure:

* Deterministic representation of change
* Cross-environment reproducibility
* Compatibility with DEX artifacts
* Verifiable transformation lineage

---

## 2. Core Principle

> Dennis does not compute diffs.
> Dennis expresses state transitions deterministically.

---

## 3. State Model

Dennis operates on three explicit states:

```
S₀ = Original State (baseline)
S₁ = Planned State (DEX plan)
S₂ = Actual State (observed result)
```

Transitions:

```
Δ₀₁ = Planned Diff      (S₀ → S₁)
Δ₀₂ = Observed Diff     (S₀ → S₂)
Δ₁₂ = Reconciliation    (S₁ → S₂)
```

---

## 4. Diff Schema (`dennis.diff.v1`)

```json
{
  "type": "dennis.diff.v1",
  "payload": {
    "files": [
      {
        "path": "string",
        "status": "added | removed | modified",
        "changes": [
          {
            "type": "insert | delete | replace",
            "start_line": number,
            "end_line": number,
            "before": ["string"],
            "after": ["string"]
          }
        ]
      }
    ]
  }
}
```

---

## 5. Canonical vs View Layer

### 5.1 Canonical Layer (MANDATORY)

* Lossless
* Identity-defining
* Used for hashing and DEX packaging
* MUST NOT remove or alter content

### 5.2 View Layer (OPTIONAL)

* User-defined filtering
* May:

  * trim whitespace
  * hide zero-impact changes
* MUST NOT affect canonical identity

---

## 6. Lossless Canonicalization Rules

Canonical diffs MUST preserve content exactly.

### Rules:

1. Lines are stored as sequences of Unicode code points
2. No trimming or modification inside lines
3. Whitespace MUST be preserved:

   * trailing spaces
   * tabs
   * non-breaking spaces
4. Empty lines MUST be preserved
5. Line ordering MUST be preserved

### Unicode Normalization

* MUST use **NFC normalization**
* This is part of canonical identity

---

## 7. Canonical JSON Serialization

Canonical JSON MUST follow:

* UTF-8 encoding
* No BOM
* Keys sorted lexicographically
* Arrays preserve order (DO NOT SORT)
* No optional fields omitted
* Empty arrays MUST be explicit
* No trailing commas
* No pretty-print formatting
* Separators MUST be: `(",", ":")`

### Numeric Constraints

* Only integers allowed
* No floats
* No NaN / Infinity

---

## 8. Block Determinism

### Definition

A block is a maximal contiguous sequence of changed lines.

### Rules

* Adjacent changes MUST be merged into a single block
* No two blocks may be contiguous
* Blocks MUST be separated by unchanged lines
* Block construction MUST NOT depend on git heuristics

---

## 9. Minimal Invariant

Canonical diffs MUST be structurally minimal.

### MUST remove:

* Empty changes (`before == []` AND `after == []`)
* Redundant structural entries

### MUST NOT remove:

* Zero-impact changes (`before == after`)

---

## 10. Diff Identity

### Definition

```
diff_hash = sha256(canonical_json(diff))
```

### Rules

* Hash is computed ONLY from canonical layer
* `"type"` field MUST be included
* Ordering is part of identity
* Hash MUST be stable across environments

---

## 11. Matching Rules (Reconciliation)

Two changes match if:

1. Same file path
2. Identical `before` content
3. Identical `after` content

### Additional Rules

* Line numbers are NOT identity
* Line numbers are metadata only

### Duplicate Handling

* Matching MUST be stable
* First unmatched planned → first unmatched observed

---

## 12. Determinism Guarantees

The system MUST satisfy:

```
normalize(normalize(x)) == normalize(x)
```

AND

```
normalize(x₁) == normalize(x₂)
```

Where:

* x₁ and x₂ represent equivalent transformations

### Required equivalence cases:

* git diff vs directory diff
* reordered file traversal
* context vs no-context diffs

---

## 13. Ordering Rules

* Files MUST be sorted by path
* Changes MUST be ordered deterministically
* Ordering is part of identity

---

## 14. Diff as First-Class Artifact

Diffs are identity-bearing objects.

They:

* Have canonical representation
* Have hash identity
* Can be packaged as DEX
* Participate in lineage tracking

---

## 15. Known Limitations (v1)

* Matching is syntactic, not semantic
* No rename detection
* No move detection
* Line-based only (no token/AST awareness)
* No partial similarity scoring

---

## 16. Versioning Rules

* Schema version is part of identity
* `"type": "dennis.diff.v1"` MUST be preserved
* Future versions MUST NOT reinterpret v1 fields
* Breaking changes require new type

---

## 17. Non-Goals (v1)

* Semantic diffing
* AI-assisted inference
* Language-specific parsing

---

## 18. Final Principle

> Dennis does not guess.
> Dennis explains.
> Dennis verifies.

---
