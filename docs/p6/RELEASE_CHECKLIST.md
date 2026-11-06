# P6 Pilot release checklist

**Status: PENDING — no Gate B closure, merge or Pilot release is granted by this checklist.** The [owner decision](decisions/P6_DIRECTION_OWNER_DECISION_2026-11-06.md) closes Gate A only; implementation start comes from the separately authorized owner instruction. The approved [design](design/P6_DESIGN_PACK_v0.2.md) and [CR-P6-001](decisions/CR-P6-001_OWNER_DECISION_2026-11-06.md) remain the authority. [README_PILOT.md](README_PILOT.md) is the operator procedure.

Every unchecked item is pending. Enter actual results and evidence only after execution. `NOT RUN`, `FAIL` and a recorded limitation are not PASS. The current documentation-authoring environment is Linux; no Mac-host Docker smoke evidence has been supplied here. P6-T19's Mac requirement is **NOT RUN / PENDING**, and T19 cannot be closed until actual required evidence exists.

**Known P-B blocker:** frozen P5 binds PB-AC-002's approved exception to `brief-pb-v1`; a new P3 UI publication has a UUID and gets DQ-010 FAIL / NEEDS_FIX. P6-T06/T07 must retain their strict required READY/PASS_WITH_WARNINGS assertions. A proposed CR-P6-002 is recorded with the new runtime evidence; no protected P5 fix or fixture/ID workaround is permitted without owner approval. This is a behavioral integration failure, not a historical scope conflict.

## Immutable identity and evidence record

| Required field | Value / evidence |
|---|---|
| Frozen main baseline | `0af4a1ff49ccf8fa59c39780d749e15cb5042fc3` |
| Approved implementation-start feature HEAD | `b93e0ef4ed69343968ff7ae4188d586c0d1485a5` |
| Approved design Git blob | `50b744540bbac136469565d1f9af57ab81697786` |
| Approved design SHA-256 | `c4b09611a647524678882c4f0b1d28a6cad1d3b8ff0c0ee0a04b92ca220dd8e0` |
| Actual tested implementation commit | PENDING — record full SHA, not owner-start HEAD by substitution |
| Actual tested tree | PENDING — record full tree SHA and worktree cleanliness/inventory |
| Distributed source package filename and SHA-256 | PENDING — hash the exact archive distributed |
| Linux distro/kernel/architecture; Python and uv | PENDING — expected Python `3.12.14`, uv `0.12.19` |
| Mac host OS/CPU; Docker Desktop/Engine; image digest | NOT RUN / PENDING |
| Frozen `pyproject.toml` / `uv.lock` checksums and installed package inventory | PENDING |
| Evidence root | PENDING — finite `docs/p6/validation/runtime-*/` directory |
| Evidence manifest SHA-256 and tested input/output inventories | PENDING |
| Independent validation reviewer and findings | PENDING |
| Explicit owner Gate B decision | PENDING — no automatic closure |
| Separate owner merge decision | NOT AUTHORIZED by this checklist |
| Separate owner Pilot release decision | NOT AUTHORIZED by this checklist |

Record `git rev-parse HEAD`, `git rev-parse HEAD^{tree}`, exact commands/working directory, UTC timestamps, OS/tool versions, exit codes, stdout/stderr and raw JUnit. For a clean selected commit, an example source-package command is `git archive --format=tar HEAD --output=/absolute/outside/repository/vde-pilot-source.tar`; compute its SHA-256 with `sha256sum` on Linux or `shasum -a 256` on Mac. This archive identifies source bytes; installed dependencies and the actual container image digest need separate records. Archive/evidence production does not certify or publish a release. Never include credential values in logs.

The new acceptance suite and successor audit live under `tests/p6/`; the outer `p6.run_validation` module records their runtime execution and unchanged historical suites. Invoke it from a clean committed selected tree, with actual disposable stress artifacts and evidence outside the repository: `PYTHONPATH=src:tests .venv/bin/python -m p6.run_validation --stress-workspace /absolute/test/stress-workspace --out /absolute/test/p6-validation`. Supply actual platform-smoke evidence only when available; an absent Mac run remains a recorded blocker.

## Scope and dependency admission

- [ ] Verify both remote refs against the owner-authorized SHAs before implementation admission; preserve the ref-query response and time.
- [ ] Compare every baseline blob and mode against frozen main. Only the four exact added `app.py` lines and the finite 4 runtime + 6 test/audit + 5 documentation paths from CR-P6-001 are admitted; no deletion/reorder of existing app lines.
- [ ] Preserve approved design/decision bytes, all P0–P5 source/tests/policies/fixtures/evidence, `DECISIONS.md`, G3 pin, schema/migrations and dependency files. Run the P6 successor audit and retain its exact inventory.
- [ ] On the exact tested tree, complete `uv sync --frozen --python 3.12.14 --extra test` without lock changes; record installed direct and transitive package versions. Direct runtime versions remain jsonschema 4.26.0, referencing 0.37.0, rfc8785 0.1.4, Streamlit 1.50.0 and openpyxl 3.1.5; pytest 8.4.2 is the existing test extra.
- [ ] Run at least one negative mutation per protected-file class plus forbidden extra paths; retain actual rejections and verify mutation workspace disposal/restoration. No old source/evidence is changed by these probes.

