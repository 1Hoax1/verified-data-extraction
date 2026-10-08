# P1 Test Plan

All tests are P1-only. Validated P0 schemas, registries, fixtures and hash vectors are immutable test inputs. No test invokes ingestion, transformation, QA computation, LLM or network code.

| ID | Test | Expected result |
|---|---|---|
| P1-T01 | Clean bootstrap | Workspace and baseline DB are created; migration history records baseline. |
| P1-T02 | Idempotent bootstrap | Second startup makes no schema/data changes. |
| P1-T03 | Migration checksum drift | Startup is blocked through a P0-valid `STORAGE_ERROR`; no migration is silently replaced. |
| P1-T04 | Failed migration rollback | Baseline schema remains usable; no partial migration state. |
| P1-T05 | Foreign-key enforcement | Cross-reference to missing relational parent is rejected and transaction rolls back. |
| P1-T06 | Exact 10 Order states / 3 approval stages | Unknown value is rejected by persistence constraint. |
| P1-T07 | Order round-trip across restart | All persisted Order fields reload unchanged after process restart. |
| P1-T08 | InputAsset byte round-trip | Stored bytes, size, path and SHA-256 match after restart. |
| P1-T09 | Workspace path traversal | Absolute/`..`/outside-root path is rejected through P0 `STORAGE_ERROR`. |
| P1-T10 | Workspace relocation | DB-relative paths remain valid after moving the whole workspace root. |
| P1-T11 | BriefVersion append-only repository | v1 persists; a changed payload requires v2; no in-place repository update API. |
| P1-T12 | TransformationSpec exact Brief link | Unknown/wrong Brief id/order/hash combination is rejected. |
| P1-T13 | P0 hash vector persistence | Loaded version recalculates to the exact validated P0 hash vector. |
| P1-T14 | No approval fields in versions | Persistence schema/model contains no `is_approved` or `approved_at` on version tables. |
| P1-T15 | BRIEF Approval duplicate | Duplicate exact approval is rejected despite null context fields. |
| P1-T16 | Transformation Approval duplicate/context | Duplicate exact approval and missing context are rejected. |
| P1-T17 | Approval immutability | UPDATE and DELETE fail at repository and DB-guard level. |
| P1-T18 | Approval validity after changed/corrupt content | Recalculated mismatching hash yields no valid Approval and corruption is reported. |
| P1-T19 | EventLog immutability/order | UPDATE/DELETE fail; reads preserve chronological ordering. |
| P1-T20 | File-write crash before promotion | Only staging/quarantine data exists; no DB reference is created. |
| P1-T21 | File-write crash after promotion/before DB UoW commit | Orphan final file is detected on restart; no DB row is invented. |
| P1-T22 | DB-referenced file missing | Recovery emits P0-valid `STORAGE_ERROR`; metadata is not silently deleted. |
| P1-T23 | DB-referenced checksum mismatch | Recovery emits P0-valid `STORAGE_ERROR`; stored checksum is not rewritten. |
| P1-T24 | Atomic final-path collision | Existing payload is not overwritten/adopted; promotion fails safely. |
| P1-T25 | ExecutionRun round-trip | Exact reference fields/status/input snapshot/metrics/error persist across restart. |
| P1-T26 | Artifact round-trip | Artifact metadata and bytes survive restart; older artifact is never overwritten. |
| P1-T27 | QAReport round-trip | Complete stored report JSON and indexed fields reload unchanged. |
| P1-T28 | Stale running run | Restart detects it but does not auto-resume, auto-fail or mutate business state. |
| P1-T29 | DB integrity failure | Write-capable startup is blocked; no auto-rebuild. |
| P1-T30 | P1 scope audit | No P2+ module, network call, LLM, Telegram, marketplace, queue/worker, dataset-row table or API service exists. |
| P1-T31 | BRIEF Approval exact target DB guard | Direct/raw insert with nonexistent target, cross-order target or wrong `target_content_hash` is rejected by DB guard. |
| P1-T32 | Transformation Approval exact target/context DB guard | Direct/raw insert with wrong spec hash, wrong order, wrong Brief id/hash context or context unrelated to target spec is rejected. |
| P1-T33 | ExecutionRun exact references DB guard | Direct/raw insert with wrong Brief Approval, wrong spec Approval, cross-order version, stale target hash or spec bound to another Brief is rejected. |
| P1-T34 | QAReport exact run/version relation | Report whose indexed run/version tuple differs from ExecutionRun is rejected. |
| P1-T35 | EventLog run/order integrity | Event with `run_id` belonging to another order is rejected. |
| P1-T36 | Selected version same-order integrity | Order cannot select Brief/TransformationSpec belonging to another order or nonexistent version. |
| P1-T37 | Brief authoritative JSON write validation | Schema-invalid document, JSON/index identity mismatch or recomputed-hash mismatch is rejected before persistence. |
| P1-T38 | Transformation authoritative JSON write validation | Schema-invalid document, JSON/index mismatch, hash mismatch or wrong stored Brief exact reference is rejected. |
| P1-T39 | Version trust-boundary/recovery validation | Deliberately corrupted stored JSON/index/hash is detected; record is not normalized or silently repaired. |
| P1-T40 | QAReport JSON/index validation | P0-schema-invalid report or report_json/index identity/status mismatch is rejected; recovery detects persisted corruption. |
| P1-T41 | File metadata + EventLog single-commit atomicity | Injected EventLog/metadata DB failure rolls back both DB writes; promoted file remains only as recoverable orphan. No metadata-only commit occurs. |
| P1-T42 | Public storage-error contract compliance | Representative storage failures validate against exact P0 error schema/registries with `code=STORAGE_ERROR`, `category=STORAGE`; no P1-only top-level code/field/stage is emitted. |

## Test fixture policy

- Use P0 P-C approval/hash cases to verify persistence does not weaken Approval semantics.
- Use validated P0 content-hash vectors for hash verification.
- Use P0 BriefVersion, TransformationSpecVersion, Approval and QAReport schemas directly for write/trust-boundary tests.
- Use tiny synthetic binary payloads for workspace/atomic-write tests; parsing their contents is forbidden in P1 tests.

## Required P1 test layers

- unit tests for path normalization, P0 error mapping and record/document mapping;
- SQLite integration tests with a temporary real database, including raw-write attempts against DB guards;
- filesystem integration tests on a temporary real workspace, including collision/no-overwrite behavior;
- transaction fault-injection tests proving metadata + EventLog share one commit;
- restart tests that close all connections/process-level resources and reopen from disk;
- migration tests from empty DB and from the immediately previous schema state when future migrations are added.
