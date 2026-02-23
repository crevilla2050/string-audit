# Dennis Stability Model

Defines what is allowed to change over time.

## Stability Tiers

### Tier 1 — Immutable (after 1.0)
- Plan schema
- Determinism guarantees

### Tier 2 — Very Stable
- CLI verbs
- Core workflow

### Tier 3 — Flexible
- Flags
- Output formats
- Internal architecture

## Version Semantics

0.x:
    Rapid iteration allowed.

1.0:
    Plan schema frozen.
    Core contracts locked.

Post-1.0:
    Additive evolution only.