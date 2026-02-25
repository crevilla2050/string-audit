Dennis UI Doctrine v0.1
Purpose

The Dennis UI exists to expose the full power of the CLI in a visual, human-friendly way.

It is not a replacement for the CLI.
It is a clarity layer.

The CLI remains the source of truth.

The UI exists to:
- Visualize plans
- Aid human review
- Reduce cognitive load
- Enable safe curation

Dennis is CLI-first.
UI-second.
Always.

Core Principle.

The UI must never introduce capabilities that do not exist in the CLI.
Everything the UI can do must map directly to:

- A CLI command
- A deterministic artifact
- A reproducible workflow

If it cannot be done from the CLI, it should not exist in the UI.

This keeps Dennis:
- Scriptable
- Deterministic
- Honest

CLI Parity Rule
Every UI action must have a 1:1 CLI equivalent.

Examples:

UI Action	CLI Equivalent
Load plan	dennis plan.json
Validate plan	dennis validate plan.json
Export CSV	dennis export --csv
Rehydrate CSV	dennis rehydrate
Apply changes	dennis apply
Undo changes	dennis undo

The UI is a mirror, not a fork.

Primary UI Goal
The UI exists to make plans understandable at a glance.
Dennis is plan-centric. Therefore the UI is:

- A plan inspection and curation interface.

Not:

- A code editor
- A full IDE
- A replacement for git tools

Dennis UI is focused, not general.

Interaction Model
The UI revolves around a two-panel mental model.

Left panel:
- Original state
- Source context
- Immutable reference

Right panel:
- Proposed transformation
- Editable tokens
- Curated output

This preserves a core Dennis invariant:
Original data is never silently mutated. Determinism Preservation
The UI must not break determinism.

This means:
- No hidden sorting
- No implicit rewrites
- No silent normalization

All transformations must remain:
- Explicit
- Serializable
- Reproducible

If a UI action changes output, it must be exportable as data.

Artifact-Centric Design
Dennis UI does not manipulate code directly. It manipulates artifacts:

- JSON plans
- CSV exports
- Deterministic projections

The UI should feel like: A visual shell around structured artifacts.
Not: A live mutation environment.
This preserves safety.

Import / Export Philosophy
The UI must support round-trippable formats:
- Inputs
- Plan JSON
- CSV exports

Future projections (optional)
Outputs:
- Plan JSON (canonical)
- CSV (human editing)
- JS projections (frontend use)

Every export must be re-ingestable.

No dead-end formats.

Trust Model

Dennis is built on trust.
The UI must reinforce this.

Rules:
- No auto-apply without confirmation
- No hidden mutations
- No irreversible actions
- Undo must always exist

If an action feels magical, it violates doctrine.

Non-Goals
The Dennis UI is intentionally limited.
It is NOT:

- A full IDE
- A Git GUI
- A refactoring playground
- A real-time code transformer

Scope discipline keeps Dennis sharp.
Human-in-the-Loop Guarantee

Dennis assumes:

Humans are good at:
- Judgement
- Pattern recognition
- Context

Machines are good at:
- Repetition
- Determinism
- Serialization

The UI exists to bridge both. It should empower humans without hiding the machine.

Error Transparency

Errors must be:
- Explicit
- Localized
- Understandable
- No generic failures.

If a plan fails validation, the UI should:
- Show why
- Show where
- Offer recovery paths

Opacity erodes trust.

Future UI Layers
Potential future expansions:

- Side-by-side diff visualization
- Confidence scoring overlays
- Batch edit tokens
- Plan diffing
- Plugin panels

All future features must pass the CLI parity rule.

Aesthetic Direction
Dennis UI should feel:
- Calm
- Mechanical
- Intentional
- Tool-like

Avoid:
- Flashy animations
- Excessive chrome
- Dashboard clutter
- Dennis is a forge, not a casino.

Final Principle

The UI must never dilute Dennis.

If forced to choose between:
Convenience / Clarity

Choose clarity.

If forced to choose between:
Speed/Trust

Choose trust.

Dennis is not built for speed. Dennis is built for confidence.