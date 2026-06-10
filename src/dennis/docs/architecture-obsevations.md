# Dennis Architecture Observation Doctrine v0.1

## Architectural Compression

Dennis should not measure architecture primarily through file size or line count.

Raw size is a symptom.

Architecture observations should attempt to explain why a file, module, or project has reached its current size.

Examples:

* Duplicate capabilities
* Repeated implementations
* Missing shared utilities
* Missing abstractions
* Dead code
* Repeated validation logic

These observations provide explanatory power that simple line-count metrics cannot.

---

## Capability First

Dennis should prefer identifying capabilities over identifying files.

Example:

```
ts()
timestamp()
now_iso()
```

may represent multiple implementations of the same capability:

```
GENERATE_TIMESTAMP
```

The architectural observation is not that the functions are duplicated.

The architectural observation is that the capability has emerged multiple times throughout the codebase.

---

## DUPLICATE_AST_CANDIDATE

Definition:

Two or more functions produce identical normalized AST signatures.

The observation is structural only.

The observation does not imply:

* semantic equivalence
* safe consolidation
* automatic refactoring

It only indicates that multiple implementations share identical structure.

---

## Malkovich Principle

A duplicate implementation is not automatically a defect.

When duplicate structures are discovered, Dennis should ask:

```
Why does this duplicate exist?
```

Possible classifications include:

### REAL_DUPLICATE

Same capability.
Same implementation.
Likely candidate for consolidation.

Examples:

```
ts()
timestamp()
```

### INTERFACE_CONFORMANCE

Duplicate implementations required by adapter or interface design.

Examples:

```
execute()
commit()
rollback()
```

across multiple storage backends.

### ABSTRACT_PLACEHOLDER

Structural duplication caused by intentionally empty or abstract methods.

Examples:

```
raise NotImplementedError()
```

methods.

### UNKNOWN

Classification has not yet been determined.

---

## Architectural Compression Metric

Future Dennis versions may estimate architectural compression opportunities.

Example:

```
Capability:
    GENERATE_TIMESTAMP

Instances:
    9

Lines per implementation:
    6

Potential reduction:
    48 lines
```

This metric should be reported as evidence.

It must not be interpreted as an automatic recommendation.

Human review remains authoritative.

---

## Oversized Modules

OVERSIZED_MODULE should be considered a symptom-level observation.

Preferred workflow:

```
DUPLICATE_AST_CANDIDATE
    ↓
Capability Classification
    ↓
Architectural Compression Estimate
    ↓
OVERSIZED_MODULE Explanation
```

Dennis should strive to explain size rather than merely report size.

---

## Dennis-on-Dennis Requirement

Dennis must be capable of analyzing itself.

The canonical validation example is the timestamp capability colony:

```
ts()
timestamp()
```

implemented in multiple locations.

The detector must be able to discover these implementations without AI assistance.

---

## Future Language Independence

Architecture observations should not be inherently tied to Python ASTs.

Language-specific parsers should be treated as adapters that emit architectural evidence.

Future implementations may support:

* Python
* Gambas3
* PHP
* JavaScript
* Other languages

while preserving the same architecture observation model.

The observation engine should remain language-agnostic whenever possible.

---

## Core Principle

Dennis should not ask:

```
What code is duplicated?
```

Dennis should ask:

```
What idea appeared multiple times?
```

The duplicate code is evidence.

The repeated idea is the architectural observation.
============================================================

# Architecture Observation v0.2 Direction

## Principle

Dennis should prefer observations that explain architectural pressure rather than observations that merely report symptoms.

Example:

```
OVERSIZED_MODULE
```

is a symptom.

It indicates that architectural pressure may exist, but does not explain why.

Example:

```
DUPLICATE_AST_CANDIDATE
```

provides evidence that may explain architectural pressure.

Dennis should therefore prioritize evidence-producing observations before symptom-producing observations whenever possible.

---

## ARCHITECTURE.DUPLICATE_AST_CANDIDATE

Description:

