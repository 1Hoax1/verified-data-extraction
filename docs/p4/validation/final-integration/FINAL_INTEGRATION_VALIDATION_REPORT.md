# Final P4 Integration Validation — approved G2 repin

**Technical result: PASS. Gate B: already CLOSED / PASS by the owner, unchanged. PR #5 remains DRAFT / UNMERGED. Merge authorization is NOT_GRANTED.**

Repository: `1Hoax1/verified-data-extraction`. Branch: `release/p4-final-integration`. PR: https://github.com/1Hoax1/verified-data-extraction/pull/5

Initial release commit: `2115e51e6036404b5134b984c9c176bbd562f2f4`. Exact tested implementation commit: **`d4ad0c297a67b4eae6a3ae1b018dc6fa73a6e2ed`**. Exact tested tree: **`1ce97d0ba09dcd03d1120ac8e5a32a91ff3a32db`**. Every final positive/scope/full-regression result uses this same commit/tree. Publication may add a separate evidence-only child; no test run on that child is claimed. The owner-authorized Gate B closure remains tied to its previously validated snapshot, and this report supplies the separately requested final combined-tree verification.

## Verified receipt and bounded implementation

Before edits, real fetched GitHub objects and ancestry independently confirmed G1 → G2 → main → initial release. G2 `27cdea7b204c36e839f1c3b1a8de387f64c0a91e`, B2 `90cbcbaf9838dcee9cc87b889958b15816b4b0fd`, H2 `035f180a346ff9f1c9a5074e872d2eb10e1d6dd1a289acf90f7eeb7d372e4782`, L2 36955, M 100644. Release DECISIONS matches the G2 blob. Source of truth: `docs/p4/validation/P4_GATE_B_CLOSURE.md` and the immutable owner repin receipt (copied here as `OWNER_G2_REPIN_RECEIPT.json`); details are in `independent-g2-verification.json`.

Exactly three implementation files changed: `tests/p4/approved_governance_pin_v1.json`, `tests/scope_policy.py`, `tests/p4/scope_allowlist_v1.json`. Only the active tuple and its two expected SHA-256 literals changed. New pin P2: **`f7a80b663b7a7347e7f38bb2aaf6281f6d1dce4344f079be02cc45210de3d050`**. All test definitions/negative probes, the P4-start baseline, 42 production files, schemas/fixtures, original packages/ZIPs, dependencies, SQLite migrations and DECISIONS remain unchanged. Full list: `IMPLEMENTATION_CHANGED_FILES.txt`. No new CR or normative amendment was needed under approved CR-P4-005 section 6.

## Actual commands and results

cwd: `/workspace/p4-final-integration`. Python 3.12.14; pytest 8.4.2; jsonschema 4.26.0. Exact package/platform/environment, commands, timestamps, recorded input hashes and exit codes are saved in each run's `command-environment.json`. `PYTEST_ADDOPTS` explicitly records its JUnit destination; the requested command argv is unchanged.

| Run | Command | Actual result |
|---|---|---|
| positive-01 | `python -m pytest tests/p2/test_p2.py::test_T40_scope_dependencies tests/p3/test_p3.py::test_T51_whole_application_scope -q` | 2 PASS, exit 0 |
| scope-01 | `python -m pytest tests/p4/test_execution.py::test_T61_forbidden_scope tests/p4/test_execution.py::test_T62_whole_application_scope_CR_P4_001 tests/p4/test_execution.py::test_T63_frozen_regression_evidence_and_p0 -q` | 3 PASS, exit 0 |
| full-01 | `python -m pytest tests/p1 tests/p2 tests/p3 tests/p4 -q` | **212 PASS, exit 0** |

Full stdout/stderr, JUnit and exit-code files are under `runs/`. P1 **42/42**, P2 **54/54**, P3 **52/52**, P4 **64/64**; failures/errors/skips/xfails = **0**. Exact IDs are checked against recorded JUnit/testcase metadata. P4-T63 also retains its nested 148 historical regressions; their commands, logs and JUnit are captured in generated outputs. All original assertions remain enabled.

## Governance criteria and independent transition controls

**P01–P05 and N01–N14: all 19 PASS, 59 recorded subcases**, on the G2-repinned tree. Detailed cases and Git-driver commands/stdout/stderr: `runs/full-01/generated/docs/p4/validation/cr-p4-005/governance-results.json` (also independently produced in scope-01).

`runs/repin-controls/` independently compares the real active pin with the **new** owner G2 receipt; accepts the exact G2 copy; rejects the previously approved G1 document and old G1 pin; and rechecks N09's trust boundary. A rewritten verifier P can mechanically accept its own substituted trust anchor, while P4's separate unchanged policy and the actual G2 owner receipt reject it. Real code, pin, policy and DECISIONS are verified unchanged after those disposable-copy probes. P05 remains a scoped synthetic future-authority test, never a new real owner decision. Historical test source is unchanged.

## Fixtures, P0, failures/restart and resources

F38/X19/W45 all PASS from freshly initialized test-output maps. Two real P0 goldens PASS. Strict approved-pack verifier returns `STATIC_PINS_REFS_AND_P0_CONTRACTS_PASS`: 36 valid operations, 2 schema-invalid rejections, 1 semantic-invalid case, 2 goldens, 45 precision cases; **9/9 isolated mutations rejected**. Real schemas and fixtures were used; no synthetic P0 replacement.

All existing failure/rollback, SIGKILL/reopen, stale-run and explicit-retry checks execute unchanged; X19 results and individual restart command/stdout/stderr files are preserved under `runs/full-01/generated/docs/p4/validation/`. No automatic resume/adoption or P5 behavior is introduced.

The fresh 100000×200 workload PASS produces 90000×200 output; all **18,000,000** cells match the independent reference. Measured runtime **59.316682s** (limit 120s), additional measured peak RSS **293543936 bytes** (limit 536870912), scratch peak **180144042 bytes** (limit 2147483648), merge fan-in **16**. Result SHA-256 `ea277f2873ed3bd712c7148c2b87035c42ed4cdbbec54edee2d59d63a6b5420b`. Injected resource-limit failures also pass. Full command/output/environment and measured results are retained, not inferred from the earlier Stage B run.

## Evidence integrity, limitations and handoff

Each phase snapshotted historical validation files, captured this run separately, restored original bytes and verified unchanged input hashes/commit/tree and a clean checkout. This includes the approved closure/receipt and previously published Stage B evidence. Earlier failure evidence is also hash-verified unchanged. The only publication additions belong to `docs/p4/validation/final-integration/`; `EVIDENCE_FILES.txt` lists the exact files. `MANIFEST.sha256` covers every published evidence file except the manifest itself. Original stdout/stderr and XML bytes are retained without rewriting.

No production/runtime, test semantics, normative contract, approved pack, dependency/migration or DECISIONS change; no scope deviation was found. Limits remain Linux/Python3.12.14 only; no independent-host/Windows/CI, physical-power-loss or manual-browser claim; sampled RSS/soft deadline; inherited P0 P-C 13-file discrepancy. P05/N09 retain the explicitly documented external approval boundary.

**Present this PASS evidence to the main managing chat for a separate explicit merge authorization. PR #5 must remain Draft and unmerged. Gate B was already closed by the owner and is not closed again by this validation or report.**
