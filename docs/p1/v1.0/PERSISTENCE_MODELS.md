# Persistence Models

## Separation of models

P1 distinguishes:

- contract documents — complete P0-defined BriefVersion, TransformationSpecVersion, Approval and QAReport payloads;
- persistence records — identifiers, indexed metadata, timestamps and stored JSON needed for durable lookup;
- filesystem records — relative path, size/checksum and byte ownership.

No ORM-specific active-record behavior is part of the model. Repository callers work with domain/persistence records rather than raw SQLite rows.

## Authoritative contract-document rule

For BriefVersion and TransformationSpecVersion, the complete validated JSON document stored in SQLite is the authoritative persisted copy. The workspace does not contain a parallel authoritative version file.

The authoritative rule does not mean the JSON is trusted blindly. Persistence must prove that the JSON, indexed columns and P0 hash are consistent before accepting a write and again at critical trust boundaries.

## Model rules

### OrderRecord

Mirrors the approved Order fields from MVP-0 Implementation Scope v1.1. Approval-derived booleans are not added. Selected version ids are references only; same-order existence is enforced by persistence.

### InputAssetRecord

Contains storage metadata only: id, order_id, original filename, relative path, media type, size, SHA-256 and created_at. No parse result or schema preview exists in P1.

### BriefVersionRecord

Contains identity/index fields plus the complete stored BriefVersion JSON document. `is_approved` and `approved_at` do not exist.

### TransformationSpecVersionRecord

Contains identity/index fields, exact Brief id/hash context and complete stored TransformationSpecVersion JSON document. `is_approved` and `approved_at` do not exist.

### ApprovalRecord

Exactly represents the immutable Approval fact. It is accepted only if the target exact version exists in the same order and its stored/recalculated content hash equals `target_content_hash`. Transformation Approval also requires exact Brief context equal to the target TransformationSpec's own Brief id/hash.

### ExecutionRunRecord

Persists the exact approved version/Approval references and run state required by the approved model. The version/Approval reference set is immutable after insert. P1 has no executor.

### ArtifactRecord

Represents one immutable file artifact reference owned by an ExecutionRun. File bytes are outside SQLite.

### QAReportRecord

Persists one complete P0 QAReport document and indexed identity/status fields. P1 has no QA evaluator. The indexed fields are derived from or verified against `report_json`, and the report's run/version references must equal the exact ExecutionRun references.

### EventRecord

Append-only audit event with order/run context and JSON payload. If `run_id` is present, that run must belong to the same `order_id`.

## Write-time integrity for version JSON

Before appending a BriefVersion or TransformationSpecVersion, the repository must perform all of the following before the DB mutation is accepted:

1. validate the complete document against the exact validated P0 JSON Schema for that entity;
2. extract identity/index values from the validated document and require exact equality with the persistence record (`id/version_id`, `order_id`, `version_number`, `schema_version`, `created_at`, and the entity-specific Brief reference fields where applicable);
3. rebuild the P0 semantic payload exactly as defined by the validated content-hash specification;
4. recompute NFC + RFC 8785 + SHA-256 and require equality with both the document's `content_hash` and the indexed `content_hash` column;
5. for TransformationSpecVersion, require exact stored Brief `(id, order_id, content_hash)` existence matching `brief_version_id` and `brief_content_hash`.

Callers must not be allowed to supply an arbitrary indexed value that contradicts the authoritative document. A practical repository API should derive indexed columns from the validated document and treat separately supplied expected ids/order as assertions only.

## QAReport JSON/index integrity

Before appending a QAReport:

1. validate `report_json` against the exact validated P0 QAReport schema;
2. require `report_id`, `run_id`, `brief_version_id`, `transformation_spec_version_id`, `generated_at` and `overall_status` indexed fields to exactly equal the corresponding values in `report_json`;
3. require the report's run/version tuple to equal the exact stored ExecutionRun tuple.

P1 does not evaluate checks or derive QA status; it only validates/persists an already valid contract instance.

## Trust-boundary verification

Critical invariants are rechecked when a stored contract crosses a trust boundary: load for later approval/execution/QA use and restart/recovery integrity verification. At minimum:

- JSON parses and still validates against the matching P0 schema;
- indexed identity fields still equal the JSON identity fields;
- version content hash still recomputes exactly;
- TransformationSpec exact Brief reference still resolves;
- QAReport indexed identity/status still matches `report_json` and the referenced ExecutionRun.

A mismatch is storage corruption. Persistence must not normalize, rewrite, rehash or silently repair the authoritative document.

P1 verification uses the P0 hash vectors and schemas; P1 does not redefine them.
