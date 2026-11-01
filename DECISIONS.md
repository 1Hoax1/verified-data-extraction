# DECISIONS.md

## Current state

- Product Specification v0.1 — APPROVED
- MVP-0 Implementation Scope v1.1 — APPROVED
- Pilot Slice V1 Contract Pack v1.0 — VALIDATED
- P0 Formal Contracts and Fixtures — VALIDATED
- P1 Implementation Pack v1.0 — APPROVED
- Current release target — Pilot Slice V1
- Current stage — P4 Implementation Start Gate OPEN / AUTHORIZED (Gate A CLOSED / PASS, approved ZIP VERIFIED; Gate B NOT_RUN)
- P1 — VALIDATED
- P1 completion/release gate — CLOSED (PASS, owner-confirmed 2026-10-08)
- P2 Implementation Pack v1.0 — APPROVED
- P2 — VALIDATED (Gate B CLOSED / PASS, owner-confirmed 2026-10-11)
- CR-P2-001 — APPROVED and implemented (validated under P2 Gate B)
- P2 Gate A — CLOSED (PASS, owner-confirmed 2026-10-11)
- P2 implementation start gate — historical OPEN at Gate A; implementation merged
- P2 Gate B — CLOSED (PASS, owner-confirmed 2026-10-11)
- P3 — VALIDATED (Gate B CLOSED / PASS, owner-confirmed 2026-10-11)
- P3 Implementation Pack v1.0 — APPROVED (owner-confirmed 2026-10-11)
- P3 Gate A — CLOSED (PASS, owner-confirmed 2026-10-11)
- P3 implementation start gate — historical OPEN (owner-authorized 2026-10-11; implementation merged)
- P3 Gate B — CLOSED / PASS (owner-confirmed 2026-10-11)
- CR-P3-001 — DEFERRED (no P0 state graph change)
- CR-P3-002 — APPROVED / IMPLEMENTED / VALIDATED (P3 Gate B; P2-T40 phase-scoped, P3-T51 full application)
- P4 — IN_IMPLEMENTATION (implementation start owner-authorized 2026-10-30; Gate A APPROVED; no P4 runtime/code or tests yet committed)
- P4 Implementation Pack v1.0 — APPROVED (GitHub ZIP upload VERIFIED, exact 112649 B and SHA-256; implementation authorized separately)
- P4 Gate A — CLOSED / PASS (owner-confirmed 2026-10-30)
- P4 implementation start gate — OPEN / AUTHORIZED (owner-confirmed 2026-10-30; no auto-merge, Gate B NOT_RUN)
- P4 Gate B — NOT_RUN / NOT_PASSED
- CR-P4-001 — APPROVED (test-boundary only; NOT_IMPLEMENTED)
- CR-P4-002 — APPROVED (owner-confirmed MAIN CHAT 2026-10-30; P4-T13 expects 4 P-B source rows, P4-T42 still 3 final; implementation in Draft PR #4, NOT_VALIDATED)
- CR-P4-003 — APPROVED (owner-confirmed MAIN CHAT 2026-10-30; test-only changed-path diff baseline for P2-T40/P3-T51 to P4 start 76851105…; negative checks retained; NOT_VALIDATED)
- CR-P4-004 — APPROVED (owner-confirmed MAIN CHAT 2026-10-30; correct negative proper fraction Decimal wire grammar and tests; NOT_VALIDATED)
- CR-P4-005 — APPROVED (owner-confirmed MAIN CHAT 2026-11-01; exact DECISIONS governance pin + historical integration audit, TEST-ONLY; NOT_IMPLEMENTED / NOT_VALIDATED)
- P4-Q01..Q05 and Q07 — APPROVED (Q03 revised signed64 / V2 / Unicode)
- P4-Q06 — DEFERRED (CR-P3-001 unchanged)

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

P1 is closed and VALIDATED. P2 design and implementation start were separately approved on 2026-10-11. P1 constraints stay in force.

### P2 — Local CSV/XLSX ingestion
Status: VALIDATED (Gate B CLOSED / PASS, owner-confirmed 2026-10-11)

Decision and design basis:
- P2 Implementation Pack v1.0 — APPROVED; owner confirmation: 2026-10-11.
- decision_revision: P2_PACK_APPROVED_2026-10-11
- P2-D01..P2-D13 and P2-Q01..P2-Q05: APPROVED as a single Gate A decision set.
- Gate A: CLOSED / PASS. P2 implementation start gate: OPEN (only P2 scope).
- Historical initial draft evidence (retained in docs/p2/validation/history/initial/): 49 P2 PASS / 4 FAIL / T54 NOT_RUN; 41 P1 PASS / 1 FAIL, before approved CR-P2-001 was implemented.
- Final Gate B evidence: P2-T01..P2-T54 54 PASS, P1-T01..P1-T42 42 PASS, 0 FAIL, 0 ERROR, 0 SKIP; P0 golden previews PASS; P2 fixtures/manifest PASS.
- Final tested implementation commit: a6c845b552656b42d81850fc3372871df979f6c2; the later PR head and merge changed validation/evidence files only, not executable source or tests.
- PR #2 merged 2026-10-11T08:13:28Z, head d5277b633d7611a98cc48983898cf681bb8dc590, merge commit e5b2d3cd5a1c26650802c23191046eafdfecef3c.
- Actual P2 test evidence: docs/p2/validation/p2-results.xml; P1 regression: docs/p2/validation/p1-results.xml; full logs/traceability: docs/p2/validation/.
- Resource evidence: tests/p2/rss_probe.py; CSV incremental RSS 198189056 bytes, XLSX incremental RSS 150138880 bytes, both below 536870912 bytes in tested Linux environment.
- CR-P2-001 phase-scoped P1-T30 audit and whole-application P2-T40 scope audit: implemented and passed, original P1 v1.0 pack preserved.
- P2 release gate closure record: docs/p2/validation/P2_GATE_B_CLOSURE.md; decision_revision: P2_VALIDATED_2026-10-11.
- Reviewed baseline: main 1a51c3605fc69c758d9cabd0eab0246c4c386870.
- Approved package: P2_Implementation_Pack_v1.0_APPROVED.zip, SHA-256 1fed602bcea695be892150581b9cbcb00807681f0a389f598bd54fac9e504d84.
- Gate A approval record: docs/p2/v1.0/GATE_A_APPROVAL.md.
- Complete binary ZIP uploaded to GitHub at docs/p2/v1.0/P2_Implementation_Pack_v1.0_APPROVED.zip; Git blob SHA-1: 62e4e6bdcc20db52f94ff549496bb0ac50799acd, size 308846 bytes (verified before PR #2).

Approved P2 scope:
- one local CSV or one explicitly selected XLSX sheet; explicit CSV encoding/delimiter and no automatic detection.
- exact P0 preview, full bounded scan, safe OOXML cached formula handling, source byte hashes via P1 Storage/InputAsset.
- minimal Streamlit upload/preview for existing P1 Order; no Order creation UI.
- no SQLite migrations, P0/P1 contract changes, P3 approval workflow, P4/P5 engine/export/QA, URL/API/JSON, LLM, Telegram, marketplace automation or workers.
- resource limits include 100 MB raw input, ZIP member/ratio caps and measured incremental peak RSS <=512 MiB.

Gate A review and accepted limits:
- ZIP/manifest checks PASS; 21 deterministic binary XLSX and 12 CSV fixtures; 54 planned P2 test IDs; corrected P2-T53 fixture is preflight-reachable.
- Stale checksum-catalog SHA in v0.3 report corrected in approved v1.0; no fixture, ingestion policy, P0 or P1 normative changes in the approval revision.
- Change Request: NOT_REQUIRED.
- Historical Gate A note: reader/runtime checks were not yet run at design approval; superseded for P2 Gate B by final PASS evidence above.
- Accepted limitations: Linux/overlayfs Python 3.12.14 / openpyxl 3.1.5 only; Windows/network FS/power-loss unvalidated; RSS sampled (not hard sandbox), source bytes whole-buffered via P1; XLSX formula cache is never recalculated; parser/private-API upgrades require revalidation; browser-native upload chooser and independent-host/CI rerun unvalidated; P1 recovery remains detect-only.

Gate B completed on 2026-10-11 after owner confirmation and the recorded tests/review. P2 is VALIDATED; no scope expansion or additional CR. P3 design preparation may begin, but P3 implementation requires its own approved pack, acceptance tests, fixtures and start gate.

### CR-P2-001 — Phase-scoped P1-T30 regression audit
Status: APPROVED (owner-confirmed 2026-10-11)

- Change Request: docs/change_requests/CR-P2-001.md
- Reason: validated P1-T30 historically audited all `src/vde/**/*.py` for absence of P2+ imports; approved P2 necessarily introduces `csv` and `openpyxl` in `src/vde/ingestion/`. The current unmodified test fails as designed when P2 is added.
- Decision: retain P1-T30 and its ID; restrict its historical P1-scope assertions to the explicitly enumerated P1 subsystem/module set, excluding the P2 integration entry point. Maintain all P1 persistence/approval/hash/recovery invariants. Add/strengthen full-application P2 scope audit for forbidden P3+ features, prohibited services/dependencies and unauthorized migrations.
- Authorization: change test/test-plan boundary only, using a traceable versioned amendment; do NOT alter approved P1 v1.0 pack, P0 contracts, production P1 persistence/runtime, Pilot whitelist, approval semantics or SQLite schema.
- Scope: corrective work in existing draft PR #2, including zlib error mapping, P2 test harness fixes, full P2 and P1 rerun and RSS measurement.
- Consequence of no change: P2 Gate B could not simultaneously require P2 readers and 42/42 P1 regression PASS.
- Validation: P1-T01..P1-T42 42 PASS including phase-scoped P1-T30, P2-T01..P2-T54 54 PASS including new full-app scope audit, P0 golden equality, RSS <= 536870912 incremental bytes, validation report and owner Gate B closure.
- No Change Request scope enlargement. CR approval is NOT P2 Gate B approval, NOT a merge authorization, and NOT P2 VALIDATED.


### P3 — Manual BriefVersion / TransformationSpecVersion / two Approval
Status: VALIDATED (Gate B CLOSED / PASS, owner-confirmed 2026-10-11)

Design and Gate A approval:
- P3 Implementation Pack v1.0 — APPROVED on 2026-10-11, based on reviewed P3 v0.3 candidate.
- decision_revision: P3_PACK_APPROVED_2026-10-11
- Gate A: CLOSED / PASS, explicit main-chat owner confirmation 2026-10-11.
- Gate A owner approval (historical) covered design pack + CR decisions only; subsequent separate implementation start authorization granted on 2026-10-11. Start gate OPEN; code not yet written. See docs/p3/v1.0/IMPLEMENTATION_START_AUTHORIZATION.md.
- Gate B: CLOSED / PASS (2026-10-11), after actual acceptance validation and explicit owner confirmation. P3-T01..P3-T52: 52 PASS; P2-T01..P2-T54: 54 PASS; P1-T01..P1-T42: 42 PASS; 0 FAIL/ERROR/SKIP/XFAIL.
- PR #3 merged on 2026-10-11T16:46:13Z; head 23e69b8fa65d5193e3462bbf9df155173d6c7e15; main merge commit aa513780594595c3f5fb3cda15060ecd51b9e00f.
- Exact tested implementation commit: 6a8e67252131c2b6a6a70388aa47ead899c35140. Diff from tested commit through the merge consists only of docs/p3/validation/ evidence; source, tests, dependencies and frozen P0/P1/P2 remain unchanged.
- P3 Gate B closure: docs/p3/validation/P3_GATE_B_CLOSURE.md; decision_revision: P3_VALIDATED_2026-10-11.
- Validation: docs/p3/validation/P3_VALIDATION_REPORT.md, p3-results.xml, p2-results.xml, p1-results.xml, TEST_STATUS.md, validation-summary.json, scenario-results.json, crash-restart-results.json and fixture-verifier.log.
- Actual 40/40 P3 fixture drivers PASS, P0 goldens/hash vectors PASS, verifier --repo PASS, AppTest PASS and four separate-process pre/post commit crash/restart probes PASS.
- Runtime RSS: incremental CSV 198193152 bytes, XLSX 153718784 bytes; both <= 536870912 bytes (512 MiB); 21 XLSX byte-identical regenerated, 12 CSV fixtures verified.
- Accepted limits: Linux/Python 3.12.14 only, no independent CI/second-host test rerun, automated AppTest not manual browser sign-off; RSS sampled not hard OS limit; session-only unsaved drafts, no Order creation, no post-APPROVED edit (deferred CR-P3-001), no P4 execution, export or QA.
- Approved release archive: P3_Implementation_Pack_v1.0_APPROVED.zip, SHA-256 8a77848419161a5f784b61e7302a058e5c23e2ff5925e88a643c350e80930bc7, size 146604 bytes, 64 manifest payload files.
- Archive assembled from owner-reviewed v0.3 candidate; 40 original JSON scenarios, all 52 test-plan IDs, the API/workflow contract and test-only verifier preserved. Approval metadata, Gate A record, CR dispositions and manifest updated; no application/runtime P3 code generated.
- Authoritative GitHub approval record: docs/p3/v1.0/GATE_A_APPROVAL.md.
- Approved binary ZIP uploaded and verified in main: docs/p3/v1.0/P3_Implementation_Pack_v1.0_APPROVED.zip; upload commit 03ffc9c5fa61ee345bb6703d77240c2e10dbd0c6, Git blob SHA-1 496829008c508153a05d2f0ef4021a5b8e2c348f, size 146604 B, SHA-256 8a77848419161a5f784b61e7302a058e5c23e2ff5925e88a643c350e80930bc7 (verified against the approved local archive 2026-10-11).
- Historical GitHub main snapshot at pack review: a64baf8a1ba666e8ae8f002fc0b5189c3a159b4a.

Approved P3 decisions:
- P3-D01..P3-D18: APPROVED as the v1.0 design set; subordinate to existing P0/P1/P2 contracts.
- P3-Q01: APPROVED — retain P0 graph, block immediate edits/reselection at status APPROVED within P3.
- P3-Q02: APPROVED — drafts stored only in Streamlit session (restart discards unfinished edits).
- P3-Q03: APPROVED — simple read-only semantic JSON diff.
- CR-P3-001: DEFERRED (docs/change_requests/CR-P3-001.md). The proposed APPROVED -> READY_FOR_APPROVAL transition is NOT approved or implemented.
- CR-P3-002: APPROVED (docs/change_requests/CR-P3-002.md) for the narrowly phase-scoped historical P2-T40 and complete P3-T51 audit; subsequently IMPLEMENTED and VALIDATED under Gate B, with P1/P2 runtime and original packs unchanged.

Gate A evidence:
- Candidate ZIP CRC and 62/62 original file size/SHA-256 PASS; approved archive CRC and 64/64 payload size/SHA-256 PASS.
- Static P3 fixture verifier actually run: 40/40 reachability PASS; F09/F10/F20/F21/F38 five invalid Approval cases and five corrected mutants detected; F07 normalized NFC oracle PASS.
- Historical Gate A: P3 runtime and verifier `--repo` were NOT_RUN at design approval; subsequently performed and passed for P3 Gate B, see final closure evidence.
- Accepted design constraints: existing Order/InputAsset, manual BriefVersion/SpecVersion, two independent exact Approval facts and atomic final transition to APPROVED/COMPLETE, no P4 execution, no new DB tables or P0 state semantics, no unauthorized third-party integrations.
- Historical Gate A checklist: P3 Gate B required 52 P3, 54 P2, 42 P1, fixtures, P0 vectors, atomicity/recovery, scope audit, report and explicit owner closure; these passed and were accepted on 2026-10-11.

P3 Gate A design is closed; start was separately authorized, P3 implementation merged in PR #3, and P3 Gate B was subsequently CLOSED / PASS by the owner on 2026-10-11. P3 is VALIDATED; only P4 design preparation is the next authorized activity.


### P3 — Implementation start authorization (owner-confirmed 2026-10-11)
Status: APPROVED_TO_START; implementation start gate OPEN; production code NOT_STARTED at decision time.

- decision_revision: P3_IMPLEMENTATION_START_APPROVED_2026-10-11
- Authorization record: docs/p3/v1.0/IMPLEMENTATION_START_AUTHORIZATION.md.
- Owner explicitly confirmed opening the P3 implementation start gate in the main managing chat following P3 Gate A closure and verified approved ZIP upload.
- Approved source: docs/p3/v1.0/P3_Implementation_Pack_v1.0_APPROVED.zip, SHA-256 8a77848419161a5f784b61e7302a058e5c23e2ff5925e88a643c350e80930bc7; Git blob SHA-1 496829008c508153a05d2f0ef4021a5b8e2c348f; size 146604 bytes.
- Authorized scope: manual BriefVersion and TransformationSpecVersion authoring, exact two immutable Approval facts, legal P0 status/approval stages and atomic final APPROVED/COMPLETE, P1 UoW/CAS/EventLog, P2 one verified InputAsset and explicit read options, minimal Streamlit UI, test-only CR-P3-002 corrective regression audit.
- CR-P3-002: APPROVED for implementation strictly in its documented bounds; P2-T40 retained with phase-scoped frozen P1/P2 checks and new P3-T51 whole-application audit. CR-P3-001 remains DEFERRED; do not permit immediate post-APPROVED revision.
- No P0 schema/status change, SQLite migration, P1/P2 production runtime mutation, new source types, P4/P5 engine/QA/export, LLM, Telegram, marketplace automation, external services or workers.
- Implementation may be prepared in a new feature branch and Draft PR; no automatic merge or Gate B closure.
- Historical implementation-start checklist: 52 P3, 54 P2, 42 P1, P0 goldens/hash vectors, 40 fixtures, --repo verifier, atomicity/restart and source/scope reviews. All required evidence was later recorded and accepted for the P3 Gate B closure on 2026-10-11; see docs/p3/validation/P3_GATE_B_CLOSURE.md.

### P3 — Formal Gate B closure (owner-confirmed 2026-10-11)
Status: VALIDATED; Gate B CLOSED / PASS.

- decision_revision: P3_VALIDATED_2026-10-11
- Gate B closure authority: main managing chat, explicit owner confirmation after post-merge review.
- Formal closure record: docs/p3/validation/P3_GATE_B_CLOSURE.md.
- Code/repo tested: 6a8e67252131c2b6a6a70388aa47ead899c35140; PR #3 merged to main aa513780594595c3f5fb3cda15060ecd51b9e00f. Later modifications were evidence only.
- 148/148 test IDs PASS (P3 52, P2 54, P1 42), no skip/xfail/fail/error; 40 P3 fixture drivers PASS; 4 crash/restart cases PASS; exact approved ZIP and P0 hash/golden checks PASS; CSV and XLSX incremental RSS within 512 MiB.
- CR-P3-002 implementation VALIDATED; CR-P3-001 remains DEFERRED, so no post-APPROVED revision.
- Accepted limits and absence of independent CI are recorded in formal closure document. No new architecture, persistence schema, Pilot scope or additional Change Request.
- Next authorized activity: P4 design/contract/fixtures/acceptance planning only. P4 code implementation requires separate owner approval, and P4 VALIDATED requires future actual tests and explicit Gate B closure.

### P4 — Formal Gate A design approval (owner-confirmed 2026-10-30)
Status: APPROVED (design pack v1.0); Gate A CLOSED / PASS; Gate B NOT_RUN.

- decision_revision: P4_GATE_A_APPROVED_2026-10-30
- Owner explicitly confirmed the proposed P4 Gate A approval in the main managing chat after independent review and successful strict P0 checkout evidence.
- Approved candidate source: P4_Implementation_Pack_v0.4.1_candidate.zip, SHA-256 79f725fd96075f3ca87b6172819d82b557f5e373b1f5ebc46f08cfbe8b2e3d0a, 104894 bytes; CRC and 48/48 payload manifest PASS; 38 F, 19 X, 45 W fixtures, 64 P4 test definitions.
- Locally assembled release archive: P4_Implementation_Pack_v1.0_APPROVED.zip, SHA-256 e3c686f81e3ba0d63874420d0f67f7585b9861826fdbc8a76dfb6a5d8f2aa5aa, 112649 bytes, 53 manifest payloads, CRC/53/53 PASS, 48/48 original source payloads byte-identical, local static verifier PASS, nine isolated mutations rejected. **Archived binary uploaded to GitHub and byte content independently verified on 2026-10-30: path `docs/p4/v1.0/P4_Implementation_Pack_v1.0_APPROVED.zip`, upload commit `a88c29b3343c0f243682f03220fc3a7867869675`, blob `1858cb62fec9220a03eec77151b4063e9758e683`, 112649 B, SHA-256 `e3c686f81e3ba0d63874420d0f67f7585b9861826fdbc8a76dfb6a5d8f2aa5aa`.**
- Formal Gate A approval: docs/p4/v1.0/GATE_A_APPROVAL.md; strict reported validation: docs/p4/v1.0/STRICT_VALIDATION_EVIDENCE.md; upload verification docs/p4/v1.0/GITHUB_ARCHIVE_UPLOAD_VERIFIED.md.
- External Codex strict verifier on real P0 checkout 411fda98b499646b355782d3ca3c34e20f9322ae: exit 0, 36 schema-valid, 2 schema-invalid rejected, 1 semantic-invalid recognized, two goldens, nine mutations rejected. Not independently re-run on a separate P0 checkout; runtime P4 tests NOT_RUN.
- P4-Q01, Q02, Q03 (revised signed64 tagged-string P4_INTERNAL_V2 and exact Unicode), Q04, Q05 (mandatory future Gate B stress), Q07 APPROVED; P4-Q06 DEFERRED. P4-D01..D14 adopted only within reviewed scope; D15 DEFERRED.
- CR-P4-001 APPROVED (test-only P3-T51 phase scoping + P4-T62 full-app audit), NOT_IMPLEMENTED. Full record: docs/change_requests/CR-P4-001.md.
- Frozen P0/P1/P2/P3 rules and Pilot Slice V1 scope unchanged, including P0 12-operation whitelist and no post-APPROVED revision. No production code, dependencies, migrations, P5 QA/export or external automation authorized.
- Existing P0 manifest discrepancy: 13 missing P-C fixture files remain recorded as a separate risk, not silently restored; strict P4 checker uses its exact verified P0 subset.
- Owner Gate A closure does NOT authorize P4 implementation start, Gate B closure, code PR or merge. ZIP upload+SHA verification complete; next action: request separate owner P4 implementation-start authorization.

### P4 — Approved ZIP GitHub upload verification (2026-10-30)
Status: VERIFIED; P4 design APPROVED, Gate A CLOSED / PASS; implementation start NOT_AUTHORIZED.

- Path: `docs/p4/v1.0/P4_Implementation_Pack_v1.0_APPROVED.zip`.
- Upload commit: `a88c29b3343c0f243682f03220fc3a7867869675` (the commit added only the ZIP), parent Gate A decision commit `9351b790a82d723b8f579878c7a3dcac9f23697b`.
- Git blob SHA-1: `1858cb62fec9220a03eec77151b4063e9758e683`; remote size 112649 B.
- SHA-256 recomputed from bytes returned by GitHub for that exact blob: `e3c686f81e3ba0d63874420d0f67f7585b9861826fdbc8a76dfb6a5d8f2aa5aa`. Exact match to locally approved ZIP checksum and independently computed local Git blob SHA-1.
- Verification record: `docs/p4/v1.0/GITHUB_ARCHIVE_UPLOAD_VERIFIED.md`.
- Existing P4 Gate A remains CLOSED / PASS. CR-P4-001 is APPROVED / NOT_IMPLEMENTED; P4 Gate B is NOT_RUN. This file upload does **not** authorize P4 implementation.
- Next decision required from owner: open P4 implementation start gate, strictly within v1.0 approved pack and CR-P4-001 test-only scope.

### P4 — Implementation Start Gate authorization (owner-confirmed 2026-10-30)
Status: OPEN / AUTHORIZED. P4 stage IN_IMPLEMENTATION (work permitted; no P4 implementation yet merged or tests executed).

- decision_revision: P4_IMPLEMENTATION_START_AUTHORIZED_2026-10-30.
- Owner explicitly confirmed opening the implementation start gate in the main managing chat after Gate A CLOSED / PASS and GitHub-approved ZIP byte-for-byte SHA-256 verification.
- Binding approved source: `docs/p4/v1.0/P4_Implementation_Pack_v1.0_APPROVED.zip` at main baseline `8ae219d717b36f463ea76eccaeb8c88d74aeeefc`; SHA-256 `e3c686f81e3ba0d63874420d0f67f7585b9861826fdbc8a76dfb6a5d8f2aa5aa` (112649 bytes).
- **Authorized:** P4-only deterministic 12-operation engine, preflight/revalidation of two exact Approvals, verified full-row CSV/XLSX adapter, bounded processing, P1-native ExecutionRun and internal Artifact, manual Streamlit trigger, P4_INTERNAL_V2 signed64/JCS exact wire, P4 test suite and narrowly approved CR-P4-001 test-only scope correction.
- **Forbidden:** P5 QA/export, P6, new operation types, changed P0/P1/P2/P3 production contracts, migrations/state graph/Approval semantics, new infrastructure, arbitrary LLM code, external marketplace automation or auto-messaging, bypassing deterministic FAIL, silent scope changes or regression test skip/xfail.
- Work in `feature/p4-deterministic-engine` branch, not on `main`; present an unmerged Draft PR for independent review and Gate B assessment. PR creation alone does not mean validated. Do not merge without owner authorization.
- Future Gate B requires actual 64/64 P4, 52/52 P3, 54/54 P2, 42/42 P1, P0 hash/schema/goldens, 38 F + 19 X + 45 W fixtures, 100000x200 memory/time constraints, crash/restart and audit checks with 0 fail/error/skip/xfail; record environment, exact commands and reproducible test evidence. A test plan is not a passing test.
- CR-P4-001 remains APPROVED / NOT_IMPLEMENTED until the exact test-only change is committed, run and reviewed. P4 Gate B remains NOT_RUN / NOT_PASSED and requires separate explicit owner closure.
- Known P0 manifest P-C 13-file discrepancy remains unresolved and must not be 'fixed' by fabricating P0 content.
- Formal implementation-start record: `docs/p4/v1.0/IMPLEMENTATION_START_AUTHORIZATION.md`.
- Next step: give Codex the implementation task under this authorization; report an unmerged Draft PR and actual validation report.


### P4 — Formal owner approval of CR-P4-002, CR-P4-003 and CR-P4-004 (2026-10-30)
Status: **APPROVED** (main managing chat); implementation remains in unmerged Draft PR #4, Gate B NOT_CLOSED.

- Owner explicitly confirmed: “Утверждаю CR-P4-002, CR-P4-003 и CR-P4-004 в предложенных узких границах”. This **supersedes any claimed approval made only in the implementation/specialist chat**. No change request is approved by Codex independently.
- **CR-P4-002 APPROVED:** Correct only P4-T13 full-row XLSX acceptance oracle to 6 headers and **four original rows** (including duplicate O-002), in frozen P0 source order and cached-cell semantics. P4-T42 continues to require **three output rows**. Keep P0/P1/P2/P3 runtime, approved P4 v1.0 ZIP and source fixtures immutable.
- **CR-P4-003 APPROVED:** Test-only adjustment of P2-T40 and P3-T51 `git diff --name-only` baseline to the exact P4 Implementation Start SHA `7685110506d115805c473b064752f86e9e5c045b`. Preserve all historical test IDs, negative probes, untracked-file inventory, frozen code hashes, production APIs, dependency/migration checks and scope protections. No wildcard authorization.
- **CR-P4-004 APPROVED:** Clarify finite canonical Decimal wire syntax for negative proper fractions such as `-0.25`; whole-string ASCII regex `(?:0|-?(?:[1-9][0-9]*(?:\\.[0-9]*[1-9])?|0\\.[0-9]*[1-9]))` (unescaped literal regex in source: `(?:0|-?(?:[1-9][0-9]*(?:\.[0-9]*[1-9])?|0\.[0-9]*[1-9]))`). Continue rejecting `-0`, `+1`, exponent form, leading or insignificant trailing zeros and NaN/Infinity; negative zero canonicalizes to `0`; retain signed64 tags and original F/X/W fixtures, add exact tests P4-T25/T57.
- Exact CR proposal text is now stored in `docs/change_requests/CR-P4-002.md`, `CR-P4-003.md`, `CR-P4-004.md`, byte-for-byte from Draft PR #4 to avoid merge conflicts; **this register entry is the formal main-chat approval authority**, independently of source-file historical wording.
- No implementation code, tests, P0–P3 production files, state graph, migrations or release ZIP altered by this decision commit. P4 remains `IN_IMPLEMENTATION`, Gate B remains `NOT_RUN / NOT_PASSED` in the managing decision register until explicit validation/closure; PR #4 stays Draft/unmerged.
- **Integration risk / mandatory pre-merge check:** existing P2-T40 and P3-T51 test commands use `git diff --name-only 7685110506…` and the repository-path auditor rejects `DECISIONS.md`. This formal post-baseline approval modifies that file in `main`, so the same tests may fail on a future combined or merged history even though they passed on the prior feature head. Confirm against the exact future integration commit; do not silently drop/skip the governance protection or shift the baseline without separately approved change if required.
- Next action: continue independent Gate B review with explicit CR approval recorded, and require a fully audited combined-tree regression before any owner-authorized merge.

### P4 — CR-P4-005 approval of exact governance pin (owner-confirmed 2026-11-01)
**Decision revision:** `CR-P4-005_APPROVED_2026-11-01`. **Status:** APPROVED / NOT_IMPLEMENTED; P4 Gate B NOT_CLOSED; PR #4 DRAFT / UNMERGED.

- The owner explicitly confirmed approval of the 2026-11-01 REVISED CR-P4-005 in the main managing chat. This is **the sole formal owner authorization**. Prior Codex/specialist proposal status was PROPOSED.
- **Exact approved proposal:** `docs/change_requests/CR-P4-005_REVISED_PROPOSED.md` (source UTF-8 SHA-256 `6545b582d4003449fdc7a5f0da3d7b2b0db8bfb314e7f85776e9b39f6c396170`, 39572 bytes, byte-identical to uploaded owner-reviewed source); binding disposition `docs/change_requests/CR-P4-005.md`.
- **Approved scope:** narrowly recognize exactly one owner-approved `DECISIONS.md` in existing test-only path and P4 frozen audits, based on immutable Git approval commit/blob/bytes/size/mode and ancestry; preserve every existing forbidden-path, frozen source, dependency/schema/migration, negative-probe and historical P2-T40/P3-T51/P4-T61/T62/T63 requirement. Keep P4-start baseline `7685110506d115805c473b064752f86e9e5c045b`.
- **Stage A:** finalize this decision and approved revised proposal in a single immutable governance-only commit G. Compute G/B/H/L/M from `G:DECISIONS.md` **after commit finalization**; publish exact owner receipt separately, **never inside DECISIONS.md**. This decision must not include G or its own SHA-256.
- **Stage B authorized only upon verified receipt:** one exact closed-schema `tests/p4/approved_governance_pin_v1.json` containing (G,B,H,L,M) with no self-checksum, independently pinned by its SHA-256 P in test-only verifier and P4 policy. HEAD/stage-0 index/working-tree DECISIONS must exactly match G bytes/mode and verified ancestry. Reject missing/corrupt/symlink/mode/staged/unstaged/other-authority paths and changed pin.
- **Approved limited repin procedure:** For any future explicitly owner-approved DECISIONS content change, create descendant governance commit G2 and separate owner receipt; update only pin/P/policy plus test evidence, preserving all audit protections. No new CR is required solely for checksum rotation; new substantive decisions still require normal approval. No automatic latest-main or silent whitelist.
- **Restrictions:** No P0–P4 production change, P5, new dependencies/migrations/operations/state transitions, no weakening tests, no modification of prior approved packs and old integration failure evidence. Full 212 tests and negatives must run on exact new integrated tree before Gate B, with additional P4 pin/ancestry probes; no automatic PR merge.
- **Current evidence:** historical review integration `9620f8f44c5a8fca41aa37f47034ccd54a563e89` failed P2-T40/P3-T51; approved fix code not yet applied, full post-change tests NOT_RUN. This governance-only approval does not close Gate B.
- **Next action:** publish verified G/B/H/L/M receipt outside DECISIONS and instruct Codex to implement approved narrow correction on isolated integration branch, provide repeatable validation, and keep PR #4 Draft.
