# P1 Release Gate

P1 may be marked complete only when all conditions below pass. P1 Implementation Pack v1.0 is APPROVED as the implementation specification and opens the P1 implementation-start gate. This approval does not close the P1 completion/release gate; that requires implemented code and the evidence below.

## Functional persistence gate

- Clean local bootstrap creates the exact P1 schema and workspace.
- Every P1 entity can be persisted/reloaded through repositories.
- All durable P1 records and registered files survive process restart.
- P0 content-hash vectors still match after persistence round-trip.
- BriefVersion/TransformationSpecVersion writes validate against exact P0 schemas, indexed columns match authoritative JSON, and content hashes recompute exactly.
- QAReport writes validate against the exact P0 schema and indexed identity/status fields match `report_json`.
- Approval remains the only stored source of approval truth.
- BRIEF Approval exact target/order/hash and TRANSFORMATION_SPEC Approval exact target/order/hash/Brief-context are enforced at repository and DB-guard level.
- ExecutionRun exact Brief/TransformationSpec/Approval relationships are enforced at repository and DB-guard level; immutable reference fields cannot be retargeted after insert.
- QAReport exact run/version relation, EventLog run/order relation and Order selected-version same-order relation are enforced.
- SQLite contains no generic dataset-row/cell storage.
- Workspace paths are relative and confined to the configured root.
- File writes follow exactly: staging -> durable flush -> atomic no-overwrite promotion -> DB UoW -> metadata + EventLog -> one commit.
- Final-path collision never overwrites or auto-adopts existing payloads.
- A DB failure while inserting metadata/EventLog leaves no partial DB commit; any already promoted file is recoverable only as an orphan.
- Migration verification is repeatable and detects drift.
- Recovery detects staging leftovers, orphan files, missing files, checksum mismatch and persisted contract/index/hash corruption without silently changing business data.
- Stale `running` ExecutionRun is detected but not auto-resumed or auto-mutated.
- Representative storage failures validate against the unchanged P0 error model with `code=STORAGE_ERROR`, `category=STORAGE`; no P1-only public top-level code/field/stage exists.

## Scope gate

The repository contains no implemented P2+ behavior: no CSV/XLSX parsing, no sheet selection, no preview, no transformation engine, no export/QA engine, no LLM, no URL/JSON/HTML ingestion, no Telegram, no marketplace integration, no worker/queue/API service.

P0 schema/hash validation used at persistence trust boundaries is allowed and is not P2/P3 workflow implementation.

## Test gate

All tests P1-T01 through P1-T42 pass on a clean local environment. Any skipped test requires an explicit owner decision before P2 starts.

In addition, the release evidence must include:

- test run summary with exact pass/fail counts;
- migration checksum/integrity result;
- P0 schema/hash-vector validation evidence used by P1 tests;
- explicit scope audit result;
- known limitations, especially host-filesystem durability limitations if any.

## Handoff to P2

P2 may begin only after P1 implementation passes this gate and the owner explicitly closes P1. P2 consumes the P1 InputAsset/workspace/repository contracts but must not bypass them by writing arbitrary paths or raw SQLite rows.
