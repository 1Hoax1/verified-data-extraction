# Migration Policy

## Strategy

P1 uses ordered, forward-only SQLite migrations packaged with the single Python application. No external migration service is introduced.

The first migration is the P1 baseline and creates only the tables, constraints, indexes and database guards described in `SQLITE_SCHEMA.md`.

## Rules

- Database schema version is independent from P0 contract `schema_version=1.1`.
- Every migration has a monotonically increasing integer version, immutable name and SHA-256 checksum.
- An applied migration is never edited in place.
- On startup, applied migration checksums are compared with packaged definitions.
- Checksum mismatch, unknown applied version or failed migration blocks write-capable startup through the P0 `STORAGE_ERROR` contract.
- Each migration must be transactional where SQLite permits it. Failure rolls back the migration rather than leaving a partially upgraded schema.
- Migrations do not perform ingestion, transformation, QA computation or network work.
- Destructive down-migrations are not part of P1 runtime behavior.
- Schema changes after P1 approval require a new migration and traceability update.

## Baseline migration contents

`001_p1_baseline` creates:

- `schema_migrations`
- `orders`
- `input_assets`
- `brief_versions`
- `transformation_spec_versions`
- `approvals`
- `execution_runs`
- `artifacts`
- `qa_reports`
- `event_log`
- required primary/foreign/composite candidate keys and indexes
- partial unique Approval indexes
- same-order selected-version foreign keys
- exact run/version and event/run reference constraints
- Approval exact-target/context insertion guards
- ExecutionRun exact version/Approval insertion guards
- ExecutionRun reference-field immutability guard
- immutable-table guards for Approval and EventLog

The polymorphic Approval target relation cannot be expressed by a single ordinary SQLite foreign key; the baseline therefore requires database insertion guards whose semantics are specified in `SQLITE_SCHEMA.md`. These guards enforce existing P0 semantics and do not introduce a new product rule.

## Startup migration gate

No repository is made available to the application until migration verification succeeds.
