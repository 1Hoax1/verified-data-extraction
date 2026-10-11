# DECISIONS.md

## Current state

- Product Specification v0.1 — APPROVED
- MVP-0 Implementation Scope v1.1 — APPROVED
- Pilot Slice V1 Contract Pack v1.0 — VALIDATED
- P0 Formal Contracts and Fixtures — VALIDATED
- P1 Implementation Pack v1.0 — APPROVED
- Current release target — Pilot Slice V1
- Current stage — P3 APPROVED_TO_START (implementation start gate OPEN; code NOT_STARTED)
- P1 — VALIDATED
- P1 completion/release gate — CLOSED (PASS, owner-confirmed 2026-10-08)
- P2 Implementation Pack v1.0 — APPROVED
- P2 — VALIDATED (Gate B CLOSED / PASS, owner-confirmed 2026-10-11)
- CR-P2-001 — APPROVED and implemented (validated under P2 Gate B)
- P2 Gate A — CLOSED (PASS, owner-confirmed 2026-10-11)
- P2 implementation start gate — historical OPEN at Gate A; implementation merged
- P2 Gate B — CLOSED (PASS, owner-confirmed 2026-10-11)
- P3 — APPROVED_TO_START (implementation authorized 2026-10-11; code NOT_STARTED; Gate B NOT_RUN)
- P3 Implementation Pack v1.0 — APPROVED (owner-confirmed 2026-10-11)
- P3 Gate A — CLOSED (PASS, owner-confirmed 2026-10-11)
- P3 implementation start gate — OPEN (explicit owner authorization 2026-10-11)
- P3 Gate B — NOT_RUN / NOT_PASSED
- CR-P3-001 — DEFERRED (no P0 state graph change)
- CR-P3-002 — APPROVED (P2-T40 phase-scoped audit amendment, not implemented)

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
Status: APPROVED_TO_START (implementation authorized; P3 runtime NOT_STARTED; Gate B NOT_RUN)

Design and Gate A approval:
- P3 Implementation Pack v1.0 — APPROVED on 2026-10-11, based on reviewed P3 v0.3 candidate.
- decision_revision: P3_PACK_APPROVED_2026-10-11
- Gate A: CLOSED / PASS, explicit main-chat owner confirmation 2026-10-11.
- Gate A owner approval (historical) covered design pack + CR decisions only; subsequent separate implementation start authorization granted on 2026-10-11. Start gate OPEN; code not yet written. See docs/p3/v1.0/IMPLEMENTATION_START_AUTHORIZATION.md.
- Gate B: NOT_RUN / NOT_PASSED. P3-T01..P3-T52 planned, not executed; P1/P2 regressions not rerun for P3.
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
- CR-P3-002: APPROVED (docs/change_requests/CR-P3-002.md) narrowly to phase-scope historical P2-T40 regression without removing the test, together with a full-application P3-T51 audit. NOT IMPLEMENTED until separate P3 implementation start.

Gate A evidence:
- Candidate ZIP CRC and 62/62 original file size/SHA-256 PASS; approved archive CRC and 64/64 payload size/SHA-256 PASS.
- Static P3 fixture verifier actually run: 40/40 reachability PASS; F09/F10/F20/F21/F38 five invalid Approval cases and five corrected mutants detected; F07 normalized NFC oracle PASS.
- No P3 production runtime testing; optional P0 checkout `--repo` verifier check NOT_RUN at Gate A and required in implementation validation.
- Accepted design constraints: existing Order/InputAsset, manual BriefVersion/SpecVersion, two independent exact Approval facts and atomic final transition to APPROVED/COMPLETE, no P4 execution, no new DB tables or P0 state semantics, no unauthorized third-party integrations.
- Known limitations: local Linux/P1/P2 contract compatibility and static verifier do not replace P3 integration/SQLite rollback tests; P3 Gate B requires 52 P3, 54 P2 and 42 P1 PASS, fixtures, P0 vectors, atomicity/recovery, scope audit, report and owner closure.

P3 Gate A design is closed. The approved ZIP is uploaded and verified in GitHub, and the separate owner authorization opened the P3 implementation start gate on 2026-10-11. Codex may implement only approved P3. No approval or closure of P3 Gate B is implied.


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
- Gate B remains NOT_RUN / NOT_PASSED. Require P3-T01..P3-T52 52/52, P2-T01..P2-T54 54/54, P1-T01..P1-T42 42/42, P0 goldens/hash vectors, 40 fixtures, explicit --repo verifier, SQLite fault atomicity, restart, source/scope tests, actual JUnit/log/RSS evidence as applicable and review of known limits. Separate owner Gate B closure still required.
