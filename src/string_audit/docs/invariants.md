
---

## 🔒 Dennis Invariants

```markdown
# Dennis Core Invariants

These are non-negotiable properties of the engine.

## Deterministic Output

- Sorted file traversal
- Sorted plan entries
- Stable token ordering

## Pure Planning

Plan generation must be side-effect free.

No file writes.
No mutations.
No hidden state.

## Side-Effect Boundaries

Only two operations may mutate disk:

1. Plan writing
2. Apply execution

Everything else must remain pure.

## Idempotent Apply

Applying the same plan twice must either:
- Produce identical output
- Or safely no-op

## Exact Matching

Apply must only replace lines that match exactly.

No fuzzy replacements.
No heuristics.

## Git Awareness

File discovery must be Git-aware by default.

## Immutable Plans

Dennis must treat plans as read-only inputs.

Never rewrite plan files.
Never modify plan files.
Never mutate plan files.

## Plan Invertibility

Every generated plan must be invertible.

An inverse plan must be derivable by swapping:

original ↔ replacement

This enables deterministic undo operations.

Undo must not rely on:
- Hidden backups
- External state
- Temporary files

Undo is implemented as applying an inverse plan.

## Plan Algebra

Plans are first-class, transformable artifacts.

Dennis supports operations on plans themselves, including:
- Inversion (undo)
- Filtering (future)
- Merging (future)

All transformations must produce new plans rather than performing implicit mutations.

No special-case undo commands should bypass the plan model.

## Undo Safety

Undo operations must be non-destructive by default.

The `undo` command should:
- Generate reversible plans first
- Require explicit flags for mutation

No undo operation should apply changes silently.