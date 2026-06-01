# SEMANTIC_OBJECT_PROTOCOL_v0.1

## Status

Draft

## Purpose

Define the canonical observation format produced by adapters.

Semantic Objects represent discovered meaning extracted from source material.

They are language-independent.

They are format-independent.

They are the primary input for Goal Discovery, reporting, visualization, and future AI-assisted analysis.

---

# Core Principle

Dennis Core does not consume syntax.

Dennis Core consumes Semantic Objects.

Adapters are responsible for translating syntax into Semantic Objects.

---

# Processing Pipeline

File

```
↓
```

Adapter

```
↓
```

Semantic Objects

```
↓
```

Goal Discovery

```
↓
```

Spec

```
↓
```

Plan

```
↓
```

DEX

---

# Canonical Structure

Minimum structure:

{
"type": "STRING",
"value": "Hello world"
}

---

# Recommended Structure

{
"type": "STRING",
"value": "Hello world",
"location": {
"file": "hello.py",
"line": 12
},
"metadata": {}
}

---

# Required Fields

type

Semantic classification.

Examples:

* STRING
* SENTENCE
* PARAGRAPH
* TITLE
* COMMENT
* FUNCTION
* CLASS
* MODULE
* CONFIG_ENTRY
* URL
* EMAIL
* SECRET

---

value

Observed content.

Example:

"Hello world"

---

# Optional Fields

location

Location in source material.

Example:

{
"file": "hello.py",
"line": 12
}

Location information is advisory.

Dennis Core MUST NOT require it.

---

metadata

Adapter-specific information.

Example:

{
"language": "python",
"quote_type": "double"
}

Dennis Core MUST ignore unknown metadata fields.

---

# Canonical Types v0.1

STRING

User-visible text.

Examples:

Python:

print("Hello world")

PHP:

echo "Hello world";

DOT:

label="Hello world"

XML:

<title>Hello world</title>

---

SENTENCE

Single human-readable sentence.

Primarily intended for TXT ingestion.

Example:

"Hello world."

---

PARAGRAPH

Multiple related sentences.

---

TITLE

Document title or heading.

---

COMMENT

Human-readable comment.

Examples:

# comment

/* comment */

<!-- comment -->

---

FUNCTION

Executable function definition.

---

CLASS

Class definition.

---

MODULE

Module, package, or file-level construct.

---

CONFIG_ENTRY

Configuration value.

---

DEPENDENCY

Dependency declaration.

---

URL

Web address.

---

EMAIL

Email address.

---

SECRET

Sensitive value.

Examples:

API keys

Passwords

Tokens

UNKNOWN

Semantic object could not be reliably classified.

The adapter detected content,
but could not determine its semantic type.

Consumers should treat UNKNOWN
as an observation requiring human review.

---

# Adapter Examples

Python Adapter

Input:

print("Hello world")

Output:

{
"type": "STRING",
"value": "Hello world",
"location": {
"file": "hello.py",
"line": 12
}
}

---

DOT Adapter

Input:

label="Hello world"

Output:

{
"type": "STRING",
"value": "Hello world"
}

---

TXT Adapter

Input:

Hello world.

Output:

{
"type": "SENTENCE",
"value": "Hello world."
}

---

# Protocol Invariants

Semantic Objects are observations.

They are not goals.

They are not plans.

They are not transformations.

They describe what exists, not what should happen.

---

# Non-Goals

Semantic Objects MUST NOT:

* modify files
* generate plans
* execute transformations
* infer intent
* generate DEX artifacts

Those responsibilities belong to later stages.

---

# Future Compatibility

New semantic types may be added in future versions.

Consumers MUST ignore unknown types they do not understand.

---

# Design Motto

Observe first.

Interpret later.
