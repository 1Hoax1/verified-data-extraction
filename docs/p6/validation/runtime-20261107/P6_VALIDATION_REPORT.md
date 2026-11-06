# P6 — implementation validation report

Date: 2026-11-07T01:27:06.946899+03:00.

**Outcome: BLOCKED. P6 is not declared VALIDATED. P6 Gate B remains NOT CLOSED. No merge, governance repin, Pilot release or next stage was performed.**

## Exact source and authority

- Branch: `feature/p6-streamlit-e2e`.
- Approved main baseline: `0af4a1ff49ccf8fa59c39780d749e15cb5042fc3`.
- Approved implementation start: `b93e0ef4ed69343968ff7ae4188d586c0d1485a5`.
- **Tested implementation commit: `deddc2799464076227173bd2e4890f552ffe64bf`.**
- **Tested implementation tree: `afc4126ccddce4ca4615ac411b1dd6281a98a960`.**
- Subsequent evidence-only commit and published branch HEAD are recorded separately. No full runtime regression on that descendant is claimed.

The three approved design/decision documents were read completely. The later owner Gate A decision supersedes preserved historical PROPOSED/OPEN headings. CR-P6-001 permits only four P6 runtime files, six P6 test files, two new release documents and exactly four app integration lines. The original three authority/design files remain byte-identical.

P6 implements explicit idempotent DRAFT creation; fresh-health/ownership/P5-backed read-only terminal views; one verified immutable Result and QA snapshot; diagnostic labeling; exact QA JSON MIME/serialization; conservative memory admission and sampling; selection/restart invalidation. Two original independent P3 approval actions are retained. No production auto-Approval or arbitrary generated execution exists.

## Blocking findings

1. **P-B behavioral integration failure, CR-P6-002 PROPOSED.** The frozen P3 UI assigns a UUID Brief. Frozen P5 limits PB-AC-002 recognition to literal `brief-pb-v1`; legally adapted P-B therefore gets DQ-010 FAIL / NEEDS_FIX, although its XLSX contains the correct 18 values. P6-T06/T07 retain their required READY/PASS_WITH_WARNINGS assertions and are real FAILs. This is not a scope conflict. No P5 fix, forced fixture ID, acceptance-criterion change or false READY was applied.
2. **Actual Mac-host Docker smoke NOT RUN.** This machine is Linux and no Mac host was supplied. T19 actually executes Linux launch/restart checks, then remains a real pytest FAIL because required Mac evidence is absent. Linux Docker evidence does not stand in for Mac execution.
3. Any other actual failure or blocking regression remains visible in the raw JUnit and summary; it is not excused by the two findings above.

## Actual mandatory test outcomes

P6: **17 PASS, 3 FAIL, 0 ERROR, 0 SKIP**, all 20 actual unique IDs. No skip/xfail replacement was used.

| Test ID | Actual pytest outcome |
|---|---|
| P6-T01 | PASS |
| P6-T02 | PASS |
| P6-T03 | PASS |
| P6-T04 | PASS |
| P6-T05 | PASS |
| P6-T06 | FAILURE |
| P6-T07 | FAILURE |
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

| Regression family | Actual outcome and source |
|---|---|
| Historical P1–P4 | Previously executed **212/212 PASS** at `fd39aa1bed480313504ae8b1f76e77e170cb72ba`, cited by exact frozen JUnit checksum. Not rerun or represented as a new P6 result. |
| Historical P5 | Previously executed **76/76 PASS** at `801cc2ba5db46494eaa93e5b963c3bc2f936ddc2`, cited by exact frozen JUnit checksum. |
| Unmodified P1–P4 on tested P6 tree | **205 PASS, 7 real FAIL classified EXPECTED_HISTORICAL_SCOPE_CONFLICT**, 0 blocking behavioral regressions; raw exit 1. |
| Unmodified P5 on tested P6 tree | **75 PASS, 1 real FAIL classified EXPECTED_HISTORICAL_SCOPE_CONFLICT**, 0 blocking regressions; raw exit 1. |

The P6 successor classifier separately proves the old P2-T01 no-Create-button assertion now contradicted by authorized C01, the prior scope assertions, and the exact child JUnit failures in P3-T50/P4-T63. Raw failures remain FAIL, never PASS/SKIPPED/XFAIL. All unclassified behavioral regressions block; the summary records 0 such regressions in legacy suites. P5-T76 rejects the extra approved app integration; the new P6 audit independently proves the finite exception. No combined all-green count is claimed.

## Outputs, resources, corruption and restart

P-A executes the UI-created Order, separate simulated explicit test-user Brief/Spec actions, P4 and P5, and transfers exact 277-byte CSV golden plus the schema-valid QA JSON. P-D executes the corresponding negative route and delivers only a conspicuously named NOT_FOR_DELIVERY diagnostic with QA FAIL / NEEDS_FIX. P-B independently checks all 18 XLSX cells and file hash, but its business QA remains failed; it is delivered only as a diagnostic in this candidate.

