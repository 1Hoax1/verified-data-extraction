# P3 Validation Report

Implementation evidence for owner review. P3 Gate B remains open; no P3 VALIDATED declaration, merge or P4 start is performed.

Tested commit: `6a8e67252131c2b6a6a70388aa47ead899c35140`. Authorized main baseline: `ba73d05d2294dfb7e51b9c3c758e63c6065286d6`.
Run started `2026-10-11T10:24:01.812723+00:00`; finished `2026-10-11T10:24:40.528153+00:00`.

| Suite | PASS | FAIL | ERROR | SKIP | XFAIL |
|---|---:|---:|---:|---:|---:|
| P3-T01…P3-T52 | 52 | 0 | 0 | 0 | 0 |
| P2-T01…P2-T54 | 54 | 0 | 0 | 0 | 0 |
| P1-T01…P1-T42 | 42 | 0 | 0 | 0 | 0 |
| Total | 148 | 0 | 0 | 0 | 0 |

Actual command from repository root: `/workspace/verified-data-extraction/.venv/bin/python tests/p3/run_validation.py`.
This executes `/workspace/verified-data-extraction/.venv/bin/python -m pytest tests/p3 -q --junitxml=docs/p3/validation/p3-results.xml`.
P3-T49 and T50 actually execute separate `pytest tests/p1` and `pytest tests/p2` subprocesses with their own JUnit files, then verify every required ID. Exact argv/stdout/stderr are in [P3 log](p3-run.log), [P1 log](p1-run.log), [P2 log](p2-run.log). JUnit: [P3](p3-results.xml), [P1](p1-results.xml), [P2](p2-results.xml). All 148 individual results: [test status](TEST_STATUS.md).

Environment: `Linux-6.18.44-x86_64-with-glibc2.41`; Python `3.12.14`; Streamlit 1.50.0, openpyxl 3.1.5, pytest 8.4.2, frozen uv dependency graph. Full installed versions and source/test SHA-256 values: [summary](validation-summary.json). Tests use temporary POSIX workspaces with SQLite foreign keys, P1 BEGIN IMMEDIATE/CAS and filesystem durability barriers. UI uses real Streamlit AppTest; restart/crash checks use separate Python processes.

Approved P3 ZIP SHA-256: `8a77848419161a5f784b61e7302a058e5c23e2ff5925e88a643c350e80930bc7`. All 64 manifest entries, sizes and hashes verified. [Verifier --repo](fixture-verifier.log) confirms 40 reachable profiles, pinned P0 bytes, NFC oracle and rejection of five corrected Approval mutants. This design verifier explicitly reports runtime tests NOT_RUN; the separate [runtime scenario evidence](scenario-results.json) records all 40 actual fixture drivers PASS.

P0 P-A/P-B previews, Brief/Spec documents and semantic hashes match unchanged goldens. P-C forbidden confirmation fields/context and P-D schema negatives are checked at their proper schema boundary. P0 NFC/RFC8785 vectors and the F07 exact normalized digest pass. All normative packs and P1/P2 runtime, migration and lock bytes are unchanged from the authorized baseline.

P2-T54 regenerates all 21 XLSX binaries in a new temporary directory and compares exact bytes; all 12 CSV fixture hashes are verified. [Fixture evidence](fixture-verification.json). Both stress probes scan 100000 rows with five preview rows and no dataset handle, including the upload buffer:

| Source | Incremental peak RSS, bytes | Limit, bytes | Result |
|---|---:|---:|---|
| CSV | 198193152 | 536870912 | PASS |
| XLSX | 153718784 | 536870912 | PASS |

Measurement uses fresh-process Linux VmRSS 5 ms samples and kernel ru_maxrss; the larger observed peak is used. Exact buffers, shapes, hashes, argv, baselines and peaks: [CSV](rss-csv.json), [XLSX](rss-xlsx.json).

Atomicity: injected EventLog failure covers every P3 mutation; stale expected Order and a late CAS failure leave all business rows unchanged; actual connection.commit failure rolls back final Approval/Order/EventLog. [Crash evidence](crash-restart-results.json) checks both approvals after uncommitted writes and after completed commit with abrupt process exit; fresh processes see the complete prior or committed state. Trusted restart preserves exact pointers, hashes, Approvals and EventLog. Tampered authoritative JSON/source blocks trust; degraded/blocked health prevents mutations. Exact duplicate approvals add no row/event. Streamlit completes the existing-Order workflow without SQL edits, keeps unsaved drafts in session only, and passive reruns produce zero business writes.

CR-P3-002 is implemented solely at the historical test boundary: P2-T40 and every original negative probe remain; explicit P1/P2 modules are frozen; reviewed P3 paths/app integration are allowed. P3-T51 checks the complete source inventory, hashes/surfaces, dependency graph, migration and actual SQLite tables, with forbidden integration/execution/dependency/schema/runtime-drift probes. [Versioned amendment](../../p2/amendments/v1.1/P2_TEST_PLAN_AMENDMENT.md), [traceability](TRACEABILITY.md).

Known limitations: CR-P3-001 remains deferred, so APPROVED revisions are blocked. Drafts are not durable. No Order creation, P4 execution, exports or QA is offered; P-D data-dependent preflight/parse/QA outcomes belong to later stages. RSS guards are sampled Linux checks, not an OS memory sandbox. Static inventory/hash audits are regression controls, not proof against deliberately obfuscated code. Immutability is enforced through supported APIs and verified loads, not against a hostile SQLite administrator. AppTest is automated Streamlit coverage; no separate human browser sign-off is claimed. No new normative conflict or unresolved implementation blocker was found; owner review and Gate B decision remain pending.

Initial unsuccessful development runs are preserved under [attempts](attempts/): 39/49 failures before correcting P2 selection adaptation, 4/49 before fixing criteria-reference validation/harness classification, 1/52 when the original positional P2 UI test encountered added P3 controls, and 1/52 from a setup assertion incorrectly assuming UUID order for two approvals timestamped in the same second. These were uncommitted development states, with no claimed exact source SHA. P3 now opens through an explicit checkbox, preserving P2 UI behavior and its original T35 assertions; no P2 test criterion was weakened. The setup assertion matches each exact approval tuple independently of UUID ordering. Final evidence above comes only from the committed tested source. Historical P2 closure artifacts are restored after regression outputs are copied into this P3 directory.

The subsequent evidence commit may change only `docs/p3/validation/`; its PR head is distinct from the tested code commit. Owners should use the tested SHA and source hash manifest when reviewing results.
