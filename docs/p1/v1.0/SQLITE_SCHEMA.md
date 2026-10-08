# SQLite Schema Design

This document is declarative. It defines tables, keys and invariants but contains no SQL implementation.

## Global storage conventions

- UUID/string identifiers are stored as `TEXT`.
- UTC datetimes are stored as ISO-8601 text with `Z`; second precision is sufficient for P1.
- JSON documents are stored as UTF-8 JSON text and returned as structured objects by repositories.
- SHA-256 values are lower-case hexadecimal strings of 64 characters.
- monetary `budget` is stored as normalized decimal text, not floating point.
- filesystem references stored in SQLite are workspace-relative paths, never absolute paths.
- foreign-key enforcement is mandatory.
- P0 contract JSON Schema and content-hash validation is performed in repository/trust-boundary logic; SQLite guards complement but do not replace P0 validation.

## Exact-reference integrity strategy

P1 uses ordinary/composite foreign keys wherever the relationship is relationally expressible and DB insertion/update guards where polymorphic Approval semantics require cross-table predicates.

Defense-in-depth requirements:

- repository validation must reject invalid references with a P0-compatible structured error;
- DB constraints/guards must still reject invalid raw writes that bypass repositories;
- no DB guard is allowed to weaken or reinterpret P0 semantics.

## Internal table: schema_migrations

Purpose: track forward-only application database migrations.

Fields:

- `version` — integer primary key.
- `name` — non-empty migration name.
- `checksum` — SHA-256 of the immutable migration definition.
- `applied_at` — UTC datetime.

Applied migration checksums are immutable. A checksum mismatch blocks startup.

## orders

Fields:

- `id` — primary key.
- `title` — required text.
- `listing_text` — required text.
- `listing_url` — nullable text; reference field only.
- `status` — required, exactly one of the 10 MVP-0 Implementation Scope v1.1 states: `DRAFT`, `ANALYZING`, `NEEDS_CLARIFICATION`, `READY_FOR_APPROVAL`, `APPROVED`, `EXECUTING`, `NEEDS_FIX`, `READY`, `FAILED`, `CANCELLED`.
- `approval_stage` — nullable; when present exactly `BRIEF_PENDING`, `TRANSFORMATION_PENDING` or `COMPLETE`.
- `selected_brief_version_id` — nullable version reference.
- `selected_transformation_spec_version_id` — nullable version reference.
- `budget` — nullable normalized decimal text.
- `deadline` — nullable UTC datetime.
- `notes` — nullable text.
- `created_at` — required UTC datetime.
- `updated_at` — required UTC datetime.

Reference constraints:

- `(selected_brief_version_id, id)` -> `brief_versions(id, order_id)` when selected Brief is non-null;
- `(selected_transformation_spec_version_id, id)` -> `transformation_spec_versions(id, order_id)` when selected spec is non-null.

These constraints enforce existence and same-order ownership only. They deliberately do not force the two selected versions to be mutually compatible in every intermediate P3 workflow state.

P1 persists these fields but does not implement P3 workflow semantics.

## input_assets

Purpose: durable metadata for one locally stored input payload. P1 stores bytes and metadata but does not parse them.

Fields:

- `id` — primary key.
- `order_id` — required foreign key to `orders`.
- `original_filename` — required display metadata.
- `workspace_relpath` — required, unique workspace-relative path.
- `media_type` — nullable text metadata.
- `size_bytes` — required non-negative integer.
- `byte_sha256` — required SHA-256 of stored bytes.
- `created_at` — required UTC datetime.

P1 does not add `parse_status`, schema preview, delimiter, encoding or selected-sheet fields; those belong to P2 ingestion.

## brief_versions

Fields:

- `id` — primary key.
- `order_id` — required foreign key to `orders`.
- `version_number` — required positive integer.
- `schema_version` — required; Pilot contract value is `1.1`.
- `content_hash` — required SHA-256.
- `document_json` — required complete BriefVersion contract instance and authoritative persisted copy.
- `created_at` — required UTC datetime.

Candidate keys/constraints:

- unique `(order_id, version_number)`;
- unique `(id, order_id)` for same-order foreign keys;
- unique `(id, order_id, content_hash)` for exact compatibility references;
- no `is_approved` or `approved_at` columns.

The repository write/trust-boundary rules in `PERSISTENCE_MODELS.md` guarantee P0 schema validation, JSON/index identity consistency and recomputed content-hash equality.

## transformation_spec_versions

Fields:

- `id` — primary key.
- `order_id` — required foreign key to `orders`.
- `version_number` — required positive integer.
- `schema_version` — required; Pilot contract value is `1.1`.
- `brief_version_id` — required.
- `brief_content_hash` — required.
- `content_hash` — required SHA-256.
- `document_json` — required complete TransformationSpecVersion contract instance and authoritative persisted copy.
- `created_at` — required UTC datetime.

Candidate keys/constraints:

- unique `(order_id, version_number)`;
- unique `(id, order_id)` for same-order foreign keys;
- unique `(id, order_id, content_hash)` for exact hash references;
- exact composite foreign key `(brief_version_id, order_id, brief_content_hash)` -> `brief_versions(id, order_id, content_hash)`;
- no `is_approved` or `approved_at` columns.

This relation guarantees that a persisted TransformationSpec cannot claim a Brief id/order/hash combination absent from storage. It does not by itself mean either version is approved.

## approvals

Single table representing the approved immutable Approval entity.

Fields:

