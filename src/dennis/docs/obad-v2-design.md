# OBAD v2 — Diagnostic Format Design

## 1. Purpose

OBAD is Dennis's diagnostic artifact format. Version 2 evolves the
existing format to represent diagnostic findings, operational errors,
validation results, and the outcome of a diagnostic operation.

OBAD remains the existing diagnostic format. Dennis must not introduce a
parallel report format for the same purpose.

## 2. Compatibility and evolution

- OBAD retains `meta.format: "obad"`.
- The format version is identified by `meta.version`.
- OBAD v2 must preserve the existing finding information used by Goal
  Discovery wherever practical.
- Consumers must be able to distinguish OBAD versions explicitly.
- The exact compatibility and migration behavior remains to be specified
  before implementation.

## 3. Stable top-level structure

Every OBAD v2 artifact must contain these top-level sections:

- `meta`
- `status`
- `findings`
- `errors`
- `validation`

The sections must not be omitted merely because they contain no data.

- `findings` is always an array; no findings are represented by `[]`.
- `errors` is always an array; no operational errors are represented by `[]`.
- `validation` is always an object containing `checks`.
- `validation.checks` is always an array; no recorded checks are represented
  by `[]`.

Empty collections must not be represented as `null` or omitted.

A stable structure supports predictable consumption and external JSON
diffing. Serialization and collection ordering rules remain to be specified.

## 4. Operational status

The top-level `status` describes whether the requested diagnostic operation
completed. It does not indicate whether validation passed or whether a
transformation should be applied.

The permitted values are:

- `completed`: the requested diagnostic operation finished, regardless of
  whether it discovered findings.
- `partial`: the operation started but could not finish all required work.
- `failed`: the operation could not be completed as a valid operation.

The `errors` section records operational errors and their causes. A
diagnostic operation may complete successfully while reporting findings.

## 5. Findings, errors, and validation

These concepts have distinct responsibilities:

- `findings` records diagnostic observations about the examined inputs.
- `errors` records operational failures that prevented or impaired work.
- `validation.checks` records the checks performed and their outcomes.

A finding is not automatically an operational error. For example, a
validator may complete successfully and report malformed markup.

Exact record fields, identifiers, severity vocabulary, check-result
vocabulary, and ordering rules must be specified before implementation.

## 6. Relationship to transformation plans

OBAD is diagnostic evidence, not an executable transformation plan.

- OBAD must not contain an `applicable` field.
- Transformation applicability and user-controlled decisions remain
  outside the responsibility of the diagnostic format.
- Reporting a finding or validation failure does not itself decide whether
  a user may proceed.
- OBAD describes what was observed or what happened; it does not silently
  authorize or prohibit a transformation.

## 7. Validation and application

Dennis validates a plan before application and presents relevant findings
before requesting explicit user confirmation.

Users may choose to proceed despite warnings when the operation can be
performed safely and atomically. A validation failure must not be silently
hidden.

Validation does not replace execution safeguards. Conditions discovered
after validation must still be handled safely.

## 8. Universal transformation atomicity

All Dennis transformation operations are subject to universal atomicity.

A transformation must either complete successfully or leave no partial
transformation behind. If it cannot complete, Dennis must report the
failure in JSON.

Writing an error report is not sufficient by itself if partial changes
remain. Dennis must roll back those changes or use an application strategy
that prevents partial changes from becoming visible.

A partial diagnostic operation may legitimately produce partial findings.
That does not permit a transformation to leave a partially modified target.

The exact implementation strategy for atomic application remains to be
specified and tested separately.

## 9. Inversion

The existing deterministic plan-inversion behavior must be preserved.

`dennis invert` structurally inverts the supplied plan. OBAD's evolution
must not silently change inversion semantics or make inversion depend on
diagnostic reports.

Any future execution-aware reversal workflow must be designed explicitly
as a separate capability and must use sufficient evidence of what actually
happened.

## 10. Determinism and integrity

OBAD serialization should be deterministic where practical, including
consistent JSON formatting and collection ordering.

Contextual values such as timestamps and project paths may legitimately
differ between reports. The rules for canonical serialization, hashing,
and integrity verification must be specified before implementation.

A content hash establishes consistency with the recorded digest; it is not
by itself a digital signature or proof that a diagnosis is correct.

## 11. Open decisions before implementation

The following details remain open and must be settled before implementation:

- Exact `meta` fields and their compatibility requirements.
- Exact finding and operational-error record schemas.
- Validation-check record fields and result vocabulary.
- Ordering rules for findings, errors, and validation checks.
- Timestamp representation and treatment of machine-specific paths.
- Canonical serialization and hashing rules, if a report hash is required.
- OBAD v1 compatibility and migration behavior.
- Schema and regression-test requirements.

No runtime behavior is changed by this design note alone.
