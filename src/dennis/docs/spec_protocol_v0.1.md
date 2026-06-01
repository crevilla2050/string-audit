# SPEC_PROTOCOL_v0.1

## Status

Draft

## Purpose

Define the canonical representation of intent within Dennis.
A Spec describes what transformation is desired.
A Spec does not describe implementation details.
A Spec does not describe executable operations.
A Spec represents human intent.

---

# Core Principle

Goals describe WHY.
Specs describe DESIRED OUTCOME.
Plans describe HOW.
DEX artifacts describe EXECUTABLE INTENT.

---

# Processing Pipeline

Semantic Objects

```
↓
```

Goal Discovery

```
↓
```

Goal

```
↓
```

Spec

```
↓
```

Plan

```
↓
```

DEX

---

# Design Philosophy

A Spec should be understandable by:

* Humans
* Goal Discovery engines
* Future AI providers
* User interfaces

without requiring knowledge of implementation details.

---

# Responsibilities

A Spec MAY:

* define goals
* define scope
* define constraints
* define desired outcomes
* define review notes

A Spec MUST NOT:

* modify files
* contain executable operations
* contain line numbers
* contain implementation-specific instructions
* contain DEX metadata

---

# Canonical Structure

{
"version": 1,
"goal": "INTERNATIONALIZE_STRINGS"
}

---

# Recommended Structure

{
"version": 1,
"goal": "INTERNATIONALIZE_STRINGS",
"scope": {},
"constraints": {},
"notes": []
}

---

# Required Fields

version

Protocol version.

---

goal

Canonical Goal Registry identifier.

Example:

INTERNATIONALIZE_STRINGS

---

# Optional Fields

scope

Limits where the goal applies.

Example:

{
"paths": [
"src/"
]
}

---

constraints

Additional restrictions.

Example:

{
"preserve_behavior": true
}

---

notes

Human-readable comments.

Example:

[
"Generated from Goal Discovery."
]

Notes are advisory.

Dennis Core MUST NOT depend on them.

---

# Examples

## Internationalization

{
"version": 1,
"goal": "INTERNATIONALIZE_STRINGS"
}

---

## Introduce Helper

{
"version": 1,
"goal": "INTRODUCE_HELPER"
}

---

## Remove Dead Code

{
"version": 1,
"goal": "REMOVE_DEAD_CODE"
}

---

# Human Workflow

Human-created Spec

↓

Review

↓

Plan Generation

↓

DEX

---

# AI Workflow

Semantic Objects

↓

AI Goal Discovery

↓

Generated Spec

↓

Human Review

↓

Plan Generation

↓

DEX

---

# Protocol Invariants

Specs describe desired outcomes.

Specs do not describe implementation.

Specs are advisory.

Plans remain authoritative.

# Reserved Words

Internationalization:

INTERNATIONALIZE_STRINGS
ADD_LANGUAGE_CATALOG
REMOVE_LANGUAGE_CATALOG

Refactoring:

EXTRACT_CONSTANTS
EXTRACT_FUNCTION
EXTRACT_MODULE
RENAME_SYMBOL
REPLACE_DEPRECATED_API

Cleanup:

REMOVE_DEAD_CODE
REMOVE_DUPLICATES
REMOVE_UNUSED_IMPORTS
NORMALIZE_FORMATTING

Helpers:

INTRODUCE_HELPER
UPDATE_HELPER
REMOVE_HELPER

Documentation:

ADD_DOCUMENTATION
UPDATE_DOCUMENTATION
SYNCHRONIZE_DOCUMENTATION

Security:

REMOVE_SECRET
EXTERNALIZE_SECRET
HARDEN_SECURITY
ROTATE_KEYS

Configuration:

ADD_CONFIGURATION
UPDATE_CONFIGURATION
REMOVE_CONFIGURATION

Data:

ADD_SCHEMA_FIELD
MODIFY_SCHEMA_FIELD
REMOVE_SCHEMA_FIELD
MIGRATE_DATA_STRUCTURE

Protocol:
These are Dennis-specific.

EMBED_INTENT
VERIFY_EXECUTION
ESTABLISH_LINEAGE
REHYDRATE_ARTIFACT

Meta:

UNKNOWN
MULTIPLE_GOALS
MANUAL_REVIEW_REQUIRED

---

* Reserved Words are protocol identifiers.
* Reserved Words MUST remain stable once published.
* Deprecated words may be retired, but should never be repurposed.

# Non-Goals

Specs are not:

* plans
* patches
* diffs
* DEX artifacts
* executable instructions

---

# Future Compatibility

Future versions may introduce:

* multiple goals
* priorities
* dependencies
* policy rules

Consumers MUST ignore unknown fields.

---

# Design Motto

Intent first.

Implementation later.