HTTP tests use the actual Streamlit media storage and HTTP handler. Response bodies, SHA-256, Content-Length, Content-Disposition and exact CSV/XLSX/QA MIME are independently read back. These are automated isolated test sessions, not owner browser acceptance or live business Approval. A pinned Streamlit compatibility guard buffers widget messages until postbinding RSS succeeds and revokes newly registered media on failure. The injected post-first-registration allocation failure returns HTTP 404 for captured URLs, exposes zero new widgets and changes zero business rows.

The actual generated P5 test artifact used for P6 resource validation is **100000×200**, **40500998 bytes**, checksum `353698a4bab0ffc54633cb3fabad7eb404821b5f97dfeb7eb9676dafec4d9239`. It is copied from an existing isolated generated P5 test workspace, not an owner workspace or a replacement P0 fixture. Actual P6 RSS (including HTTP server/client transfer in the test process) is recorded in T17: **119894016 incremental bytes**, limit **536870912**. Admission accounts for at least 3×Result + serialized QA +64MiB. Both ordinary transfer and tightened-budget/fault denial execute; no refusal is substituted for the successful admitted workload.

The unchanged P5-T72 also actually reruns both approved **100000×200** export workloads on this same implementation tree, with **20000000 independently checked cells per format**:

| Format | Actual result | P5 elapsed seconds | Sampled incremental peak RSS bytes |
|---|---|---|---|
| CSV | PASS | 100.62445555299928 | 171790336 |
| XLSX | PASS | 553.5007339939984 | 188801024 |

The separate expanded-text 100000×200 negative workload has **299601477 P4 internal bytes** and is safely rejected with EXPORT_FAILED, zero new final Artifacts and zero QAReports. Original P4 bytes remain unchanged. Its refusal is not counted as either positive workload. Full worker argv, stdout/stderr, exits, exact cells, input/output hashes and resource samples are retained in `STRESS_TEST_RESULTS.json` and the raw observations.

Corruption checks mutate disposable workspace copies only: source CSV/XLSX, P4 internal/final bytes, approval/hash/context, missing report, altered metadata and degraded/orphan states fail closed. Cross-Order rejection occurs before artifact bytes. Three-plus passive renders, repeat prepare/transfer and restart preserve persisted records/checksums and create no automatic Approval/Run/Artifact/Event. Prepared copies are verified immutable snapshots; the final browser click is not a fresh disk reread. Sampled RSS is not hard OS isolation.

Linux native smoke launches/restarts the app and checks health 200. Clean **Linux-host Docker** smoke at the exact tested commit installs the unchanged lock in an ephemeral writable copy of a read-only source mount, uses the same persistent writable workspace, runs P-A, transfers Result/QA, destroys/recreates the container and verifies byte/row persistence and fresh-session reprepare. Commands, stdout/stderr, versions and actual image digest are preserved. Mac-host execution remains NOT RUN.

## Schema, source preservation and evidence

Actual P0 validation: **20 schemas, 121 positive schema applications PASS**, 116/129 original manifest files present and matching. Thirteen P-C originals remain absent; full P-C positive coverage is not claimed. Available negative schema/semantic guards remain in unchanged executed historical suites and P6 corruption cases.

The successor source audit passes, including a clean extracted positive control and **23/23 rejected mutations**. Protected classes include P1–P5 source, historical tests/policies/evidence, schema, fixture, dependency/lock, migration, governance/pin, authority record, extra path, new owned source/policy and file mode. `PROTECTED_FILES_BEFORE_AFTER.json` independently records all 1461 owner-start files: 1460 unchanged and the exact four-line app edit. Thirteen implementation changed paths comprise 12 permitted additions and that one modification. No historical contract/test/fixture/schema/migration/dependency/governance/evidence bytes are changed; temporary generated old-test outputs are captured and restored exactly after every phase.

Full commands, versions, exits, stdout/stderr, JUnit, test-ID inventory, observations, protected-file hashes, exact diff, CR proposal and a finite SHA-256 manifest are included. The evidence-only descendant is checked for byte/scope identity without claiming a full new runtime run.

Earlier uncommitted development diagnostics and candidate `9838151ca50e10976c85d087fe17ec0d30ae2fea` are separate. Its old-suite run was 205 PASS / 7 FAIL; a P5-only nested-failure classifier then stopped because it expected only the six pre-P6 scope cases. Only the new P6 runner was corrected to prove the authorized CreateOrder assertion and nested cascades; historical tests/assertions were not changed. Earlier failed attempts are not retroactively labeled successful.

**Handoff: BLOCKED pending owner decision on CR-P6-002, the required actual Mac Docker smoke and resolution of every remaining blocking failure. No P6 VALIDATED, Gate B closure, merge or Pilot release is asserted.**
