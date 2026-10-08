# DECISIONS.md

## Current state

- Product Specification v0.1 — APPROVED
- MVP-0 Implementation Scope v1.1 — APPROVED
- Pilot Slice V1 Contract Pack v1.0 — VALIDATED
- P0 Formal Contracts and Fixtures — VALIDATED
- P1 Implementation Pack v1.0 — APPROVED
- Current release target — Pilot Slice V1
- Current stage — P1
- P1 — VALIDATED
- P1 completion/release gate — CLOSED (PASS, owner-confirmed 2026-10-08)
- P2 — NOT_STARTED; planning may begin under a separately approved scope

## Approved architecture

- Streamlit
- one Python application
- SQLite
- local filesystem
- single user

## Approved product constraints

- human performs all external marketplace actions
- no browser automation
- no marketplace authentication
- no automatic message sending
- no arbitrary LLM-generated code execution
- deterministic transformation engine
- deterministic QA is authoritative
- LLM cannot override deterministic FAIL

## Pilot Slice V1

- one local CSV or one XLSX sheet
- BriefVersion and TransformationSpecVersion are separate
- two mandatory Approval records
- fixed operation whitelist
- no LLM
- no URL ingestion
- no JSON ingestion
- no Telegram
- no multi-dataset processing

## Release history

### P0 — Formal Contracts and Fixtures
Status: VALIDATED

Evidence:
- Contract Pack v1.0
- validation_status: PASS
- schema_version: 1.1
- decision_revision: P0_RESOLVED_2026-07-12

### P1 — Persistence and workspace
Status: VALIDATED

Approved implementation basis:
- P1 Implementation Pack v1.0 — APPROVED
- decision_revision: P1_PACK_APPROVED_2026-10-05
- implementation start gate: OPEN at design approval (historical)
- implementation code had not started at design approval time
- P1 completion/release gate: CLOSED (PASS) on 2026-10-08 by explicit owner confirmation
- decision_revision: P1_VALIDATED_2026-10-08

Scope:
- application skeleton
- SQLite
- migrations
- local filesystem workspace
- persistence models
- repositories
- storage errors
- restart/recovery tests

Approved P1 implementation decisions:
- D1: standard-library SQLite + explicit repositories/Unit of Work; no ORM
- D2: WAL + synchronous=FULL + foreign keys
- D3: BriefVersion/TransformationSpecVersion JSON is authoritative in SQLite, with mandatory P0 schema/index/hash consistency checks
- D4: database stores workspace-relative paths only
- D5: file protocol is staging -> durable flush -> atomic no-overwrite promotion -> DB Unit of Work -> metadata + EventLog -> one commit
- D6: DB guards enforce immutable Approval and EventLog
- D7: Approval uniqueness uses partial unique indexes appropriate to nullable Brief context
- D8: restart only detects stale running ExecutionRun; no automatic resume or business-state mutation

Validation and merge evidence:
- PR #1: https://github.com/1Hoax1/verified-data-extraction/pull/1 — merged 2026-10-08
- main merge commit: 258bc593e71dbf7bcafc53486998b318c4265e9f
- approved design: docs/p1/v1.0/ (unchanged)
- P1 validation report: docs/p1/validation/P1_VALIDATION_REPORT.md
- implementation traceability: docs/p1/validation/IMPLEMENTATION_TRACEABILITY.md
- JUnit test evidence: docs/p1/validation/p1-results.xml
- test run of implementation b88b0da: P1-T01..P1-T42, 42 PASS, 0 FAIL, 0 errors, 0 skipped, 0 xfail
- review confirmed that changes after b88b0da and before merge concerned only documentation and validation evidence, not implementation code
- architecture/release-gate review: PASS; no blocking P1 findings, no scope expansion and no Change Request
- independent test rerun and GitHub Actions CI were not performed; the recorded Codex/pytest/JUnit evidence was accepted for closure

Known limitations accepted for the P1 gate:
- Linux/overlayfs process-crash and filesystem durability exercised; physical power loss, Windows and network filesystems not validated
- local single-user/process design; no adversarial concurrent filesystem-mutation guarantee
- recovery is detect-only and reports the first blocker; no automatic repair, adoption or execution resume
- large-file streaming, ingestion, transformations and QA computation are outside P1
- only baseline migration was implemented; a future upgrade failure was fault-injected
- standalone wheel/independent cloud-environment distribution was not validated; editable install reads the repository's P0 pack
- Product Specification PDF and MVP-0 Scope DOCX GitHub paths remain placeholder files; actual source documents were used as provided separately

P1 is closed and VALIDATED. P2 planning can be prepared, but P2 scope, contracts, fixtures, acceptance criteria and implementation start require their own explicit approvals before coding.

