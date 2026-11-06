# P6 Design Pack v0.2 — Minimal Streamlit E2E & release hardening

**Project:** Verified Data Extraction · **Release:** Pilot Slice V1 · **Date:** 2026-11-06  
**Status:** `PROPOSED / GATE A REVIEW`; **not approved for implementation**.  
**Frozen base:** `1Hoax1/verified-data-extraction`, `main:0af4a1ff49ccf8fa59c39780d749e15cb5042fc3`.  
**Owner authority:** P6 direction and Q01–Q03 APPROVED; CR-P6-001 APPROVED in feature branch record `4e1559c99817d16b842c81010ce528e191a14795`. **Gate A has not been closed**.  
**Normative basis:** Product Specification v0.1; MVP-0 Implementation Scope v1.1 §15, §18/P6 and Pilot release gate; P0 Contract Pack v1.0 and frozen P1–P5; `P6_GATE_A_FINALIZATION_v0.2_CANDIDATE.md`; owner CR decision. This pack supersedes the *candidate details* in P6 v0.1/v0.2 finalization where explicitly clarified below, without altering any approved P0–P5 rule.

## 1. Purpose, deliverables and boundaries

**P6 is mandatory for Pilot release**, solves the two known usability gaps—no Order-creation UI and no verified Result/QAReport download UI—and adds restart/corruption and release proof. A person must be able to follow **Create DRAFT Order → upload one CSV or one selected XLSX sheet → manually review/publish/approve BriefVersion → manually review/publish/approve linked TransformationSpecVersion → explicitly Execute P4 → explicitly run P5 → download checked result and QAReport** entirely within local Streamlit. A person, not the app, handles all marketplace messages, external transfer and billing.

**No scope expansion:** no new transforms/DQ checks/schemas, LLM, Telegram, URL/network ingestion, multiple datasets/users, workflow auto-approvals, web API, native macOS P2 rewrite, storage migration, external dependencies, generated code execution, business state, Approval role, PDF/DOCX export or customer auto-delivery. Reuse P1–P5 unmodified. P6 result is a Pilot Slice vertical slice, *not* MVP-0 Complete and not a market-demand validation.

**Runtime:** Linux; Apple Silicon/Intel Mac only via documented local Linux container (not native macOS). Single Streamlit process and one user, one SQLite and filesystem workspace. Supported file limits and QA authority are those already approved. P6 does not guarantee hard OS memory isolation or exact network-click-time disk verification.

## 2. Frozen scope and source contracts

Allowed **new runtime paths** (4):
- `src/vde/p6/__init__.py`
- `src/vde/p6/orders.py`
- `src/vde/p6/delivery.py`
- `src/vde/p6/ui.py`

Allowed **new test/audit paths** (6):
- `tests/p6/__init__.py`
- `tests/p6/conftest.py`
- `tests/p6/test_acceptance.py`
- `tests/p6/scope_audit.py`
- `tests/p6/scope_policy_v1.json`
- `tests/p6/run_validation.py`

Allowed **new design/release/decision paths** (5):
- `docs/p6/design/P6_DESIGN_PACK_v0.2.md`
- `docs/p6/decisions/P6_DIRECTION_OWNER_DECISION_2026-11-06.md`
- `docs/p6/decisions/CR-P6-001_OWNER_DECISION_2026-11-06.md` (already committed; never rewrite)
- `docs/p6/README_PILOT.md`
- `docs/p6/RELEASE_CHECKLIST.md`

**Evidence exception only:** finite actual runtime outputs in `docs/p6/validation/runtime-*/`, SHA-256 manifest, tested commit/tree, exact inputs, stdout/stderr, JUnit and results. **Only existing source edit**: exact four added lines in `src/vde/app.py`; no removal/reorder of existing lines:

Before original `from vde.ingestion.ui import panel`:
```python
from vde.p6.ui import order_panel
order_panel(result)
```
After the existing final `export_qa_panel(result)`:
```python
from vde.p6.ui import delivery_panel
delivery_panel(result)
```

The owner-approved CR-P6-001 is a *bounded exception* to frozen P5 inventory, not permission to change `tests/p5/scope_audit.py`, `tests/p5/scope_policy_v1.json`, `P5-T76`, original tests/fixtures/contracts, old evidence, `DECISIONS.md`, G3 pin, migration, dependency/lock, business semantics or source modules. A P6 successor audit must validate exact baseline blobs/modes and these exceptions.

