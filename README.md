# Dennis the Forge 🪓

Deterministic codemod engine and artifact system.

**Status:** Active development\
**License:** MIT\
**Python:** 3.10+\
**CLI:** `dennis`

------------------------------------------------------------------------

Dennis is a **deterministic codemod engine** that turns code
transformations into **portable artifacts**.

Plans are reviewable.\
Artifacts are inspectable.\
Transformations are reversible.

**No magic. Just steel.**

------------------------------------------------------------------------

## Quick Example

Transform hardcoded strings into a deterministic plan:

``` bash
dennis plan run . --dict messages_en.json
```

Forge the artifact:

``` bash
dennis pack plan.json artifact.dex
```

Inspect the artifact:

``` bash
dennis inspect artifact.dex
```

Apply the transformation:

``` bash
dennis apply rehydrated-plan.json
```

Undo if necessary:

``` bash
dennis invert rehydrated-plan.json
dennis apply rehydrated-plan.undo.json
```

Dennis guarantees the invariant:

    apply(plan)
    apply(invert(plan))
    → filesystem returns to its original state

------------------------------------------------------------------------

## Philosophy

Dennis follows a simple doctrine:

-   Deterministic over clever\
-   Reversible over risky\
-   Inspectable over magical\
-   Human‑in‑the‑loop by default

Every transformation can be:

-   Planned\
-   Reviewed\
-   Forged into an artifact\
-   Verified\
-   Applied\
-   Undone

No hidden mutations. No silent rewrites. Just steel.

------------------------------------------------------------------------

## What Dennis Does

Dennis provides a full transformation lifecycle:

    Scan → Plan → Review → Pack → Sign → Inspect → Rehydrate → Apply → Invert

It is designed for:

-   i18n migrations\
-   codemods\
-   large‑scale refactors\
-   deterministic rewrites\
-   safe automation in real repositories

------------------------------------------------------------------------

## Installation

The easiest way to install Dennis is with pipx:

``` bash
pipx install dennis
```

For development:

``` bash
pip install -e .

This exposes the dennis CLI.

CLI Overview
Run:
dennis --help

Core Commands

dennis plan Generate deterministic transformation plan
dennis validate Validate a plan against schema
dennis export Export projections (CSV / JS)
dennis rehydrate CSV → JSON canonical
dennis apply Apply transformations
dennis undo Revert transformations

Legacy Commands (compatibility layer)

Dennis evolved from earlier tooling and maintains compatibility:
- scan
- generate-i18n
- apply-i18n

These remain available during the transition phase.

Design Principles

Dennis is intentionally:

-   Lightweight\
-   Dependency‑minimal\
-   Git‑friendly\
-   Scriptable\
-   Deterministic

It avoids:

-   runtime magic\
-   heavy frameworks\
-   hidden state\
-   implicit mutations

If a tool surprises you, it's probably not Dennis.

------------------------------------------------------------------------

## Determinism Guarantee

Given the same inputs:

-   Same plan\
-   Same artifact\
-   Same output

Dennis sorts and serializes consistently to ensure reproducibility
across machines and CI environments.

------------------------------------------------------------------------

## Current Status

Dennis is actively evolving, but the core forge is already stable:

-   Deterministic plan engine ✅\
-   Artifact format (DEX) ✅\
-   Cryptographic signatures ✅\
-   Rehydration pipeline ✅\
-   Reversible transformations ✅

The forge is lit.

------------------------------------------------------------------------

## Roadmap

Planned future directions:

-   Artifact registries\
-   Federation between registries\
-   Artifact discovery and search\
-   Plan diffing and previews\
-   Interactive review UI\
-   Developer ecosystem around transformation artifacts

Dennis is being built slowly and deliberately.

------------------------------------------------------------------------

## Why Dennis?

Most automation tools optimize for speed.

Dennis optimizes for **trust**.

It is designed for engineers who want:

-   Confidence over convenience\
-   Control over abstraction\
-   Craft over magic

------------------------------------------------------------------------

## Try it yourself

A small example project is available to experiment with Dennis:

https://github.com/crevilla2050/hello-dennis

------------------------------------------------------------------------

Licensed under MIT.\
Forged slowly. Built for trust.
