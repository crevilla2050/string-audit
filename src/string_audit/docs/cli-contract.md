# Dennis CLI Contract

Defines stable command verbs and their meaning.

## Stable Verbs (v0.x → v1.x)

These verbs should remain stable long-term:

- scan   → detect candidates
- plan   → generate transformation plans
- apply  → execute reviewed plans
- undo → revert changes

## Semantic Meaning

scan:
    Pure analysis. No mutations.

plan:
    Deterministic transformation planning.
    Must be side-effect free except writing the plan file.

apply:
    The only destructive command.
    Must require explicit input (e.g., --from-plan).

undo:
    Revert changes from a previous apply.
    Must require explicit input (e.g., --from-plan).

## Command Philosophy

Commands should be:
- Short
- Verb-based
- Composable

Avoid:
- Verbosity
- Overloaded flags
- Hidden modes

### Plan Transformations

Dennis supports transformations of plans as standalone operations.

Example:

    dennis invert plan.json > undo.json
    dennis apply --from-plan undo.json

This reinforces:
- Human reviewability
- Deterministic workflows
- Composability

Single-step undo commands are considered convenience wrappers, not core primitives.

### Undo Semantics

Undo is implemented via plan inversion.

Canonical workflow:

    dennis invert plan.json > undo.json
    dennis apply --from-plan undo.json

Convenience alias:

    dennis undo plan.json

Aliases must:
- Preserve determinism
- Avoid hidden state
- Clearly communicate underlying operations

### Undo Modes

The `undo` command is a guided workflow over reversible plans.

Default behavior:
    Generate and preview inverse plan without applying changes.

Mutation requires explicit opt-in:
    --auto-apply

Pure composable mode:
    --stdout

### Stream Output

Dennis uses `--stdout` for raw stream emission.

This flag:
- Emits canonical machine-readable output
- Bypasses preview layers
- Enables Unix composability

The project favors established CLI conventions over novel terminology for long-term clarity.