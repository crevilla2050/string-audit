# Dennis the Forge

Dennis the Forge is a deterministic codemod engine for Git-native projects.  
It plans, reviews, and forges transformations into your codebase with precision and intent.  

Built for engineers who prefer craftsmanship over magic.

---

## Philosophy

Dennis is built around a few simple ideas:

- Deterministic > clever  
- Git is the source of truth  
- Plans before changes  
- Small tools, sharp edges  

No hidden AST wizardry.  
No framework lock-in.  
Just controlled, reviewable transformations.

---

## What it does

Dennis helps you migrate codebases safely by turning large refactors into a clear pipeline:

1. Scan your codebase  
2. Generate a plan  
3. Review the plan  
4. Apply transformations  

Think of it as a codemod engine with brakes.

---

## Core Features

- Git-native scanning (no junk, no venv noise)
- Plan → review → apply workflow
- Deterministic output
- Lightweight CLI
- Framework-agnostic

---

## Install

```bash
pip install -e .

(Temporary local install — PyPI packaging will come later.)

## Usage:

$>Scan a project
$>dennis scan <path/to/project>
$>Generate a transformation plan
$>dennis plan <dictionary.json>
$>Apply a reviewed plan
$>dennis apply --from-plan plan.json

All destructive operations are explicit and intentional.

## Origins:

Dennis the Forge started as a simple string-audit tool and evolved into a full codemod engine.
The original scanner still exists as a minimal building block:

$>string-audit (legacy component)
A lightweight CLI to detect hardcoded user-facing strings in Python codebases.

$>string-audit scan <path/to/project>
Dennis builds on top of this idea and takes it much further.

## Why Dennis?
Most migration tools are either:

* Too magical
* Too fragile
* Too coupled to frameworks

Dennis stays small and predictable. It treats code transformations like metalwork:
heat, shape, inspect, repeat.

Status
Early but real.
Already used on real-world codebases.
Expect sharp edges, but also sharp tools.

License

MIT