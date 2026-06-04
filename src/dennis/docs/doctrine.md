# Dennis the Forge — Doctrine v0.1

Dennis is a deterministic, plan-first codemod engine for Git-native projects.

This document defines the non-negotiable principles that guide the project.

## Core Identity

Dennis is:
- Deterministic
- Git-native
- Plan-first
- Framework-agnostic
- Explicit by design

Dennis is NOT:
- A linter
- A formatter
- An AI tool
- A framework plugin
- A migration platform

## The Pipeline

All transformations follow:

code → scan → dictionary → plan → review → apply

If a feature does not fit this pipeline, it likely does not belong in Dennis.

## Determinism

Same input must produce the same output.

No randomness.
No timing dependence.
No environment-sensitive behavior.

Dennis should behave more like a compiler than a script.

## Explicitness

Dennis never performs hidden mutations.

All code transformations must:
- Be planned
- Be reviewable
- Be replayable

## Git Reality

Dennis operates on repository truth, not filesystem accidents.

Git is the source of reality.

## Plans are Sacred

The plan file is a first-class artifact.

It must be:
- Immutable once generated
- Human-readable
- Replayable
- Auditable

## Safety Model

Dennis prioritizes safety over convenience.

No direct mutation without an explicit plan.

## Scope Boundaries

Dennis focuses on structured textual transformations.

Non-goals:
- IDE-style refactoring engines
- AI rewriting tools
- Full semantic compilers
- Framework integrations

## Craftsmanship

Dennis values:
- Minimalism
- Predictability
- Mechanical sympathy
- Long-term stability

## Stability Promise

Once 1.0 is released:
- Plan schema becomes immutable
- CLI verbs stabilize
- Determinism is never compromised

## Reversible Plans

Dennis supports reversible transformations through plan inversion.

Undo is implemented by generating and applying an inverse plan.

Canonical form:

    dennis invert plan.json > undo.json
    dennis apply --from-plan undo.json

This preserves:
- Determinism
- Reviewability
- Explicit workflows

Dennis may provide convenience aliases (e.g., `dennis undo`) but all undo operations are grounded in reversible plans.

# Dennis-on-Dennis Test

A mature Dennis installation must be capable of
inspecting its own source tree, generating
observations, deriving goals, producing
specifications, and proposing reviewable
improvement plans for itself.

A feature that helps Dennis understand,
explain, or improve Dennis is considered
strategically aligned with the project.