## 3. P6-C01 — CreateOrder

**Input:** an explicitly submitted `st.form`, current runtime health, `request_token` (UUID4, generated when a new form is opened, and used as `OrderRecord.id`) and fields `title`, `listing_text`, optionally `listing_url`, `budget`, `deadline`, `notes`. `title` and `listing_text` must be strings with non-whitespace content. Required title may trim *outer* spaces **only by explicit form contract**; `listing_text` persists verbatim (no LLM, scraping or silent transformation). Absent optional inputs are `None`. Optional nonempty `budget` must already be finite canonical Decimal text accepted by frozen `verify_values`; invalid text yields UI validation error, not auto-rounding. Optional `deadline` must be an exact UTC `YYYY-MM-DDTHH:MM:SSZ`, not a silently converted local time. Other optional fields must match existing `OrderRecord` types; `listing_url` is stored as text only—no fetch.

**Preconditions:** `bootstrap/recover` currently `ready`; not just a stale bootstrap banner. The form is submitted by the user; rerenders never create Orders. User sees that a form submit creates a DRAFT, **not** a published/approved Brief or Spec. Existing P3 JSON editor remains the only way to create the approval versions.

**Operation:** one existing `UnitOfWork` and `OrderRepository` only; no migration/new deduplication table. **Check for existing token using a nonthrowing record-list/existence query in the same transaction (do not call `OrderRepository.get` for a missing key, since it marks the UoW rollback-only).** If absent, insert exactly one `OrderRecord(id=token, status='DRAFT', approval_stage=None, selected_brief_version_id=None, selected_transformation_spec_version_id=None, created_at=updated_at=utc_now(), other fields validated)`; commit via normal UoW. If present, compare persisted *user-input fields*, not later workflow status/timestamps: exact equality returns the prior `id` with zero business writes; any mismatch returns UI-only `P6_ORDER_TOKEN_CONFLICT` and zero writes. SQLite `BEGIN IMMEDIATE` serializes concurrent attempts; cannot create two Orders with the same ID. Generate **a new token only after success** or on an explicit new-Order action; a failed submit retains token. Browser session loss can lose the form token and does not create a persisted idempotency mapping.

**Output:** immutable Order ID; newly created DRAFT visible in unmodified P2/P3/P4/P5 selectors; creation creates **no** InputAsset, Brief, Spec, Approval, Run, Artifact, Event or QAReport. Separate duplicate user-created new token is a different Order by design.

**Errors:** `P6_INVALID_FORM` (UI only) for missing/invalid user fields or token; `P6_ORDER_TOKEN_CONFLICT`; `STORAGE_ERROR` for DB or workspace failures. All: fail closed, no partial/mismatched business rows; never silently replace data or write events.

## 4. P6-C02 — ReadOnlyDeliveryView

