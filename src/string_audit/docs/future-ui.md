# Future UI: Dennis Plan Editor

A visual editor for Dennis plans.

Not a general GUI, but a structured plan editing environment.

## Core Concept

A two-panel interface:

Left panel:
    Original lines (read-only)

Right panel:
    Editable transformations

This preserves Dennis’s human-in-the-loop philosophy while improving safety and ergonomics.

## Goals

- Prevent malformed JSON edits
- Enforce schema correctness
- Normalize encodings (UTF-8 safe)
- Improve large-plan review workflows

## Capabilities

- Side-by-side diff editing
- Schema-aware validation
- Token integrity checks
- Export to JSON (canonical)
- Export to CSV (projection)

## Non-Goals

- Replacing the CLI
- Becoming a full migration platform
- Adding hidden transformations

The UI should remain a thin layer over the Dennis plan model.

## Timeline

This feature should only be considered after:

- Plan schema stabilization (post-1.0)
- Reversible plan maturity
- CLI contract freeze

Tentative target: v1.5+