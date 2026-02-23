# Dennis Architecture Blueprint

High-level internal layout.

## Layers

1. Discovery Layer
   - Git-aware file enumeration

2. Detection Layer
   - String detectors
   - Heuristics

3. Transformation Layer
   - Dictionary building
   - Mapping logic

4. Planning Layer
   - Pure plan generation
   - Deterministic sorting

5. Execution Layer
   - Plan validation
   - Apply engine

## Purity Boundaries

Pure layers:
- Discovery
- Detection
- Planning

Impure layers:
- CLI I/O
- File writes
- Apply

## Dependency Direction

CLI → Planning → Detection

Never the reverse.

Core logic must remain importable as a library.

## CLI

- `dennis` - main CLI entrypoint
- `dennis-apply` - apply engine
- `dennis-detect` - detection engine
- `dennis-plan` - planning engine
- `dennis undo` - undo engine

## Plan Algebra Layer

Handles transformations of plans themselves.

Includes:
- Plan inversion (undo)
- Plan merging (future)
- Plan filtering (future)

This layer operates purely on plan artifacts and remains side-effect free.

## Plan Algebra Layer

Handles transformations of plans themselves.

Includes:
- Inversion (reversible plans)
- Filtering (future)
- Merging (future)

This layer operates purely on plan artifacts and remains side-effect free.

Aliases such as `undo` are implemented as compositions of plan algebra primitives.