**Input:** explicitly selected `Order.id`, `Run.id`, current workspace health and existing `P5Service`. **No writes**, no QA recompute, no implicit approval or run. In a fresh UoW, verify the run belongs to this exact Order **before** any call that reads P4/P5 artifacts. Then require fresh `health == ready` and call `P5Service.read_decision(run_id)` (it independently checks persisted source, P4, final, two version hashes/Approvals, event and QA consistency). Do not use session cache as authority. No cross-Order run IDs or paths are accepted. For missing/invalid orders/runs, show generic safe diagnostics (never expose the other Order's bytes).

**Display:** Order/Run ID, approval version IDs and hashes, exact Approval provenance (without inventing identity), P5 status and QA overall, warnings, blocker count, row/column count, final `Artifact` type/format, checksum, file size. A reported `PASS_WITH_WARNINGS` is acceptable *only* when Order `READY` and no blockers; `NEEDS_FIX` must pair with QA `FAIL`.

**Output states:** `READY+PASS` or `READY+PASS_WITH_WARNINGS`: verified result and QA eligible; `NEEDS_FIX+FAIL`: a diagnostic file with conspicuous **NOT FOR DELIVERY** warning and the associated QA eligible; `FAILED`, `EXECUTING`, `APPROVED`, DRAFT, missing or inconsistent terminal records, `degraded`/`blocked`: no download or cached session authorization. UI rendering must be passive.

**Errors:** `P6_NOT_READY`, `P6_CROSS_ORDER`, `P6_INTEGRITY_FAILED`, existing `STORAGE_ERROR`, with zero business writes and zero exposed payload. Protect against stale selection changes and stale UI state.

## 5. P6-C03 — Verified Result or Diagnostic Download

**Input:** explicit **Prepare verified download** button, valid P6-C02 decision (not merely cached), approved Spec output filename/format, persisted P5 Artifact and workspace.

**Exact lifecycle:** (1) on prepare, invalidate any prior snapshot; (2) re-run P6-C02 and inspect the reported Artifact path using P1 controlled workspace API; (3) preflight file size and **conservative memory estimate** accounting for full payload, snapshot and Streamlit internal buffer; (4) read bytes from the exact Artifact path using controlled, verified access; calculate actual length and SHA-256, compare to both `Artifact.checksum` and `report.dataset_summary.checksum/file_size_bytes`; (5) recheck selection/context and budget, **then** store one immutable verified `bytes` snapshot plus exact `(order_id, run_id, artifact_id, checksum, overall_status, format)` key in `st.session_state`; (6) show `st.download_button` bound **only to those bytes**, never to an unverified path or file-like object. No additional Result Artifact and no workspace mutation.

**Invalidation:** any selected Order/Run change, new preparation request, failed health/context verification on subsequent rerender, error, restart or browser session loss clears snapshot. Clear the previous snapshot *before* loading another one. A click to download itself is only a transfer of prepared immutable bytes; **Streamlit cannot promise fresh disk verification at the last HTTP click**. A previously prepared copy is still valid as the verified copy even if underlying disk bytes change later; new prepare blocks on corruption. Documentation must disclose this snapshot boundary. Never claim last-click corruption detection by the static download button.

**Format and names:** `RESULT_CSV` or `RESULT_XLSX` only, matching approved Spec `output.format` and P5 decision. Safe display basename derived from approved `output.file_name`, reject traversal/separators/control characters and force approved extension/MIME (`text/csv`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`). `NEEDS_FIX` adds `_DIAGNOSTIC_NOT_FOR_DELIVERY` **before** file extension and a permanent red/yellow warning; cannot be represented as a client-ready delivery. Never publish internal `P4_INTERNAL` or `workspace_relpath` as a download.

**Resource and failure policy:** incrementally sampled **RSS ≤ 536870912 bytes above pre-preparation baseline** for P6; not an OS sandbox. Before materializing payload, check conservative total allocation = **at least 3 × file_size + serialized QA bytes + 64 MiB reserve**, against the remaining incremental budget; after reading/rebinding check actual sampled and current RSS again. The `3× + reserve` is a **P6 admission estimate**, not a reduction of allowed file size/rows or a guarantee of Streamlit internal duplication; stress test must measure actual peaks and fail closed if estimate is insufficient. Bound retained snapshots to **one selected run, one result bytes object and at most one report bytes object**; a new result or run clears the old. Refuse (`P6_DOWNLOAD_RESOURCE_LIMIT`) when the estimate/observed RSS would exceed budget, with zero transmitted payload, no state/QA changes; log the limit and file characteristics for owner review. If an approved ordinary Pilot workload cannot be served, open a new CR rather than weakening the Gate B test. No hard RAM guarantee; sampled RSS may miss transients.

**Failures:** missing or corrupted Result, Report/context drift, wrong MIME/extension, memory failure, altered file bytes ⇒ no new download object and no business writes. Verify the snapshot hash in tests and via independent download readback.

## 6. P6-C04 — Verified QAReport Download

**Input:** same selected terminal Order/Run, exact approved versions/Approvals and persisted `QAReportRecord` from P5 read-only result; explicit prepare (may share C03 preparation after checking the same view). Validate `report_json` against *existing* P0 `qa_report` schema, including exact `run_id`, version IDs and `report_id`; `report.artifacts` must identify the final Artifact verified by C03, and `dataset_summary` must match it. Use deterministic serialization: `json.dumps(report_json, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('utf-8')` (no rewriting report contents); reparse/check exact schema and linked identity in test. `.json`, MIME `application/json; charset=utf-8`, safe name `qa_report_<controlled_report_id>.json`. No new Artifact or stored file. Also available when `NEEDS_FIX` with QA `FAIL` (diagnostic labeling applies to associated Result). Unavailable for other or corrupt terminal states. Clear cached QA bytes together with Result on selection change. Memory for both buffers included in C03 conservative budget.

## 7. P6-C05 — Orchestration, restart, corruption and manuals

**Inputs:** existing P1–P5 UI commands, bootstrap health (`ready`, `degraded`, `blocked`), selected Order/Run and persisted workspace; no scheduler, queue, automation or self-repair. On `ready`, P6 order form and read-only downloads may work, but P2–P5 require their original **explicit human clicks**, including two separate legal P3 Approvals. `degraded` and `blocked`: no new business writes or downloads; display existing `recover` diagnostics (orphans/staging/stale run/errors) without rewriting state. New UI must not bypass old frozen health/recovery guards.

**Restart:** with the same mounted workspace, reread exact SQLite versions, approvals, runs, P5 QAReports and artifacts, but never reuse a prepared browser download snapshot; a new prepare is required. No automatic P4/P5 execution or additional approvals. Detect corrupted source/P4/final bytes using existing `recover` + P5 semantics; missing report/context/hashes, altered Approval or cross-run references ⇒ fail closed. Negative tests operate **only on disposable workspace copies**, never owner workspace or original P0 fixtures.

**Release documentation:** `docs/p6/README_PILOT.md` documents Linux install/bootstrap, Mac Docker (read-only repository, writable *same* persistent workspace), explicit workflow, editing P3 JSON in UI, result-vs-diagnostic interpretation, checkpoint/backup **with app stopped**, manual external delivery, permissions and limitations. `docs/p6/RELEASE_CHECKLIST.md` has measurable checks and evidence refs, installed dependencies from frozen lock, known macOS `/proc` constraint, absent P-C originals, rollback/recovery manual procedure, no automatic repair, exact package SHA/commit, and explicit owner release decision. No new scripts or deps without CR.

## 8. Fixed UI state and error policy

| Order / QA / health | Display & download policy | Business writes |
|---|---|---|
| `DRAFT`, `ANALYZING`, `READY_FOR_APPROVAL`, `APPROVED` etc., healthy | Route to original manual panels; no download | Only explicit P1–P5 operations |
| `EXECUTING`, healthy | P4/P5 progress; no download | Only explicit P4/P5 operations |
| `READY` + `PASS` or `PASS_WITH_WARNINGS`, healthy + verified | Result CSV/XLSX + QAReport; warning shown if applicable | **0** on view/prepare/download |
| `NEEDS_FIX` + `FAIL`, healthy + verified | **diagnostic, NOT FOR DELIVERY** + QAReport | **0** on view/prepare/download |
| `FAILED`, missing/inconsistent records | No download, diagnostic error | 0 |
| `degraded` or `blocked` | No create/download; show detect-only recovery | 0 |

**Error presentation (UI only; never add to P0 `execution_error` enum):**

| UI code | Trigger | Fail-closed behavior |
|---|---|---|
| `P6_INVALID_FORM` | Missing/invalid title, listing, token, budget, deadline or optional type | No Order and no partial state |
| `P6_ORDER_TOKEN_CONFLICT` | Same UUID token with different persisted user fields | Return error; zero writes |
| `P6_NOT_READY` | Ineligible Order/Run/status/report | No payload/QA bytes |
| `P6_CROSS_ORDER` | Selected Run belongs to different Order | No bytes, no other-Order details |
| `P6_INTEGRITY_FAILED` | Source, P4, P5, spec, Approval, final Artifact, QA Report inconsistencies | Clear prepared buffers; no payload |
| `P6_DOWNLOAD_RESOURCE_LIMIT` | Preflight or observed incremental RSS exceeds budget | No prepared download, no mutation |
| `STORAGE_ERROR` (existing) | Persistence/workspace failure / bootstrap blocked | Display established StorageError, no unsafe writes/repair |

**Exception mapping:** existing `P5Error`/`StorageError` and schema-validation failures → only safe summarized P6 UI message; never swallow a deterministic QA FAIL or mark it READY. Catch only expected error classes; unknown errors bubble/log for debugging, with no false success state. On failure clear buffers, preserve persisted bytes and exact user action logs (no new business EventLog).

## 9. Frozen fixture provenance and acceptance oracles

No P0 fixtures or goldens may be created/rewritten. Actual fixture *families* are `pecs/pilot_slice_v1/fixtures/P-A_dirty_csv`, `P-B_xlsx_sheet`, `P-C_approval_safety` and `P-D_errors_and_qa_blockers`. They are available in the tested `main` tree. **Thirteen missing original P-C files remain absent**; no substitute positives.

| Family | Source / reference files | Oracle and constraints |
|---|---|---|
| P-A | `P-A_dirty_csv/input_dirty.csv`, `brief_version.json`, `transformation_spec_version.json`, `expected_result.csv` | UI-created Order; manual P3 approvals; `READY/PASS` (per P5 accepted golden); exact resulting CSV bytes/headers/rows equal unchanged golden; P6-T04/05 |
| P-B | `P-B_xlsx_sheet/input_orders.xlsx`, Brief v1 and Spec v1 + **approved v2 specimen** `P5_Codex_Implementation_Handoff_2026-11-05.zip` SHA-256 `3e3a2f6a8e65f500fe5bd281ef805d9229d50b96c50433cdda52cbb4fd6d63e4` → nested `P5_Gate_A_PB_Supplement_v0.2b_candidate.zip` SHA-256 `4e08285b00344f2d00a7af89a723a835f931f4bceb768b11ec1aaf637fd0ae18` → `fixtures/P-B_versioned/transformation_spec_version_v2_CANDIDATE.json` | v2 must be *published and separately approved* after Brief; `READY/PASS_WITH_WARNINGS`, one `RESULT_XLSX`, 3×6, 18 data values, no exported formulas, DQ-017 `PB-AC-006/007 = PASS`; source formulas warning preserved; T06/07. No TEST_ONLY Approval accepted as real business authority. |
| P-D | `P-D_errors_and_qa_blockers/input_problematic.csv`, `brief_version.json`, `transformation_spec_version.json`, `expected_result.csv`, `expected_qa_report.json`, `semantic_error_cases.json` | Isolated negative: QA `FAIL`, Order `NEEDS_FIX`, associated clearly marked diagnostic + QAReport, no client-ready status; P6-T08; preserve P5 typed semantics, not raw-byte identity against diagnostic file unless frozen golden defines it |
| P-C | only files physically present under `P-C_approval_safety/` | Approval/hash/context negative guards and list of 13 absent originals; never claim complete positive golden coverage |
| Resource/recovery | frozen P5 stress evidence and generated artifacts with recorded hash/provenance; disposable fresh test workspaces | 100k×200 is a P5 export/QA proof, not proof of Streamlit browser delivery; tests measure actual P6 memory and safe denial independently |

**Identity adaptation rule for a UI-created Order:** the frozen fixture JSONs generally contain fixture-specific `order_id`, version IDs and source `asset_id`. An Order created by P6-C01 uses a fresh UUID4 and P2 creates its own input ID. Therefore tests **must not submit fixture JSON unchanged** if its Order/Asset does not match. In the isolated test workspace only, construct documented in-memory working copies replacing the specific Order and InputAsset bindings, and (where required) version IDs/references; recompute all affected P0 canonical content hashes and assert both Approvals match the actual derived version hashes. Preserve the original fixture bytes, semantic transformations, acceptance criteria, expected rows and golden results unchanged. Log the exact original SHA-256, each allowed metadata/identity substitution and resulting new SHA-256. An adapted P-B v2 may **not** claim the source specimen hash `c4f9aa33...` as its own hash unless the canonical payload actually matches. This adaptation is test-only input preparation, not an autonomous P3 approval or revision of certified P0 fixture data. Any semantic change beyond identity/context binding needs an explicit review.

Test-only fixture snippets can be injected into **isolated automated UI test sessions** to simulate deliberate test-user actions; they cannot serve as live customer Approvals, cannot overwrite a real user's workspace and cannot silently approve versions in production.

## 10. Fixed acceptance suite P6-T01…T20

Each unique ID requires a **runtime test on exact implementation SHA/tree**, raw JUnit outcome and an independent oracle, not only a static mention. Tests may use isolated ephemeral workspaces and a reproducible simulated *explicit* test-user action sequence. All passed means 20/20 mandatory IDs plus the required audits; a failure remains FAIL.

| ID | Action / test input | PASS oracle / records | Fixture or evidence |
|---|---|---|---|
| P6-T01 | Fresh Linux installed workspace + open Streamlit | `health=ready`; 0 Orders, 0 Approvals; UI shows CreateOrder; 0 automatic writes | temporary workspace; bootstrap/UI test |
| P6-T02 | Submit valid form with all required and optional fields | Exactly one DRAFT Order with exact user fields, generated token==id, `created_at=updated_at`, null selected versions, 0 associated asset/version/approval/run/report/event; visible in P2 | exact OrderRecord from SQLite |
| P6-T03 | Submit empty/invalid budget/deadline then rerender and reuse same token; concurrent replay with same/different fields | 0 invalid rows, no passive write; same payload returns same ID and row count; conflicting same token rejected; no duplicate under concurrent attempts | temp SQLite, two sessions |
| P6-T04 | UI-created P-A input, P3 publish/approve Brief, then publish/approve exact linked Spec (explicit test-user events) | Both Approvals separately required/recorded and exact hashes/context; P4 disabled until both; no invented/silent Approval | unchanged P-A specs/input, isolated UI actions |
| P6-T05 | Execute P-A P4 then P5 and prepare/download result/QA | READY/PASS, one production CSV exact 277-byte golden per P5, independent SHA and readback, QA valid, unchanged persisted rows on repeated transfer | P-A `expected_result.csv` |
| P6-T06 | P-B selected sheet Orders, real manual sequence with published approved Spec v2 | READY/PASS_WITH_WARNINGS, XLSX 3 rows×6 cols; 0 exported formulas; 24 DQ records, separate DQ-017 PB-AC-006/007 PASS; source formula warning, immutable exact versions | P-B v2 nested handoff specimen and XLSX |
| P6-T07 | Prepare/download P-B XLSX + saved QAReport | XLSX bytes checksum equals final P5 Artifact/report, one RESULT_XLSX, MIME/name correct, decoded 18 cells correct, no extra production CSV; JSON links exact Run/Artifact | P-B isolated workspace |
| P6-T08 | P-D negative through P4/P5 and prepare diagnostic | Order NEEDS_FIX/QA FAIL; only `_DIAGNOSTIC_NOT_FOR_DELIVERY` output and QA JSON, conspicuous warning, no READY/delivery wording | P-D input + expected QA |
| P6-T09 | No Run, DRAFT, FAILED, EXECUTING and missing approvals | All no-download, no READY promotion or new Approval/Artifact/Event | isolated state copies |
| P6-T10 | Restart Streamlit at intermediate P3 and terminal P5 milestones | Identical persisted Order/versions/Approvals/Run/QA/artifacts after restart, zero auto-execute, old prepared session not reused | P-A/P-B snapshots |
| P6-T11 | Mutate source CSV and XLSX in disposable workspace | Detect corruption by checksum; no downloads/writes/auto-repair, safe diagnostic | copies of P-A/P-B workspaces |
| P6-T12 | Mutate P4_INTERNAL and final Result separately | Each causes fail-closed: 0 payload, intact business rows/events; once verified snapshot exists, subsequent corruption is documented, future prepare fails | copies of P-A/P-B workspaces |
| P6-T13 | Cross-Order Run, mismatched Approval/hash/Spec/Run context | Reject before leaking report/bytes; no cross-Order data/details; 0 writes | two isolated Orders + mutations |
| P6-T14 | Missing QAReport, altered artifact metadata, degraded staging/orphan and blocked workspace | Correct health/error; disabled download/create, no unsafe repair | disposable recovery workspace |
| P6-T15 | Passive UI rerenders (≥3), re-prepare and repeat browser transfer | No new Order/Version/Approval/Run/Artifact/QA/Event, unchanged stored checksums; one in-memory snapshot per selected run | persisted counts/hashes before/after |
| P6-T16 | Verify content types, filenames, exact JSON schema, hash and replay/format | CSV/XLSX MIME+extension correct; QA deterministic UTF-8, link to one artifact, no path traversal, no unverified bytes | P-A/P-B/P-D output; invalid names |
| P6-T17 | Actual resource test with accepted small and large or admission-refused real generated artifacts | RSS sampling + conservative preflight recorded; allowed download reads correctly; rejected size yields `P6_DOWNLOAD_RESOURCE_LIMIT` and no partial/unsafe writes; if mandatory Pilot workload can't be served, test **FAIL pending CR**, not faux PASS | actual hashed P5 stress artefact, workspace temp |
| P6-T18 | P6 successor audit on exact tree, plus ≥1 mutation per protected-file class/forbidden extra path | All baseline bytes/modes except four approved UI lines match; only 4+6+5 finite paths and manifest evidence; negative changes rejected; historical scope conflicts classified by actual failing assertions, no hidden PASS | baseline main SHA, full Git inventory, JUnit |
| P6-T19 | Documentation smoke from clean Linux + Mac Docker launch | README commands work, mount persists SQLite and output after restart; workflow can be completed without hand-editing DB/files, native Mac not claimed | actual environment commands/logs |
| P6-T20 | Validation/release inventory and gate readiness | Full P6 20 IDs+JUnit+commands+SHA/tree, historical P1–P5 suites stated per exact tree, raw FAIL preserved, full known limitations and release checklist, owner Gate B still PENDING | SHA manifest + report/checklist |

**P6-T18 phase-aware regressions**: keep the previously run P1–P4 212/212 PASS and P5 76/76 PASS explicitly tied to their tested frozen refs; separately execute unchanged historical P1–P5 suites on actual P6 tree. The old P5-T76 inventory guard **may FAIL** against new paths; report actual failed tests, exact assertions, correct expected scope classifications, and any behavioral regressions as blockers; never rewrite test files or fake combined green counts. All original P0 schema/fixture negative guards unchanged. Resource and mutation tests are substantive runtime checks, not proof of release by document alone.

## 11. Gate criteria and authorized sequence

### Gate A — this stage (design and authority)
Required: (a) owner CR-P6-001 already APPROVED and verified on feature branch; (b) exact baseline/source whitelist and 4-line UI diff; (c) input/output/state/error policy for C01–C05; (d) all P6-T01…T20 with fixed fixtures and independent PASS/FAIL oracles; (e) known limitations documented; (f) independent static review report with actual completed checks; (g) **separate, explicit owner decision** `P6 Gate A: CLOSED / PASS`. **Creating this Design Pack alone does not satisfy (g)**. P6 code authoring requires **another owner start** after Gate A closes.

### Gate B — only after authorized implementation
All 20 tests actually executed, P1–P5 phase-aware regressions and raw failures, real CSV/XLSX and P-D, reproducible Linux/Mac container smoke, P0 schemas and recovery/limit checks, immutable evidence with commands/JUnit/manifests/actual SHA/tree, owner validation and explicit Gate B closure. Any blocking behavioral regression means Gate B not passed. Merge and Pilot release are **separate decisions**, not automatic follow-ons.

## 12. Known limitations and consequences of deferment

- Native macOS P2 reads Linux `/proc`; only Linux/Mac local container is supported for Pilot. No P2 patch authorized.
- Thirteen missing historical P-C originals preclude full P-C golden positive validation.
- Streamlit `download_button` serves a preverified session bytes object, not a dynamic final-click disk recheck. Prepared bytes remain checksum-verifiable but can be older than a subsequently corrupted on-disk source.
- Memory evidence is sampled incremental Linux RSS and preflight estimation, not isolation. P5 100k×200 successful export is not P6 browser-delivery proof. If admissible Pilot output cannot be downloaded under budget, block Gate B for owner decision.
- P6 Order token idempotency is session-scoped until submit; session loss before success can create a new token later and is not globally deduplicated by content.
- Original P5 inventory check on P6 tree may record a genuine FAIL; exact failure assertion and owner-authorized phase-aware classifier are required, not a skip/xfail.
- Post-P5 user scenario gives a verified P-B local workspace snapshot, **not** authorization for test automation to forge subsequent live approvals.

**Status recommendation:** `P6 Design Pack v0.2: PROPOSED / STATIC-REVIEWED`, `P6 Gate A: READY FOR OWNER DECISION` once the independent static review is actually completed; no P6 code written, no new approvals or stage closure inferred.
