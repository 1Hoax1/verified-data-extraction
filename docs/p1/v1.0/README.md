# P1 Implementation Pack v1.0 — Approved

Status: APPROVED
Release target: Pilot Slice V1
Stage: P1 — Persistence and workspace
Basis decision revision: P0_RESOLVED_2026-07-12
Review basis: main-chat review of P1 Implementation Pack v0.1 — CHANGES_REQUIRED; final review of v0.2 candidate — PASS

## Purpose

This pack defines the implementation boundary for P1 only. It converts the approved product, MVP scope, validated Pilot contract pack and DECISIONS.md into a concrete persistence/workspace design without implementing P2+ behavior.

Version 1.0 is the approved promotion of the corrected v0.2 candidate. The design changes relative to v0.1 are limited to the four mandatory P1 review corrections: exact-reference integrity, authoritative JSON integrity, the filesystem+DB transaction protocol, and strict reuse of the P0 storage-error contract. It does not revise P0 contracts or expand Pilot scope.

## Normative basis and precedence

1. Product Specification v0.1 — product intent and baseline requirements.
2. MVP-0 Implementation Scope v1.1 — executable scope and narrower first-release rules; it wins on first-release scope when narrower.
3. Pilot Slice V1 Contract Pack v1.0 — validated P0 JSON Schemas, registries, content-hash specification, approval semantics, error model and fixtures.
4. DECISIONS.md — current approved stage, architecture and P1 boundary.

No source document is changed by this pack. P0 schemas/registries/hash rules are consumed read-only and must not be redefined by P1.

## P1 deliverables

- application skeleton
- SQLite persistence schema and integrity guards
- migration policy
- local filesystem workspace policy
- persistence models and trust-boundary validation
- repository contracts
- transaction rules
- P0-compatible storage error mapping
- restart/recovery behavior
- P1 test plan
- P1 traceability matrix
- P1 release gate

## Review corrections applied in v0.2

1. Exact-reference integrity is specified for Approval, ExecutionRun, QAReport, EventLog and Order selected-version references, including same-order and exact-hash checks where required.
2. BriefVersion and TransformationSpecVersion JSON in SQLite remains the authoritative persisted copy; write and trust-boundary checks now explicitly require P0 schema validation, indexed-column/JSON consistency and content-hash recomputation. QAReport has equivalent JSON/index consistency rules.
3. The file protocol is fixed to: staging -> durable flush -> atomic no-overwrite promotion -> DB Unit of Work -> metadata + EventLog -> one commit. Collision and durability semantics are explicit.
4. Public storage failures now use only the validated P0 error contract: `code=STORAGE_ERROR`, `category=STORAGE`, no P1-defined top-level fields/codes/stage vocabulary. Internal storage reasons remain implementation-only.

## Explicit exclusions

P1 contains no CSV/XLSX parsing, sheet selection, schema preview, ingestion flow, TransformationSpec execution, transformation operations, export, deterministic QA engine, LLM calls, Telegram, network ingestion, marketplace integration, browser automation, background worker, task queue, multi-user/auth system or API service.

P1 also does not implement the P3 approval workflow or state-transition use cases. It provides only the persistence primitives and integrity constraints required by later approved stages.

## Pack contents

- `SCOPE.md`
- `APPLICATION_SKELETON.md`
- `SQLITE_SCHEMA.md`
- `MIGRATIONS.md`
- `WORKSPACE.md`
- `PERSISTENCE_MODELS.md`
- `REPOSITORIES.md`
- `TRANSACTIONS.md`
- `STORAGE_ERRORS.md`
- `RESTART_RECOVERY.md`
- `P1_TEST_PLAN.md`
- `TRACEABILITY_MATRIX.md`
- `P1_RELEASE_GATE.md`
- `OPEN_DECISIONS.md`
- `PACK_MANIFEST.json`