## Mandatory acceptance register

All twenty IDs require actual runtime outcomes on the recorded SHA/tree, raw JUnit and independent oracles. Fill the result/evidence column with exact relative evidence paths and outcomes; do not infer success from test collection or documentation.

| ID | Measurable closure condition | Result / evidence |
|---|---|---|
| P6-T01 | Clean Linux install/bootstrap and opened Streamlit: ready, zero Orders/Approvals, CreateOrder present, no automatic business writes. | PENDING |
| P6-T02 | Explicit valid form creates one exact DRAFT; token=id, equal initial timestamps, null selections, no associated records/events, P2 visibility. | PENDING |
| P6-T03 | Invalid fields/replays/concurrency/rerenders: no invalid/duplicate rows; exact replay returns same ID, conflict rejected without writes. | PENDING |
| P6-T04 | P-A explicit isolated UI test-user workflow records both independently reviewed Approvals with exact IDs/hashes/context; P4 disabled before both. | PENDING |
| P6-T05 | P-A P4/P5 gives READY/PASS and one exact 277-byte golden CSV; saved result hash/readback and QA schema/linkage checked; repeat transfer passive. | PENDING |
| P6-T06 | P-B Orders worksheet and approved v2 gives READY/PASS_WITH_WARNINGS, 3×6 XLSX, 18 values, no exported formulas, 24 DQ records, separate DQ-017 PB-AC-006/007 PASS, source warning. | PENDING |
| P6-T07 | Saved P-B XLSX/QA matches Artifact/report hashes, MIME/name, all 18 values and exact links; one production XLSX, no extra production CSV. | PENDING |
| P6-T08 | P-D gives NEEDS_FIX/FAIL, marked diagnostic `_DIAGNOSTIC_NOT_FOR_DELIVERY` and matching QA; no delivery-ready claim. | PENDING |
| P6-T09 | Missing Run/DRAFT/FAILED/EXECUTING/missing approvals expose no payload and create no promotion/Approval/Artifact/Event. | PENDING |
| P6-T10 | Actual Streamlit restart at intermediate P3 and terminal P5 preserves persisted rows/bytes/context; no auto-execute or prepared-session reuse. | PENDING |
| P6-T11 | Separate disposable CSV/XLSX source corruption is detected; no payload/business writes/repair. | PENDING |
| P6-T12 | Separate P4_INTERNAL/final corruption blocks future preparation; no exposed new bytes or changed rows/events; prior-snapshot limitation recorded. | PENDING |
| P6-T13 | Cross-Order Run and mismatched Approval/hash/Spec/Run context rejected before reading/leaking other-Order payload or report details; zero writes. | PENDING |
| P6-T14 | Missing report, altered metadata, degraded staging/orphan and blocked health disable create/download with detect-only diagnostics. | PENDING |
| P6-T15 | At least three passive rerenders, re-prepare and repeated browser transfers preserve counts/hashes and retain at most one selected Run's result/report buffers. | PENDING |
| P6-T16 | Actual CSV/XLSX MIME/name/extension and saved QA deterministic UTF-8/schema/identity checks; unsafe filenames/replay/format blocked. | PENDING |
| P6-T17 | Actual hashed small and large/admission-refused real artifacts; preflight and sampled RSS recorded; accepted transfer reads correctly; refusal exposes no payload/writes. Mandatory Pilot workload refusal is FAIL pending CR. | PENDING |
| P6-T18 | Successor exact-tree/mode/whitelist audit plus protected-class mutation negatives; all historical failures retained and individually classified. | PENDING |
| P6-T19 | Clean Linux and actual Mac Docker commands work; read-only repository/ephemeral build copy and same writable persistent workspace survive restart; UI workflow needs no DB/file edits. | Linux PENDING; Mac NOT RUN / PENDING |
| P6-T20 | All 20 runtime IDs, commands/JUnit/SHA/tree/manifests and full legacy outcomes/limitations/checklist assembled; owner Gate B remains pending for separate decision. | PENDING |

## Fixture and historical regression evidence

