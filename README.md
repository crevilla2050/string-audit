# Dennis the Forge 🪓

Deterministic transformation engine and DEX artifact system.

**Status:** Active development
**License:** MIT
**Python:** 3.10+
**CLI:** `dennis`

---

Dennis is a **deterministic transformation platform** that turns code changes into **portable, inspectable, and verifiable artifacts (DEX)**.

Plans are reviewable.
Artifacts are inspectable.
Transformations are reversible.

**No magic. Just steel.**

---

## 🔥 What Makes Dennis Different

Most tools extract.

Dennis **decides**.

Before any transformation is created, Dennis evaluates:

* what is meaningful
* what is noise
* what should be transformed

This **decision layer (Clean Engine)** ensures that transformations are built on **signal, not garbage**.

> Deterministic input → deterministic output
> Garbage input → deterministic garbage

Dennis avoids both.

---

## ⚙️ The Pipeline

```text id="pipe1"
scan → decide → plan → pack → sign → inspect → rehydrate → apply → invert
```

Every step is explicit. Every step is inspectable.

---

## 📦 What is a DEX Artifact?

A DEX artifact is a portable package describing a transformation.

```text id="dex1"
DEX
├── manifest.json
├── payload/
│   └── plan.json
└── signatures/
```

It contains everything needed to reproduce a transformation deterministically.

---

## 🔐 Determinism + Lineage

Dennis guarantees:

### Determinism

Same input → same plan → same artifact → same output

### Lineage (Forensic Traceability)

Every artifact records its origin:

* previous state hash
* transformation plan
* applied steps
* signatures

Artifacts form a **chain of transformations**.

> Break the chain, and the artifact tells on you.

This enables:

* auditability
* reproducibility
* forensic traceability

---

## 🧪 Quick Example

Transform hardcoded strings into a deterministic plan:

```bash id="ex1"
dennis plan run . --dict messages_en.json
```

Forge the artifact:

```bash id="ex2"
dennis pack plan.json artifact.dex
```

Inspect the artifact:

```bash id="ex3"
dennis inspect artifact.dex
```

Apply the transformation:

```bash id="ex4"
dennis apply rehydrated-plan.json
```

Undo if necessary:

```bash id="ex5"
dennis invert rehydrated-plan.json
dennis apply rehydrated-plan.undo.json
```

Dennis guarantees the invariant:

```text id="inv1"
apply(plan)
apply(invert(plan))
→ filesystem returns to its original state
```

---

## 🧠 Philosophy

Dennis follows a simple doctrine:

* Deterministic over clever
* Reversible over risky
* Inspectable over magical
* Human-in-the-loop by default

Every transformation can be:

* Planned
* Reviewed
* Forged into an artifact
* Verified
* Applied
* Undone

No hidden mutations. No silent rewrites. Just steel.

---

## 🧩 What Dennis Does

Dennis provides a full transformation lifecycle:

```text id="pipe2"
Scan → Decide → Plan → Review → Pack → Sign → Inspect → Rehydrate → Apply → Invert
```

It is designed for:

* i18n migrations
* codemods
* large-scale refactors
* deterministic rewrites
* safe automation in real repositories

---

## 📚 Learn More

* Intro:
  https://dev.to/crevilla2050/what-the-hex-is-a-dex-introducing-deterministic-transformation-artifacts-397d

* Deep dive:
  https://dev.to/crevilla2050/the-dex-was-not-a-hex-why-deterministic-artifacts-depend-on-deterministic-classification-2728

---

## ⚙️ Installation

```bash id="inst1"
pipx install dennis
```

For development:

```bash id="inst2"
pip install -e .
```

---

## 🧪 CLI Overview

```bash id="cli1"
dennis --help
```

### Core Commands

* `dennis plan` → generate deterministic plan
* `dennis validate` → validate plan schema
* `dennis export` → export projections
* `dennis rehydrate` → CSV → JSON canonical
* `dennis apply` → apply transformations
* `dennis invert` → revert transformations

### Legacy Commands (compatibility)

* scan
* generate-i18n
* apply-i18n

---

## 🧱 Design Principles

Dennis is intentionally:

* CLI First
* Lightweight
* Dependency-minimal
* Git-friendly
* Scriptable
* Deterministic

It avoids:

* runtime magic
* heavy frameworks
* hidden state
* implicit mutations

If a tool surprises you, it's probably not Dennis.

---

## 🔒 Determinism Guarantee

Given the same inputs:

* Same plan
* Same artifact
* Same output

Dennis ensures reproducibility across machines and CI.

---

## 🚧 Current Status

* Deterministic plan engine ✅
* Clean decision layer ✅
* DEX artifact system ✅
* Cryptographic signatures ✅
* Lineage tracking ✅
* Reversible transformations ✅

The forge is lit.

---

## 🧭 Roadmap

* Artifact registries
* Federation between registries
* Artifact discovery
* Plan diffing and previews
* UI / visualization layer
* Ecosystem around DEX artifacts

---

## 🧠 Why Dennis?

Most tools optimize for speed.

Dennis optimizes for **trust**.

It is built for engineers who want:

* Confidence over convenience
* Control over abstraction
* Craft over magic

---

## 🧪 Try it Yourself

https://github.com/crevilla2050/hello-dennis

---

Licensed under MIT.
Forged slowly. Built for trust.
