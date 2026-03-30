# Dennis Plan Schema v0.1

The plan file is the canonical artifact of Dennis.

It defines deterministic, replayable transformations.

## Top-Level Structure

```json
{
  "tool": "dennis",
  "version": "0.1.0",
  "generated_at": "ISO8601 UTC timestamp",
  "project_root": "absolute or canonical path",
  "dictionary": "path or identifier"
}