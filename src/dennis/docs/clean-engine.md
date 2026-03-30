# Dennis Clean Engine (v0.7.0)

## Overview

The **Clean Engine** introduces a post-processing pipeline for dictionary refinement in Dennis.

Its purpose is to remove non-human strings (e.g. SQL, CSS, URLs, identifiers) from generated dictionaries while preserving:

* determinism
* traceability
* non-destructive workflows

---

## Core Principles

### 1. Non-Destructive by Default

Dennis NEVER overwrites existing files unless explicitly instructed.

Every transformation produces a **new file**.

---

### 2. Separation of Concerns

```
plan   → generates data
filter → transforms data
```

These stages are independent but composable.

---

### 3. Deterministic Processing

Given:

* same input file
* same filters

The output is always identical (except for timestamp in filename).

---

### 4. Transparency over Magic

Filtering is:

* explicit via CLI
* optionally automated via flags
* always reproducible

---

## File Naming Convention

### Raw Dictionary

```
<name>.json
```

Example:

```
tacosroy.json
```

---

### Cleaned Dictionary

```
<name>.cleaned.<filters>.<timestamp>.json
```

Example:

```
tacosroy.cleaned.css-sql-url.2026-03-18T21-15.json
```

---

### Rules

* Filters MUST be sorted alphabetically
* Timestamp MUST be ISO-8601 (no seconds precision required)
* Original file MUST remain unchanged

---

## CLI Commands

### 1. Generate Plan

```
dennis plan run . --dict tacosroy.json
```

Output:

```
tacosroy.json
```

---

### 2. Apply Filters

```
dennis filter tacosroy.json --filters sql css url
```

Output:

```
tacosroy.cleaned.css-sql-url.<timestamp>.json
```

---

### 3. Custom Output

```
dennis filter tacosroy.json --filters sql css --out custom.json
```

---

### 4. Auto Filter (Optional)

```
dennis plan run . --dict tacosroy.json --auto-filter
```

Output:

```
tacosroy.json
tacosroy.cleaned.css-sql-url.<timestamp>.json
```

---

## Available Filters (v0.7.0)

### sql

Removes SQL queries and statements.

Examples:

* `INSERT INTO ...`
* `SELECT * FROM ...`

---

### css

Removes CSS class definitions and style tokens.

Examples:

* `btn btn-primary`
* `d-flex justify-content-between`

---

### url

Removes URLs and external resource links.

Examples:

* `https://cdn.jsdelivr.net/...`
* `http://example.com/...`

---

## Processing Pipeline

```
dictionary (raw)
    ↓
apply_filters()
    ↓
cleaned dictionary
    ↓
write new file
```

---

## Design Philosophy

The Clean Engine embraces:

> “Be permissive in extraction, strict in refinement.”

Dennis intentionally collects more data during scanning, then applies deterministic filters afterward.

This avoids:

* fragile regex detection
* language-specific edge cases
* premature optimization

---

## Future Extensions

Planned enhancements include:

* additional filters (js, html, config)
* plugin-based filters
* pipeline chaining (multi-stage processing)
* SaaS-based diff visualization
* artifact lineage tracking

---

## Summary

The Clean Engine transforms Dennis from:

```
string extractor
```

into:

```
deterministic transformation pipeline
```

while preserving:

* simplicity
* auditability
* extensibility
* user control

Dennis does not try to understand everything.

Dennis removes everything that should NOT be translated.