- `id` — primary key.
- `order_id` — required foreign key to `orders`.
- `target_type` — exactly `BRIEF` or `TRANSFORMATION_SPEC`.
- `target_version_id` — required.
- `target_content_hash` — required SHA-256.
- `context_brief_version_id` — nullable for BRIEF, required for TRANSFORMATION_SPEC.
- `context_brief_content_hash` — nullable for BRIEF, required for TRANSFORMATION_SPEC.
- `approved_by` — constant `local_user`.
- `approved_at` — required UTC datetime.

Context constraints:

- BRIEF Approval: both context fields must be null.
- TRANSFORMATION_SPEC Approval: both context fields must be non-null.

Exact-target insertion guard:

- BRIEF Approval is accepted only when `brief_versions` contains `(target_version_id, order_id, target_content_hash)` exactly.
- TRANSFORMATION_SPEC Approval is accepted only when `transformation_spec_versions` contains `(target_version_id, order_id, target_content_hash)` exactly and that spec's `brief_version_id/brief_content_hash` equals the Approval's `context_brief_version_id/context_brief_content_hash`.
- the context Brief must therefore be the exact Brief already referenced by the target spec; cross-order, stale-hash and unrelated-context approvals are rejected.

Because target table depends on `target_type`, this rule is enforced by a DB insertion guard in addition to repository validation rather than by one polymorphic foreign key.

Uniqueness is implemented with two SQLite partial unique indexes:

- BRIEF: unique `(target_type, target_version_id, target_content_hash)` for `target_type=BRIEF`;
- TRANSFORMATION_SPEC: unique `(target_type, target_version_id, target_content_hash, context_brief_version_id, context_brief_content_hash)` for `target_type=TRANSFORMATION_SPEC`.

Approval rows are append-only. Database-level guards reject UPDATE and DELETE.

## execution_runs

Fields follow the MVP-0 Implementation Scope v1.1 ExecutionRun contract:

- `id` — primary key.
- `order_id` — required foreign key.
- `brief_version_id` — required.
- `brief_approval_id` — required foreign key to Approval.
- `transformation_spec_version_id` — required.
- `transformation_approval_id` — required foreign key to Approval.
- `status` — exactly `running`, `succeeded`, `needs_fix`, `failed`, `cancelled`.
- `started_at` — required UTC datetime.
- `finished_at` — nullable UTC datetime.
- `input_snapshot_json` — required JSON.
- `metrics_json` — required JSON.
- `error_json` — nullable structured error JSON.

Candidate keys/relational constraints:

- unique `(id, order_id)` for EventLog same-order references;
- unique `(id, brief_version_id, transformation_spec_version_id)` for exact QAReport/run linkage;
- `(brief_version_id, order_id)` -> `brief_versions(id, order_id)`;
- `(transformation_spec_version_id, order_id)` -> `transformation_spec_versions(id, order_id)`.

Exact-reference insertion guard additionally requires all of the following atomically:

1. target TransformationSpec is bound to the same exact run Brief id/hash;
2. `brief_approval_id` identifies a BRIEF Approval with the same `order_id`, `target_version_id=brief_version_id` and `target_content_hash` equal to the current/recomputed stored Brief hash;
3. `transformation_approval_id` identifies a TRANSFORMATION_SPEC Approval with the same `order_id`, exact target spec id/hash and Brief context equal to the run Brief id/hash;
4. both Approval records therefore refer to the exact versions used by this run, not merely to versions in the same order.

Order/version/Approval reference fields and `started_at` are immutable after insert; a DB update guard rejects changes to them. Later stages may update only status/finished_at/metrics/error according to their approved behavior.

P1 does not start runs. The table exists so later stages have a durable target and P1 can prove restart persistence.

## artifacts

Fields:

- `id` — primary key.
- `run_id` — required foreign key to `execution_runs`.
- `artifact_type` — required non-empty text; concrete semantics are owned by the stage that creates the artifact.
- `format` — required non-empty text.
- `workspace_relpath` — required unique path.
- `checksum` — required SHA-256.
- `created_at` — required UTC datetime.

Artifact rows are append-only from the repository perspective; a new artifact never overwrites the metadata of an older artifact.

## qa_reports

Fields:

- `report_id` — primary key.
- `run_id` — required.
- `brief_version_id` — required.
- `transformation_spec_version_id` — required.
- `generated_at` — required UTC datetime.
- `overall_status` — exactly `PASS`, `PASS_WITH_WARNINGS` or `FAIL`.
- `report_json` — required complete QAReport contract instance.

Exact run/version constraint:

- composite foreign key `(run_id, brief_version_id, transformation_spec_version_id)` -> `execution_runs(id, brief_version_id, transformation_spec_version_id)`.

JSON/index rule:

- repository write validates `report_json` against the exact P0 QAReport schema and requires the indexed `report_id/run_id/brief_version_id/transformation_spec_version_id/generated_at/overall_status` to equal the corresponding document values;
- trust-boundary/recovery verification repeats critical JSON/index/run consistency checks.

P1 persists a report only; it contains no QA engine.

## event_log

Fields:

- `id` — primary key.
- `order_id` — required foreign key.
- `run_id` — nullable.
- `event_type` — required non-empty text.
- `payload_json` — nullable JSON.
- `created_at` — required UTC datetime.

Reference constraint:

- when `run_id` is non-null, composite foreign key `(run_id, order_id)` -> `execution_runs(id, order_id)` guarantees that an event cannot claim a run from another order.

EventLog is immutable. Database-level guards reject UPDATE and DELETE.

## Deliberately absent tables

P1 has no tables for:

- normalized dataset rows/cells;
- SourceDefinition network configuration;
- LLMInvocation;
- users/roles/sessions;
- task queues/workers;
- Telegram or marketplace entities;
- ingestion previews or parsed schemas;
- transformation-step execution data;
- QA check execution internals beyond persisted QAReport JSON.
