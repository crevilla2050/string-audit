# Dennis Doctrine: `.dexproject`

Status: Conceptual Doctrine (Frozen for Future Evaluation)

## Overview

A `.dexproject` is a higher-order DEX artifact.

Just as a DEX artifact describes the deterministic evolution of files, a `.dexproject` describes the deterministic evolution of a project.

A project is therefore treated as a first-class artifact.

The `.dexproject` format does not replace DEX artifacts. It composes them.

---

## Core Principle

A project is an artifact composed of artifacts.

The relationship is recursive:

File
→ Artifact (.dex)

Artifact
→ Project Artifact (.dexproject)

Future higher-order compositions may follow the same principle.

No new philosophy is introduced.

The existing DEX philosophy is extended.

---

## Purpose

A `.dexproject` exists to answer:

* What belongs to this project?
* What artifacts define it?
* What assets support it?
* What dependencies are required?
* What environment is expected?
* What lineage does the project have?
* Can the project be rehydrated?

---

## Non-Goals

A `.dexproject` is NOT:

* A task manager
* A Jira replacement
* A ticket system
* A source-control replacement
* A cloud storage service

Dennis remains artifact-centric.

---

## Canonical Properties

A `.dexproject` should remain:

* Deterministic
* Human-readable
* Inspectable
* Portable
* Offline-capable
* Rehydratable
* Signable
* Verifiable

These properties are inherited from DEX.

---

## Example Contents

A project may contain:

* DEX artifacts
* Images
* Documentation
* PDFs
* Configuration files
* Build instructions
* Environment metadata
* Binary assets
* External references

All entries should be declarative and inspectable.

---

## Inspection

The command:

```
dennis project inspect project.dexproject
```

must provide a complete narrative of the project.

The goal is understanding.

Inspection should answer:

* What is this?
* What does it contain?
* Who created it?
* What artifacts define it?
* What assets support it?
* Can it be trusted?
* Can it be restored?

---

## Rehydration

A project should be restorable without requiring tribal knowledge.

The ideal outcome is:

New Developer
↓
Downloads Project
↓
Inspects Project
↓
Rehydrates Project
↓
Begins Work

without requiring undocumented knowledge from other team members.

---

## Dennis-on-Dennis Test

A future milestone shall be:

Can Dennis represent itself as a `.dexproject`?

Success criteria:

* Dennis artifacts represented inside the project
* Dennis assets represented inside the project
* Dennis documentation represented inside the project
* Dennis environment represented inside the project
* Project inspection succeeds
* Project verification succeeds
* Project rehydration succeeds

This is considered a high-value architectural validation.

---

## Relationship to `.dexscope`

`.dexscope` answers:

"What belongs to this artifact?"

`.dexproject` answers:

"What belongs to this project?"

The concepts are intentionally parallel.

---

## Project Integrity

Every referenced element SHOULD have
a deterministic hash.

Dennis MUST be able to detect drift
between the project definition and
the current filesystem state.

---

## Manifest Principle

A .dexproject references artifacts.

A .dexproject does not embed artifacts.

Artifacts remain first-class entities
with their own hashes, signatures,
lineage and inspection workflows.

---

## Long-Term Vision

A `.dexproject` becomes a portable project capsule.

Its purpose is to preserve:

* Artifacts
* Assets
* Environment
* Lineage
* Context
* Project continuity

Projects should survive personnel changes, organizational changes, and time.

The ultimate objective is reproducible project knowledge.
