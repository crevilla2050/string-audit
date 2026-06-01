# DENNIS_AI_ARCHITECTURE_v0.1

## Purpose

Introduce AI-assisted goal discovery without compromising Dennis determinism.

## Core Principles

* Dennis remains fully functional without AI.
* AI is optional.
* AI is implemented through Goal Discovery Plugins.
* AI may propose goals and generated specifications.
* AI may not generate plans.
* AI may not generate DEX artifacts.
* AI may not modify files.
* Human approval is mandatory before entering the deterministic pipeline.

## Pipeline

Goal
↓
Spec
↓
Plan
↓
DEX
↓
Proof

## Responsibility Matrix

AI:

* Goal discovery
* Generated spec proposals

Human:

* Review
* Approval
* Editing

Dennis:

* Plan generation
* Artifact generation
* Execution
* Verification
