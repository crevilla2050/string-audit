# Dennis Forge — Information Integrity Through Deterministic Change

**Status:** Active development  
**License:** MIT  
**Python:** 3.10+  
**CLI:** `dennis`

**Discover what exists. Transform information through explicit, reviewable procedures. Preserve the evidence of what changed.**

Dennis Forge is an information-integrity system built around two complementary capabilities:

1. **Discovery and state capture** — inspect supported targets and establish a structured, inspectable picture of their current state.
2. **Controlled transformation** — describe intended changes in explicit plans, validate them, and apply supported transformations through reproducible, reviewable steps.

The software-development workflow is the primary implemented application today. The underlying approach is intended to be useful anywhere information must be inspected, changed under controlled procedures, and traced afterward—but other domains require their own integrations and validation.

> Plans are reviewable. Artifacts are inspectable. Changes should never be a surprise.

---

## The two pillars

### 1. Discover and capture

Before changing anything, establish what exists.

Dennis's scanning and inspection workflows help capture and reason about a supported target's current state. The exact inventory and state information available depends on the target and the capabilities implemented for it; Dennis does not claim universal, out-of-the-box discovery of every system.

Discovery provides the baseline against which a proposed change can be understood and reviewed.

### 2. Plan and transform

When a change is required, Dennis represents it as an explicit plan rather than relying on hidden or implicit mutations.

The transformation workflow supports:

- generating and validating plans;
- reviewing intended changes before applying them;
- packaging plans as portable DEX artifacts;
- inspecting and rehydrating artifacts;
- applying supported transformations and generating inverse plans where available;
- preserving hashes, signatures, and lineage information where the artifact workflow provides them.

The objective is controlled, reproducible change—not automation for its own sake.

## DEX artifacts: the integrity bridge

A DEX artifact is a portable package describing a transformation and the information needed to inspect its provenance.

A typical artifact contains:

```text
artifact.dex
├── manifest.json
├── payload/
│   └── plan.json
└── signatures/
```

The manifest, plan, and signatures connect a declared transformation to its artifact-level integrity and lineage information. DEX is the common representation that makes transformations portable and inspectable; it does not require every discovery workflow to be a transformation.

## Workflow

The implemented command-line workflow includes stages such as:

```text
scan → decide → plan → validate → pack/sign → inspect → rehydrate → apply → invert
```

The available stages depend on the operation and target. Each stage is intended to be explicit and inspectable.

## Quick example

Generate a plan from a supported repository:

```bash
dennis plan run . --dict messages_en.json
```

Package the plan as an artifact:

```bash
dennis pack plan.json artifact.dex
```

Inspect the artifact:

```bash
dennis inspect artifact.dex
```

Apply a rehydrated plan:

```bash
dennis apply rehydrated-plan.json
```

Generate and apply an inverse plan when the transformation supports it:

```bash
dennis invert rehydrated-plan.json
dennis apply rehydrated-plan.undo.json
```

Review the plan and understand its effects before applying it. Reversibility depends on the operation and the information captured by its plan; it should not be interpreted as a promise that every arbitrary external side effect can be undone.

## Integrity, determinism, and lineage

Dennis is designed around these principles:

- **Determinism:** for supported operations, equivalent inputs and conditions should produce reproducible plans and results.
- **Explicit plans:** intended changes are represented as data that can be inspected and validated.
- **Artifact integrity:** DEX packages can carry integrity and signature information.
- **Lineage:** artifact workflows can record relationships between prior state, plans, and subsequent transformations.
- **Human review:** inspection and validation belong in the workflow, not as afterthoughts.
- **Non-destructive defaults:** avoid silent changes; review and approval matter, especially for destructive operations.

These capabilities support auditability and reproducibility. They do not, by themselves, certify regulatory compliance or establish forensic admissibility in a particular jurisdiction.

## What Dennis is for

The current software focus includes:

- internationalization and localization migrations;
- codemods and deterministic rewrites;
- large-scale refactoring in supported repositories;
- structured plan generation and validation;
- repeatable change workflows in development and CI environments.

The same two-pillar model may also inform future applications involving configuration inventories, controlled deployments, records, or other information-management workflows. Those uses require target-specific engineering, operational controls, and validation; they should not be read as claims that every such integration already exists.

## Installation

Install the published CLI with `pipx`:

```bash
pipx install dennis
```

For development from a source checkout:

```bash
pip install -e .
```

See the available commands:

```bash
dennis --help
```

### CLI overview

Core commands include:

- `dennis plan` — generate a deterministic plan;
- `dennis validate` — validate a plan schema;
- `dennis export` — export projections;
- `dennis rehydrate` — convert supported CSV input to canonical JSON;
- `dennis apply` — apply supported transformations;
- `dennis invert` — generate an inverse transformation plan;
- `dennis inspect` — inspect a DEX artifact.

Compatibility commands include `scan`, `generate-i18n`, and `apply-i18n`.

Exact syntax and available options may evolve during active development; use `dennis <command> --help` for the installed version.

## Design principles

Dennis is intentionally:

- CLI-first;
- lightweight and scriptable;
- Git-friendly;
- explicit rather than magical;
- deterministic where the operation supports it;
- inspectable before execution;
- cautious about destructive changes.

The guiding rule is simple: **if it is not broken, do not repair it.** Make changes because a reviewed plan calls for them—not because a tool silently decided to rewrite something.

## Learn more

- **Website:** https://www.dennis-forge.com/
- **Forge repository:** https://github.com/crevilla2050/dennis-forge
- **Example project:** https://github.com/crevilla2050/hello-dennis
- **Introduction to DEX:** https://dev.to/crevilla2050/what-the-hex-is-a-dex-introducing-deterministic-transformation-artifacts-397d
- **DEX and deterministic classification:** https://dev.to/crevilla2050/the-dex-was-not-a-hex-why-deterministic-artifacts-depend-on-deterministic-classification-2728

---

Dennis Forge is built for people who need to understand what exists, control what changes, and retain an inspectable account of the transformation.

**No hidden mutations. No magic. Just steel.**

Licensed under MIT.
