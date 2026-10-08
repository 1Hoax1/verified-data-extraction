# P1 Traceability Matrix

| ID | Requirement | Source basis | P1 design artifact | Verification |
|---|---|---|---|---|
| P1-TR-001 | Single local app, SQLite, filesystem, single user | DECISIONS.md Approved architecture; Implementation Scope 5 | APPLICATION_SKELETON.md | P1-T01, P1-T30 |
| P1-TR-002 | P1 scope = skeleton, SQLite, migrations, workspace, models, repos, storage errors, restart/recovery | DECISIONS.md P1 | Whole pack | P1 release gate |
| P1-TR-003 | SQLite stores metadata; datasets remain files | Implementation Scope 2.3, 5.2; Product Spec 9 | SQLITE_SCHEMA.md; WORKSPACE.md | P1-T30 |
| P1-TR-004 | Order persists approved 10-state model and approval_stage | Implementation Scope 6, 7.1; P0 state registries | SQLITE_SCHEMA.md | P1-T06, P1-T07 |
| P1-TR-005 | Brief and TransformationSpec are separate versioned entities | Implementation Scope 7-9; DECISIONS.md Pilot | PERSISTENCE_MODELS.md; SQLITE_SCHEMA.md | P1-T11, P1-T12 |
| P1-TR-006 | Versions contain no approval flags | Implementation Scope 7.3, 8, 9; P0 trace TR-007/TR-008 | SQLITE_SCHEMA.md | P1-T14 |
| P1-TR-007 | Approval is the sole immutable approval fact | Implementation Scope 7.3; P0 approval schema/rules | SQLITE_SCHEMA.md; REPOSITORIES.md | P1-T15..P1-T18 |
| P1-TR-008 | Approval targets exact existing version/hash in same order; Transformation Approval has exact Brief context | Implementation Scope 6.3, 7.3; P0 approval rules | SQLITE_SCHEMA.md; REPOSITORIES.md | P1-T31, P1-T32 |
| P1-TR-009 | Content hash uses validated P0 rules/vectors | Implementation Scope 17.8; P0 manifest/validation | PERSISTENCE_MODELS.md | P1-T13, P1-T37..P1-T39 |
| P1-TR-010 | ExecutionRun stores exact version and corresponding Approval refs | Implementation Scope 7.4 | SQLITE_SCHEMA.md; REPOSITORIES.md | P1-T25, P1-T33 |
| P1-TR-011 | Artifact/InputAsset bytes are filesystem-backed and never silently overwritten | Product Spec 9.5/10; Implementation Scope error policy | WORKSPACE.md; TRANSACTIONS.md | P1-T20..P1-T24, P1-T26 |
| P1-TR-012 | QAReport persists but no QA engine exists in P1 | Implementation Scope 12, 18.1 P1/P5 separation | SQLITE_SCHEMA.md; SCOPE.md | P1-T27, P1-T30 |
| P1-TR-013 | QAReport indexed fields match report_json and exact ExecutionRun versions | Implementation Scope 12; P0 QAReport schema | PERSISTENCE_MODELS.md; SQLITE_SCHEMA.md; REPOSITORIES.md | P1-T34, P1-T40 |
| P1-TR-014 | EventLog is immutable chronology and run belongs to event order | Implementation Scope 7; Product Spec FR-17 | SQLITE_SCHEMA.md; REPOSITORIES.md | P1-T19, P1-T35 |
| P1-TR-015 | Selected version references exist and belong to same Order | Implementation Scope 7.1 | SQLITE_SCHEMA.md; REPOSITORIES.md | P1-T36 |
| P1-TR-016 | Data and critical invariants survive/revalidate on restart | Product Spec NFR-06; Implementation Scope Pilot readiness | RESTART_RECOVERY.md | P1-T07, T08, T25-T29, T39-T40 |
| P1-TR-017 | Storage failures use unchanged P0 structured error model | Implementation Scope 17.6; P0 execution-error schema/registry | STORAGE_ERRORS.md | P1-T03, T09, T22, T23, T29, T42 |
| P1-TR-018 | File protocol = staging -> durable flush -> no-overwrite promotion -> DB UoW -> metadata + EventLog -> one commit | Main-chat P1 review correction; P1 transaction design | TRANSACTIONS.md; WORKSPACE.md | P1-T20, T21, T24, T41 |
| P1-TR-019 | Authoritative version JSON validated against P0 schema/index/hash on write/trust boundary | Main-chat P1 review correction; P0 schemas/hash spec | PERSISTENCE_MODELS.md; REPOSITORIES.md | P1-T37..P1-T39 |
| P1-TR-020 | No internal API/worker/queue | Implementation Scope 5.2; DECISIONS.md | APPLICATION_SKELETON.md | P1-T30 |
| P1-TR-021 | No P2 ingestion in P1 | Implementation Scope 18.1: P2 depends on P1 | SCOPE.md; REPOSITORIES.md | P1-T30 |
| P1-TR-022 | No LLM/URL/JSON/Telegram/multi-dataset in Pilot P1 | DECISIONS.md Pilot; P0 validation conclusion | SCOPE.md | P1-T30 |
| P1-TR-023 | P3 atomic APPROVED transition remains supportable by one transaction, but is not implemented in P1 | Implementation Scope 6.3 | TRANSACTIONS.md | design review; P3 tests later |
| P1-TR-024 | Migration history is durable and restart-safe | DECISIONS.md P1; Implementation Scope 18.1 | MIGRATIONS.md | P1-T01..P1-T04 |
