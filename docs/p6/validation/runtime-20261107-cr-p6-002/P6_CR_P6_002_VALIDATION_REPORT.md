# CR-P6-002 — corrected P6 validation

Recorded: 2026-11-07T02:36:25.684467+03:00.

**Status: CR-P6-002 correction technically verified on Linux; P6 BLOCKED by actual Mac Docker T19 NOT RUN. No Gate B closure, merge, governance repin, Pilot release or next stage is asserted.**

## Authority and exact tested source

Owner-approved start: `66c2b4f97e2b4dbe4e7a01696c89ae5fd0431981`. Main remains the separately verified frozen baseline `0af4a1ff49ccf8fa59c39780d749e15cb5042fc3`. Branch: `feature/p6-streamlit-e2e`.

**Tested implementation: `245b1ccf5d4212d3f34973e526172f20a4928539`. Tree: `0db696f5e14284849f969310fadf4ee585713045`.** Its only parent is the owner-authority commit. Exactly seven existing files are modified; `IMPLEMENTATION_CHANGED_FILES.txt` and `IMPLEMENTATION.diff` provide the complete inventory and bytes. A later evidence-only commit has identical source/tests and separate publication verification; no full runtime rerun on that descendant is claimed.

The owner decision was read fully and independently fetched from GitHub before source edits. Its exact blob, SHA-256 and ancestry remain pinned. This project authority is separate from the two actual business-version Approvals required by unchanged P5 admission. No live owner workspace or Approval was changed.

## Fix and exact boundaries

Only P5 `qa.py`'s PB-AC-002 recognition guard changes, with a private pure helper and its required imports. `QA_CHANGE_BOUNDARY_VERIFICATION_FINAL.json` proves the entire prior AST is identical after reversing precisely those changes. Generic `predicate`, every other QA function, admission, transformations, stored identities/hashes/history and source bytes remain unchanged.

All guards are conjunctive: admitted real Order/source/Brief/Spec/Approval/Run; exactly one matching LOCAL_XLSX/Orders input; source SHA-256 `d275fa7393e73ef1be7815e83b31b1a710b3f345bb7138c72569b03f66edf80d`; exact approved XLSX output; PB-AC-002/COLUMNS/sequence_equals with the same five target/expected columns and exact six output columns. A separate deep copy substitutes solely its verified input asset binding to asset-pb-xlsx for frozen P0 semantic hash comparison with `9b7c2b0111360714dfbc9cbdbc755b693b11e067f32771cb226126fdcd1ffb49`. The original document/hash is never changed or replaced as authority.

Corrected QA file SHA-256: `8caee87fce7a0c748e2333b8fe3b1b3333fee3548ee78111516a8eac541d8a52`. Active audit version is `P6_SCOPE_POLICY_V2_CR_P6_002` in the historical filename scope_policy_v1.json. Original baselines are unchanged; correction authority is separately named. Exact hash protection covers only this single P5 edit. V1 policy/audit/runner remain at `deddc2799464076227173bd2e4890f552ffe64bf` and are copied under retired-v1 with immutable Git blob/SHA provenance, clearly inactive. No broad P5 waiver or latest-main trust exists.

## Actual results on the corrected tree

| Suite | Actual outcome |
|---|---|
| P6-T01…T20 | 19 PASS / 1 FAIL / 0 ERROR / 0 SKIP; raw exit 1 |
| Unchanged P1–P4 | 205 PASS / 7 actual historical scope FAIL; 0 behavioral regressions |
| Unchanged P5 | 75 PASS / 1 actual historical scope FAIL; 0 behavioral regressions |
| New successor audit | PASS; 30/30 negative mutations rejected |
| P0 | 20 schemas / 121 positive schema applications PASS; 116/129 original files present+matching |

| P6 ID | Actual outcome |
|---|---|
| P6-T01 | PASS |
| P6-T02 | PASS |
| P6-T03 | PASS |
| P6-T04 | PASS |
| P6-T05 | PASS |
| P6-T06 | PASS |
| P6-T07 | PASS |
| P6-T08 | PASS |
| P6-T09 | PASS |
| P6-T10 | PASS |
| P6-T11 | PASS |
| P6-T12 | PASS |
| P6-T13 | PASS |
| P6-T14 | PASS |
| P6-T15 | PASS |
| P6-T16 | PASS |
| P6-T17 | PASS |
| P6-T18 | PASS |
| P6-T19 | FAILURE |
| P6-T20 | PASS |