- [ ] Record untouched P-A/P-B/P-D fixture hashes, expected rows/results and exact isolated-workspace setup. Preserve the P-A 277-byte golden and P-D typed QA semantics.
- [ ] Verify P-B v2 provenance: outer `P5_Codex_Implementation_Handoff_2026-11-05.zip` SHA-256 `3e3a2f6a8e65f500fe5bd281ef805d9229d50b96c50433cdda52cbb4fd6d63e4`, nested supplement SHA-256 `4e08285b00344f2d00a7af89a723a835f931f4bceb768b11ec1aaf637fd0ae18`, and exact v2 specimen. Missing provenance is a blocker, not permission to invent a replacement.
- [ ] Log allowed test-only Order/InputAsset/version identity substitutions and canonical original/derived hashes. Preserve fixture semantic transformations/goldens. Do not claim the specimen's hash for an adapted payload.
- [ ] List the thirteen missing original P-C files and actual available negative coverage; no synthetic positive fixture or full-P-C claim.
- [ ] Separately cite the historical P1–P4 212/212 and P5 76/76 results with their actual tested refs and preserved reports; do not attribute those outcomes to P6.
- [ ] Execute unchanged P1–P5 suites on the actual P6 tree, including original P5-T76. Retain every raw PASS/FAIL, exact failing assertion, nested subprocess outcome/JUnit and exit code. Only proven owner-approved scope conflicts receive that classification; keep them FAIL, never skip/xfail or false PASS. Other behavioral regressions block Gate B.
- [ ] Run all mutation/corruption tests in disposable copies, not owner workspace or original fixtures. Detect and prevent test runners' historical evidence writes from altering preserved files.

## Delivery, resource and restart review

- [ ] Verify no view/prepare/download creates or changes business rows/events, QA decisions or workspace files; ownership is checked before artifact access and every new prepare uses current health/context.
- [ ] Record independent saved-file readback/hash checks for CSV and XLSX and exact QAReport schema/Run/version/Artifact linkage, deterministic serialization and MIME/extension/basename. Widget inspection alone does not replace actual transfer evidence.
- [ ] On frozen Streamlit 1.50.0, inject failure after the first real media registration and verify that no newly registered URL is published/fetchable and prior valid media remains intact. Cover the private `_enqueue`/media-manager rollback compatibility and dedicated internal QA MIME extension with actual HTTP responses; the saved QA filename remains `.json`.
- [ ] Verify READY/PASS and READY/PASS_WITH_WARNINGS with zero blockers, and conspicuously marked NEEDS_FIX/FAIL diagnostic behavior. No downloads for inconsistent/nonterminal/unhealthy context.
- [ ] Measure incremental RSS above pre-preparation baseline against 536870912 bytes. Record artifact size/hash, sampling cadence/observed peak, `3× size + QA bytes + 64 MiB` preflight, rebinding checks, safe refusal and absence of partial payload/writes. No silent limit reduction or P5-stress-as-P6 proof.
- [ ] Verify one immutable result snapshot and at most one report buffer per selected Run; clear on new preparation, selection/context/health failure, error or session loss. Demonstrate new preparation after actual process restart.
- [ ] Disclose last-click boundary: the static download button transfers prepared verified bytes; it cannot promise fresh disk verification at the final browser click. Prior bytes can remain valid after later disk corruption; future prepare must fail.

## Operator and platform smoke

- [ ] Record clean Linux commands, OS/kernel, Python 3.12.14, uv 0.12.19, exact package/lock identity, logs and actual UI workflow/restart observations.
- [ ] Record actual Mac-host OS/CPU, Docker Desktop/Engine, image digest, frozen installation, read-only source mount, ephemeral build environment and writable host workspace. Restart using exactly the same mount and verify SQLite/payload persistence. **NOT RUN until performed on a Mac.**
- [ ] Confirm native macOS is not claimed supported; frozen Linux `/proc` constraints remain documented. No new dependency, Dockerfile, migration or helper script is required by the manual.
- [ ] Review both exact published business versions and independent Approvals with the real authorized person for any live Order. Automated isolated-test Approvals/fixture snippets never authorize business delivery.
- [ ] Complete stopped-app checkpoint/full backup and verify restoration to a disposable new directory with exact package identity. Retain problem workspace/logs; recovery remains detect-only with no silent repair or DB editing.
- [ ] Demonstrate manual rollback/restart using a separately selected owner-approved compatible package and complete verified checkpoint, without overwriting the only failing copy or mixing database/files from different snapshots.
- [ ] Confirm only manual external messages/transfer/billing, one local operator/process/workspace, filesystem permissions and all documented limitations. The Pilot slice is not MVP-0 Complete or market-demand validation.

## Separate owner decisions

- [ ] Independent validation review completed against immutable recorded evidence, including every unresolved FAIL/NOT RUN and any CR blocker.
- [ ] Owner explicitly closes **P6 Gate B: CLOSED / PASS** after required runtime evidence; record decision reference/date. An agent/test runner cannot supply this decision.
- [ ] Owner separately authorizes merge of the specified commit, if desired. No governance repin is implicit.
- [ ] Owner separately authorizes Pilot release of the exact package SHA-256 and records unresolved accepted limitations. No approval is inferred from implementation, this checklist, a green subset or a prepared download.

Until those decisions and required runtime checks exist: **P6 Gate B PENDING; merge and Pilot release NOT AUTHORIZED.**
