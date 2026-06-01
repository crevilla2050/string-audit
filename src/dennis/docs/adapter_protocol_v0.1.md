# ADAPTER_PROTOCOL_v0.1

## Status

Draft

## Purpose

Define the contract between Dennis Core and language/document adapters.

Adapters are responsible for translating source material into canonical semantic objects.

Adapters do not:

* generate DEX artifacts
* generate plans
* execute transformations
* verify transformations
* sign artifacts

Adapters only observe and describe content.

---

# Core Principle

Dennis Core understands meaning.

Adapters understand syntax.

---

# Scope

Adapters may process:

* Programming languages
* Markup languages
* Configuration files
* Documentation
* Plain text
* Structured documents

Examples:

* Python
* PHP
* Java
* Go
* Ruby
* XML
* HTML
* DOT
* TXT
* ODT

---

# Responsibilities

An adapter MUST:

1. Parse source material.
2. Identify semantic objects.
3. Return canonical observations.

An adapter MUST NOT:

1. Modify files.
2. Generate plans.
3. Generate DEX artifacts.
4. Perform execution.
5. Apply transformations.

---

# Processing Pipeline

Input

```
File
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

Dennis Core

```
    ↓
```

Goals

```
    ↓
```

Specs

```
    ↓
```

Plans

```
    ↓
```

DEX

---

# Semantic Object

Canonical representation of a discovered element.

Example:

{
"type": "STRING",
"value": "Hello world"
}

Dictionary entries may serve two purposes:

1. Exclusion Rules
   Prevent extraction/transformation.

2. Semantic Hints
   Assist adapter classification.

The same dictionary may be used for both.

---

# Canonical Types v0.1

STRING

User-visible text.

Examples:

* Python string literal
* PHP string literal
* XML text node
* DOT label

---

SENTENCE

Human-readable sentence.

Primarily intended for TXT ingestion.

Example:

"Hello world."

---

PARAGRAPH

Multiple related sentences.

---

TITLE

Document title or heading.

Examples:

* HTML h1
* XML title
* Markdown heading

---

COMMENT

Human-readable comments.

Examples:

* Python comments
* C comments
* SQL comments

---

FUNCTION

Executable function definition.

---

CLASS

Class definition.

---

MODULE

File/module/package level construct.

---

CONFIG_ENTRY

Configuration value.

Examples:

* JSON
* YAML
* INI

---

DEPENDENCY

External dependency declaration.

Examples:

* requirements.txt
* package.json
* pom.xml

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

* API keys
* Passwords
* Tokens

---

# TXT Adapter Guidance

TXT is considered a first-class format.

Recommended observation unit:

SENTENCE

Rationale:

* Human-readable
* Reviewable
* Stable
* Appropriate for translation workflows

Implementations MAY use NLP sentence segmentation.

The protocol only defines the semantic unit.

---

# Adapter Output

Example:

[
{
"type": "STRING",
"value": "Hello world",
"location": {
"file": "hello.py",
"line": 12
}
}
]

Location metadata is optional but recommended.

---

# Protocol Invariants

Goals describe WHY.

Transformation Types describe WHAT.

Plans describe HOW.

DEX artifacts describe EXECUTABLE INTENT.

---

# Future Compatibility

Future adapters should require no changes to Dennis Core.

Adding support for:

* PHP
* Java
* Go
* Ruby
* DOT
* TXT
* XML
* ODT

should only require implementing a new adapter.

---

# Design Motto

Transformation Types are universal.

Language syntax is local.
