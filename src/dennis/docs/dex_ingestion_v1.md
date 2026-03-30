# DEX Artifact Ingestion Specification v1

Status: Draft

This document defines the validation pipeline used by Dennis Forge
when accepting DEX artifacts.

The goal of the ingestion process is to ensure that uploaded artifacts:

• conform to the DEX protocol
• are structurally valid
• are safe to process
• have verifiable identity
• cannot compromise the registry

Artifacts failing any validation step MUST be rejected.

---

# 1. Threat Model

The ingestion system must defend against:

• malformed containers
• decompression bombs
• oversized payloads
• path traversal attacks
• invalid manifests
• signature spoofing
• hash mismatch attacks
• duplicate artifact abuse

The system assumes uploaded artifacts may be hostile.

---

# 2. Ingestion Pipeline

Artifact ingestion follows a strict validation pipeline.

Upload
 ↓
Header Check
 ↓
Compression Check
 ↓
Tar Structure Validation
 ↓
Manifest Validation
 ↓
Payload Hash Verification
 ↓
Signature Verification
 ↓
Artifact Identity Calculation
 ↓
Artifact Storage

Failure at any step aborts ingestion.

---

# 3. File Header Check

Before decompression, the system must inspect the file header.

DEX artifacts must satisfy:

• gzip header present
• file size within allowed limits
• compression ratio within safe bounds

The system MUST reject files exceeding configured limits.

Recommended limits:

Max compressed size: configurable
Max decompressed size: configurable
Max compression ratio: configurable

These checks prevent decompression bomb attacks.

---

# 4. Safe Decompression

DEX artifacts use gzip compression.

Decompression must be performed using a safe streaming implementation.

The system MUST:

• enforce decompression size limits
• abort decompression if limits are exceeded
• avoid loading entire artifacts into memory when possible

---

# 5. TAR Container Validation

DEX artifacts contain a tar archive.

The tar structure must be validated before extraction.

Allowed entries:

manifest.json  
payload/*  
signatures/*  

The following MUST be rejected:

• absolute paths
• path traversal sequences (../)
• symbolic links
• hard links
• device nodes

Only regular files are permitted.

---

# 6. Required Files

A valid DEX artifact MUST contain:

manifest.json

Optional directories:

payload/
signatures/

The manifest must reference any payload files present.

---

# 7. Manifest Validation

The manifest must be validated against the official schema.

Validation includes:

• schema validation
• required fields
• field type correctness
• hash_version compatibility

Artifacts with invalid manifests MUST be rejected.

---

# 8. Payload Hash Verification

After payload extraction:

1. Canonical JSON normalization must be applied
2. plan_hash must be recomputed
3. recomputed hash must match manifest value

Mismatch MUST reject the artifact.

This ensures payload integrity.

---

# 9. Signature Verification

If the artifact contains signatures:

• signatures must reference valid public keys
• signature algorithm must be supported
• signature must verify against canonical payload

Invalid signatures must be flagged.

Registry policy may choose:

• reject invalid signatures
• accept artifact but mark signatures invalid

---

# 10. Artifact Identity Calculation

The system must compute:

payload_hash  
artifact_hash  
signature_set_hash (future)

These values become the canonical identifiers stored in the registry.

---

# 11. Deduplication

If an artifact with identical payload_hash already exists:

The registry must:

• avoid storing duplicate payload data
• record additional metadata if needed

Artifacts with identical payload but different signatures may coexist.

---

# 12. Storage Layout

Artifacts must be stored using content-addressed paths.

Recommended layout:

storage/
  artifacts/
    ab/
      cd/
        ef/
          abcdef123456.dex

Directory levels are derived from the artifact hash prefix.

This prevents filesystem hot spots.

---

# 13. Metadata Indexing

The registry database should record:

artifact_hash  
payload_hash  
signature_set_hash  
uploader  
upload_time  
artifact_size  

This enables efficient lookup and verification.

---

# 14. Rate Limiting

To prevent abuse, ingestion must enforce:

• per-user upload limits
• per-IP rate limits
• artifact size quotas

---

# 15. Logging

All ingestion attempts must be logged.

Logs must record:

• uploader identity
• artifact hash
• validation result
• rejection reason

Logs support auditing and abuse investigation.

---

# 16. Failure Handling

Artifacts failing validation must never be partially stored.

The system must guarantee:

• atomic ingestion
• no partial artifact state
• safe cleanup of temporary files

---

# 17. Security Principles

DEX ingestion follows these principles:

Reject early  
Validate everything  
Trust nothing  
Store immutable artifacts  
Verify before indexing

These rules protect the registry from malicious artifacts.
