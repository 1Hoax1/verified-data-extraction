# P1 implementation traceability

This supplements, without modifying, the approved v1.0 traceability matrix.
All referenced P1 IDs executed and passed in the recorded validation run.

| Approved requirement | Implementation | Verification |
|---|---|---|
| P1-TR-001: Single local app, SQLite, filesystem, single user | src/vde/app.py; bootstrap.py; config.py | P1-T01, P1-T30 |
| P1-TR-002: P1 scope = skeleton, SQLite, migrations, workspace, models, repos, storage errors, restart/recovery | src/vde; tests/p1 | P1 release gate |
| P1-TR-003: SQLite stores metadata; datasets remain files | persistence/migrations/001_p1_baseline.sql; workspace.py | P1-T30 |
| P1-TR-004: Order persists approved 10-state model and approval_stage | models.py; persistence/repositories.py; baseline SQL | P1-T06, P1-T07 |
| P1-TR-005: Brief and TransformationSpec are separate versioned entities | models.py; contracts.py; VersionRepository; baseline SQL | P1-T11, P1-T12 |
| P1-TR-006: Versions contain no approval flags | version records; baseline SQL | P1-T14 |
| P1-TR-007: Approval is the sole immutable approval fact | ApprovalRepository; partial indexes; immutable triggers | P1-T15..P1-T18 |
| P1-TR-008: Approval targets exact existing version/hash in same order; Transformation Approval has exact Brief context | ApprovalRepository; approval_exact trigger | P1-T31, P1-T32 |
| P1-TR-009: Content hash uses validated P0 rules/vectors | contracts.py; VersionRepository | P1-T13, P1-T37..P1-T39 |
| P1-TR-010: ExecutionRun stores exact version and corresponding Approval refs | ExecutionRunRepository; run_exact and run_identity_immutable triggers | P1-T25, P1-T33 |
| P1-TR-011: Artifact/InputAsset bytes are filesystem-backed and never silently overwritten | workspace.py; storage.py | P1-T20..P1-T24, P1-T26 |
| P1-TR-012: QAReport persists but no QA engine exists in P1 | QAReportRepository (supplied report persistence only) | P1-T27, P1-T30 |
| P1-TR-013: QAReport indexed fields match report_json and exact ExecutionRun versions | QAReportRepository; composite foreign key | P1-T34, P1-T40 |
| P1-TR-014: EventLog is immutable chronology and run belongs to event order | EventLogRepository; immutable triggers; same-order FK | P1-T19, P1-T35 |
| P1-TR-015: Selected version references exist and belong to same Order | OrderRepository; composite foreign keys | P1-T36 |
| P1-TR-016: Data and critical invariants survive/revalidate on restart | bootstrap.py; recovery.py; verified repository loads | P1-T07, T08, T25-T29, T39-T40 |
| P1-TR-017: Storage failures use unchanged P0 structured error model | errors.py; repository boundary; bootstrap/recovery | P1-T03, T09, T22, T23, T29, T42 |
| P1-TR-018: File protocol = staging -> durable flush -> no-overwrite promotion -> DB UoW -> metadata + EventLog -> one commit | workspace.py; Storage; UnitOfWork | P1-T20, T21, T24, T41 |
| P1-TR-019: Authoritative version JSON validated against P0 schema/index/hash on write/trust boundary | contracts.py; VersionRepository; recovery.py | P1-T37..P1-T39 |
| P1-TR-020: No internal API/worker/queue | single app.py and local Python modules | P1-T30 |
| P1-TR-021: No P2 ingestion in P1 | opaque-byte storage APIs; no parsers | P1-T30 |
| P1-TR-022: No LLM/URL/JSON/Telegram/multi-dataset in Pilot P1 | scope audit; unchanged P0 pack | P1-T30 |
| P1-TR-023: P3 atomic APPROVED transition remains supportable by one transaction, but is not implemented in P1 | caller-owned UnitOfWork; full-record Order CAS; no P3 use case | design review; P3 tests later |
| P1-TR-024: Migration history is durable and restart-safe | database.py; schema_migrations | P1-T01..P1-T04 |
