
---

## 🔒 Dennis Invariants

```markdown
# Dennis Core Invariants

These are non-negotiable properties of the engine.

## Payload identity is canonical.

Two DEX artifacts with identical payload hashes represent the same transformation regardless of metadata, signatures, or container structure.

DEX container generation must be deterministic.

Given identical payload and metadata inputs, the resulting DEX artifact
must be byte-for-byte reproducible.

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

## Signatures must not alter payload identity.

Adding or removing signatures must never alter the payload hash or transformation semantics.

## Plan Signatures

Plans must be signable.

Signatures must be verifiable.

Signatures must not alter payload identity.

## Plan Metadata

Plans must support arbitrary metadata (for future extensions for different ingestors).

Metadata must not alter payload identity.

## Plan Container

Plans must be container-agnostic.

The same plan must work in:
- Git repos
- Filesystems
- Archives
- Databases

## Plan Portability

Plans must be portable across systems.

No system-specific assumptions.

## Plan Reproducibility

Plans must be reproducible.

The same plan must produce identical output on any system.

## Plan Isolation

Plan execution must be isolated.

Plan execution must not rely on implicit external state.

All inputs required for execution must be explicitly defined by the plan.

## Plan Validation

Plans must be self-validating.

Dennis must validate plans before execution.

## Plan Execution

Plan execution must be atomic.

Either:
- All changes succeed
- Or none do

No partial execution.

## Plan Execution Order

Plan execution must be deterministic.

Independent operations may execute in parallel, but the final result
must be identical to deterministic sequential execution.

## Plan Execution Parallelism

Plan execution must support parallelism.

Dennis must execute independent operations in parallel.

## Plan Execution Retry

Plan execution must support safe retry.

If execution fails partway through, the plan must be able to run again
without producing inconsistent state.

## Plan Execution Rollback

Plan execution must support rollback.

If execution fails, the system must be able to roll back to a consistent state.