# DECISIONS.md

## Current state

- Product Specification v0.1 — APPROVED
- MVP-0 Implementation Scope v1.1 — APPROVED
- Pilot Slice V1 Contract Pack v1.0 — VALIDATED
- P0 Formal Contracts and Fixtures — VALIDATED
- P1 Implementation Pack v1.0 — APPROVED
- Current release target — Pilot Slice V1
- Current stage — P1
- P1 — APPROVED_TO_START
- P1 implementation start gate — OPEN

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
Status: APPROVED_TO_START

Approved implementation basis:
- P1 Implementation Pack v1.0 — APPROVED
- decision_revision: P1_PACK_APPROVED_2026-10-05
- implementation start gate: OPEN
- implementation code has not started at approval time
- P1 completion/release gate is not yet passed; it requires implemented code, P1-T01..P1-T42, validation evidence and explicit owner closure

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

Do not begin P2 until P1 passes its release gate.