Two functions exhibit identical or highly similar Abstract Syntax Tree (AST) structure.

This observation identifies structural duplication.

It does not imply semantic equivalence.

It does not imply that one implementation should be removed.

It only states that the implementations appear structurally similar.

---

## Evidence

Required evidence:

```
symbol_a
symbol_b

file_a
file_b

similarity
```

Optional future evidence:

```
ast_hash
normalized_ast
shared_calls
shared_dependencies
```

---

## Confidence

v0.1:

```
Exact normalized AST match:
    confidence = 1.0
```

Future versions:

```
Similarity score derived from
normalized AST comparison.
```

---

## Detection Strategy v0.1

1. Parse Python source using ast.
2. Collect FunctionDef nodes.
3. Normalize AST:

   * remove function name
   * remove line numbers
   * remove column offsets
4. Generate canonical AST representation.
5. Compare canonical AST structures.
6. Emit observation when structures match.

---

## Dennis-on-Dennis Objective

The first Dennis-on-Dennis target is:

```
ts()
```

and

```
timestamp()
```

These functions intentionally remain unresolved.

They serve as architectural test data for future architecture observations.

---

## Future Evolution

Potential future observations:

```
ARCHITECTURE.SHARED_CAPABILITY_CANDIDATE
```

This observation would be derived from multiple
DUPLICATE_AST_CANDIDATE observations and other evidence.

Example:

```
ts()
timestamp()
timestamp_iso()
```

might all contribute evidence for:

```
GENERATE_TIMESTAMP
```

without requiring AI.

---

## Relationship To OVERSIZED_MODULE

OVERSIZED_MODULE remains a valid observation.

However, it is considered a symptom-level observation.

Future Dennis versions should attempt to explain oversized modules through lower-level evidence such as:

```
DUPLICATE_AST_CANDIDATE
SHARED_CAPABILITY_CANDIDATE
DEAD_FILE_CANDIDATE
```

before recommending structural changes.

Observation:
    ARCHITECTURE.DUPLICATE_AST_CANDIDATE

Candidate Goal:
    CONSOLIDATE_SHARED_CAPABILITY

Description:
    Multiple implementations of the same
    capability were detected through AST
    normalization and structural matching.

Evidence:
    Duplicate function groups.


# Dennis Doctrine: Observation vs Evidence Separation

## Motivation

Current architecture observations embed evidence directly inside observation records.

This is convenient for debugging and early development, but couples metadata and payload into a single structure.

As observation volume grows, this approach creates:

* Large observation files
* Repeated evidence payloads
* Reduced reuse of identical evidence
* Increased storage and transmission costs
* Tighter coupling between findings and supporting data

## Principle

Observations and evidence are distinct concepts.

An observation answers:

```
What did Dennis observe?
```

Evidence answers:

```
Why does Dennis believe it?
```

These concerns should be represented separately.

## Proposed Direction

### Observation Index

Contains lightweight findings and references to evidence.

Example:

{
"finding_id": "finding-001",

"type":
"ARCHITECTURE.DUPLICATE_AST_CANDIDATE",

"evidence_hash":
"69af1cf7...",

"classification":
"UNKNOWN_DUPLICATION",

"confidence":
1.0
}

### Evidence Store

Contains heavyweight supporting data.

Example:

{
"69af1cf7...": {

```
"functions": [...],

"source_excerpt": [...],

"metrics": {...}
```

}
}

## Benefits

* Observation files remain small
* Evidence can be reused
* Evidence can be deduplicated
* UI can lazy-load details
* Forge can index findings efficiently
* Future evidence types become possible without changing observation structures

## Architectural Rule

Observations reference evidence.

Observations do not own evidence.

## Future Possibilities

Evidence stores may eventually contain:

* Source code excerpts
* AST representations
* Diff payloads
* Metrics
* Screenshots
* Dependency graphs
* Binary artifacts
* Media lineage records

without requiring changes to the observation schema.

## Dennis Principle

Observation describes the finding.

Evidence proves the finding.

They are related, but they are not the same artifact.
