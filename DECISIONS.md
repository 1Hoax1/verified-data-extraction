# DECISIONS.md

## Current state

- Product Specification v0.1 — APPROVED
- MVP-0 Implementation Scope v1.1 — APPROVED
- Pilot Slice V1 Contract Pack v1.0 — VALIDATED
- P0 Formal Contracts and Fixtures — VALIDATED
- Current release target — Pilot Slice V1
- Current stage — P1
- P1 — APPROVED_TO_START

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

Scope:
- application skeleton
- SQLite
- migrations
- local filesystem workspace
- persistence models
- repositories
- storage errors
- restart/recovery tests

Do not begin P2 until P1 passes its release gate.