The only corrected-tree P6 failure is T19: native Linux launch/restart passed, but actual Mac-host Docker execution is NOT RUN. It remains a real FAIL, never skip/xfail or Linux substitution. The historical eight scope failures remain FAIL with exact assertion and child-JUnit proof. Historical 212/212 and 76/76 PASS remain tied solely to `fd39aa1bed480313504ae8b1f76e77e170cb72ba` and `801cc2ba5db46494eaa93e5b963c3bc2f936ddc2`, respectively. No combined all-green result is claimed.

Both original certified P-B and fresh UUID UI P-B actually reach READY/PASS_WITH_WARNINGS, one RESULT_XLSX, 3×6/18 exact values, no formulas, 24 checks, source warnings and separate DQ-017/PB-AC-006/007 PASS. Actual HTTP XLSX/QA checks verify bodies, SHA-256, sizes, MIME, names and exact report linkage. The original-identity scenario uses the approved isolated P1/P3/P4 procedure; its explicit simulated API test actions are not live owner Approvals. The UUID scenario retains the original two separate explicit UI test actions. Generic five-versus-six remains FAIL.

Recognition-only controls reject 34 semantic/input/output mutations; an additional original-ID/wrong-source control fails. Twelve real persisted-context negatives reject invalid source/Spec/Run/Approvals on disposable copies. The existing SQLite CHECK prevents a forged approver before persistence; it was not disabled. P-A exact 277-byte golden and P-D authoritative NEEDS_FIX/FAIL diagnostic remain covered, with restart, corruption, ownership, idempotency and no unauthorized business writes.

## Resources and platform

Both actual 100000×200 P5 exports reread all 20000000 values independently. CSV: PASS, P5 elapsed 102.17889795200608 seconds, incremental peak RSS 171474944 bytes. XLSX: PASS, P5 elapsed 541.6580616589927 seconds, incremental peak RSS 189276160 bytes. Expanded-text negative: 299601477 internal bytes, safe EXPORT_FAILED, zero new final Artifacts/QAReports and unchanged P4 bytes. This rejection is not a positive-workload substitute.

P6 actual verified download: 40500998 bytes, incremental peak RSS 120795136 bytes against 536870912. Conservative admission and sampled memory remain unchanged. Actual injected allocation failure revokes the newly registered URL (HTTP 404), exposes no new widget/snapshot and changes no business rows. Frozen Streamlit private compatibility and preverified-snapshot last-click limitations remain explicit.

Linux native and clean Linux-host Docker smoke actually pass on this exact source: unchanged frozen-lock install, health 200, P-A Result/QA HTTP, container removal/recreation on the same mount, exact row/payload persistence and fresh-session reprepare. Actual Mac Docker is NOT RUN. `MACOS_DOCKER_T19_HANDOFF.md` gives the exact source SHA/tree, real host/container requirements, explicit human workflow, readback/hash/restart evidence and separate T19 rerun procedure. No success receipt is fabricated.

## Preservation and evidence

All 1914 owner-start files were independently compared by bytes/blob/mode: 1907 unchanged; seven explicitly authorized modifications. P6 runtime, app integration, conftest, P0–P4/P5 historical tests/contracts/fixtures/schema/migrations/dependencies/governance and original FAILED evidence remain unchanged. Available P0 passes do not imply full positive coverage of the 13 absent P-C originals; no replacement fixture exists.

Original T06/T07 were actually rerun on frozen `deddc2799464076227173bd2e4890f552ffe64bf` / tree afc4126ccddce4ca4615ac411b1dd6281a98a960, giving two real FAIL and exit 1. That reproduction and original manifest integrity are preserved separately. Uncommitted dev-focused-01 recorded two passes and a new test-harness failure when SQLite correctly rejected an impossible approver mutation; dev-focused-02 correctly asserted that denial and passed all three selected tests. Neither diagnostic is substituted for final exact-tree outcomes.

Complete commands, timestamps, versions, exits, stdout/stderr, JUnit, unique ID inventories, guards, resources, protected-file hashes, source diff, Mac handoff and finite SHA-256 manifest are included. Temporary output writes from historical tests were captured and restored exactly by the unchanged recorder. The later evidence-only commit/published HEAD is separately identified; its full runtime suite was not rerun.

**Handoff: BLOCKED pending actual Mac-host P6-T19 and separate owner review. CR-P6-002 recognition correction passes its executed Linux obligations; no P6 VALIDATED, Gate B closure, merge or Pilot release is claimed.**
