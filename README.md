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
```

This exposes the `dennis` CLI.

------------------------------------------------------------------------

## Core Workflow

### 1. Generate a transformation plan

This applies for the example project at: https://github.com/crevilla2050/hello-dennis, just
clone project and build from scratch a plan:
``` bash

dennis plan run . --dict messages_en.json   --add-helper helper.py   --target-file hello.py   --line 12

```

This creates a deterministic transformation plan that you can open and review in any text editor.

No code is modified yet.

------------------------------------------------------------------------

### 2. Forge an artifact

``` bash
dennis pack plan_generated.json artifact.dex
```

Artifacts are portable transformation capsules.

------------------------------------------------------------------------

### 3. Sign the artifact (optional)
In order to sign your artifact, create a public and private keys, and apply signature:

``` bash
dennis keygen
...
...
dennis dex sign artifact.dex --key dev.key
```

Artifacts can be cryptographically verified.

------------------------------------------------------------------------

### 4. Inspect the artifact
You can rename the .dex file to tar.gz and examine it's contents. There is nothing hidden, no tricks.

``` bash
dennis inspect artifact.dex
```

Artifacts are transparent and inspectable.

------------------------------------------------------------------------

### 5. Rehydrate the plan

``` bash
dennis rehydrate artifact.dex
```

This restores the transformation plan locally.

------------------------------------------------------------------------

### 6. Apply the transformation

``` bash
dennis apply rehydrated-plan.json
```

Dennis executes the deterministic plan.

------------------------------------------------------------------------

### 7. Undo if necessary

Dennis transformations are reversible.

If the result is not what you expected, you can always return the
repository to its original state without resetting your Git branch or
pulling the project again.

``` bash
dennis invert rehydrated-plan.json
dennis apply rehydrated-plan.undo.json
```

Dennis guarantees the invariant:

    apply(plan)
    apply(invert(plan))
    → filesystem returns to its original state

------------------------------------------------------------------------

## Human Review Workflows

Dennis plans are designed to be **human‑reviewable**.

Plans can be exported to CSV and reviewed in spreadsheets or
collaborative tools.

``` bash
dennis plan export plan.json --format csv --file plan.csv
```

This allows teams to:

-   inspect planned changes\
-   annotate transformations\
-   collaborate outside the CLI

After review, the plan can be rehydrated back into canonical JSON.

``` bash
dennis rehydrate plan.csv --out reviewed-plan.json
```

Dennis ensures the resulting plan remains deterministic and
schema‑valid.

------------------------------------------------------------------------

## Artifact Model

Dennis transformations are packaged as **DEX artifacts**.

A DEX artifact contains:

    manifest.json
    payload/plan.json
    signatures/

Artifacts can be:

-   inspected\
-   verified\
-   distributed\
-   applied\
-   reversed

Artifacts make transformations **portable and auditable**.

------------------------------------------------------------------------

## Design Principles

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
