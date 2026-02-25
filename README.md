Dennis the Forge 🪓

Dennis the Forge is a deterministic codemod engine for Git-native projects.
It plans, reviews, and forges transformations into your codebase with precision and intent.

Built for engineers who prefer craftsmanship over magic.

Philosophy

Dennis follows a simple doctrine:
- Deterministic over clever
- Reversible over risky
- Inspectable over magical
- Human-in-the-loop by default

Every transformation can be:
- Planned
- Reviewed
- Exported
- Rehydrated
- Applied
- Undone

No hidden mutations. No silent rewrites. Just steel.

What Dennis Does.
Dennis provides a full transformation lifecycle:

Scan → Plan → Validate → Export → Human Review → Rehydrate → Apply → Undo

It is designed for:
- i18n migrations
- codemods
- large-scale refactors
- deterministic rewrites
- safe automation in real repositories

Installation

Currently optimized for local development: 

pip install -e .

This exposes the dennis CLI.

CLI Overview
Run:
dennis --help

Core Commands

dennis plan Generate deterministic transformation plan
dennis validate Validate a plan against schema
dennis export Export projections (CSV / JS)
dennis rehydrate CSV → JSON canonical
dennis apply Apply transformations
dennis undo Revert transformations

Legacy Commands (compatibility layer)

Dennis evolved from earlier tooling and maintains compatibility:
- scan
- generate-i18n
- apply-i18n

These remain available during the transition phase.

Design Principles

Dennis is intentionally:
- Lightweight
- Dependency-minimal
- Git-friendly
- Scriptable
- Deterministic

It avoids:
- runtime magic
- heavy frameworks
- hidden state
- implicit mutations

If a tool surprises you, it’s probably not Dennis.

Reversible Plans

Dennis transformations are built around plans.

A plan is:
- JSON
- Deterministic
- Schema-validated
- Human-readable

Plans can be:
- Exported to CSV for spreadsheet review
- Rehydrated back into canonical JSON
- Inverted into undo plans

This makes Dennis safe for real-world refactors.

Determinism Guarantee

Given the same inputs:
- Same plan
- Same exports
- Same output

Dennis sorts and serializes consistently to ensure reproducibility across machines and CI environments.

Current Status.

Dennis is actively evolving, but the core engine is already stable:
- Deterministic plan engine ✅
- Schema validation ✅
- CSV roundtrip ✅
- JS export ✅
- CLI lifecycle complete ✅

The forge is hot.

Roadmap

Planned future directions:
- Richer CLI ergonomics
- Git-native workflows
- Plan diffing and previews
- Interactive review UI
- PyPI distribution
- Tooling ecosystem

Dennis is being built slowly and deliberately.

Why Dennis?

Most automation tools optimize for speed.
Dennis optimizes for trust.

It is designed for engineers who want:
- Confidence over convenience
- Control over abstraction
- Craft over magic

License: MIT

=========================

Example: Converting Hardcoded Strings to Tokens

Let’s walk through a simple real-world scenario.
You have a file with hardcoded user-facing strings:

print("Hello world")
print("Goodbye world")

You want to migrate these into deterministic, reviewable transformations.

1. Generate a plan
dennis plan ./project --dict en.json --out plan.json

This produces a deterministic transformation plan:

{
  "changes": [
    {
      "file": "src/hello.py",
      "line": 1,
      "original": "print(\"Hello world\")",
      "replacement": "print(msg.HELLO)"
    }
  ]
}

Nothing is applied yet.
Dennis always starts with a plan.

2. Validate the plan

dennis validate plan.json

This ensures the plan is schema-safe and deterministic.

3. Export for human review
Export to CSV for spreadsheet inspection:

dennis export plan.json --csv plan.csv

You can now:
- Review changes
- Annotate confidence
- Edit tokens
- Share with teammates

4. Rehydrate after review
Convert the curated CSV back into canonical JSON:

dennis rehydrate plan.csv --out reviewed.json

This restores a deterministic, machine-safe plan.

5. Apply transformations
Once satisfied:

dennis apply reviewed.json

Changes are applied exactly as reviewed.
No hidden mutations.

6. Undo if needed
Every plan is reversible. If something feels wrong:

dennis undo reviewed.json

Dennis generates and applies the inverse transformation.
Safety first.

Why This Matters
Dennis is built around a simple idea:

Transformations should be:
- Planned
- Reviewed
- Reversible
- Deterministic
- Not magical.
- Not irreversible.
- Not opaque.

Just forged.