# CR-P4-005 — G3 limited governance repin validation

**Status: IMPLEMENTED / TECHNICALLY VALIDATED / NOT_MERGED.** No owner acceptance or final integration approval is claimed. P4 Gate B remains the owner's existing CLOSED / PASS decision; it was neither reopened nor closed again.

Repository `1Hoax1/verified-data-extraction`; branch `governance/p4-g3-limited-repin`. Immutable base R3 `2ec6a895362f0b1b3a0d81a4930d623e00349441`, governance G3 `d941714bc1d152d0a2189aa954e623460b4e6d03`, previous authority G2 `27cdea7b204c36e839f1c3b1a8de387f64c0a91e`, implementation baseline `7685110506d115805c473b064752f86e9e5c045b`.

## Tested implementation identity

**Implementation commit `bfd4bb4cb18d130027607c5f643993858785cbe4`; exact tested tree `159d2581aff5acc8ccf46ddcc6033e6743b44c64`; only parent R3 `2ec6a895362f0b1b3a0d81a4930d623e00349441`.** All targeted/scope/full runtime evidence below belongs to this one committed implementation tree. A later evidence-only child adds only this folder; its SHA/published branch HEAD is given separately in the final handoff. No independent test execution is claimed on that evidence-only child.

## Authority and exact bounded changes

R3/G3 were fetched from GitHub before changes. API/local immutable objects confirm R3's only parent is G3, G3 descends from G2, and G3/B3/H3/L3/M match the owner's tuple: B3 `be002c5b196b3a374c39fe511d2e1c68477723ab`, H3 `c76e162cca8e044dcc78d3f52a52b57fd230592b17249b6048f6f753618b6d18`, L3 40572, M 100644. The owner receipt and all 52 R3 evidence files are present; their prior manifest is 51/51 PASS. Source heads and initial main are captured in `AUTHORITY_VERIFICATION.json` and `REFS_BEFORE.txt`. No authority was derived automatically from latest main.

The single active pin has the original exact nine-field closed schema and required sorted/indented ASCII serialization plus final newline. Python hashlib and `sha256sum` both yield the independently expected **`95b7c92a417ec06a80f3d4e839e136e00100e4313d1bee021c94f5beda1f0df7`**. Its two expected references match. No self-checksum, alternate authority/hash, wildcard, placeholder or schema/algorithm expansion was added.

Only the three authorized existing files changed. `IMPLEMENTATION.diff` is the exact Git diff; `IMPLEMENTATION_CHANGED_FILES.txt`, `IMPLEMENTATION_COMMIT.json` and `THREE_FILE_HASHES_BEFORE_AFTER.json` contain paths, parent/tree and actual before/after SHA-256 values. The verifier bytes differ only in the literal checksum; the P4 policy differs only in `governance_pin.sha256`. Frozen hashes, source inventories, old DECISIONS baseline hash, ancestry/HEAD/index/disk/mode/type rules and all tests/IDs/negative assertions remain unchanged.

All **653 protected files** have matching R3/implementation Git blobs and independently computed before/after-validation SHA-256. `PROTECTED_FILES_BEFORE_AFTER.json` records every comparison; original R3 hashes are preserved in `R3_FILE_HASHES_BEFORE.json`. DECISIONS, production, schemas/contracts/fixtures/packages, SQLite migrations, dependencies/lock and all historical evidence remain unchanged.

## Executed commands and mandatory results

cwd `/workspace/p4-g3-limited-repin`. Python 3.12.14, pytest 8.4.2, jsonschema 4.26.0; actual platform, versions, full argv/env, timestamps, stdout/stderr, exit codes and JUnit are in each `runs/*/` folder. `PYTEST_ADDOPTS` explicitly records a JUnit destination, while the requested pytest argv remains unchanged.

| Run | Actual argv | Result |
|---|---|---|
| positive-01 | `python -m pytest tests/p2/test_p2.py::test_T40_scope_dependencies tests/p3/test_p3.py::test_T51_whole_application_scope -q` | 2 PASS, exit 0 |
| scope-01 | `python -m pytest tests/p4/test_execution.py::test_T61_forbidden_scope tests/p4/test_execution.py::test_T62_whole_application_scope_CR_P4_001 tests/p4/test_execution.py::test_T63_frozen_regression_evidence_and_p0 -q` | 3 PASS, exit 0 |
| full-01 | `python -m pytest tests/p1 tests/p2 tests/p3 tests/p4 -q` | **212 PASS, exit 0** |

Verified exact ID sets: P1 **42/42**, P2 **54/54**, P3 **52/52**, P4 **64/64**; fail/error/skip/xfail **0**. `MANDATORY_TEST_IDS.json` contains the complete unique inventory and actual results; JUnit and stdout are retained. T63 executes its nested historical 148-test regression with original assertions, not merely static ID counting.

## Governance controls

All original **P01–P05 / N01–N14 PASS: 19 criteria and 59 recorded subcases**, with no test-definition changes. Full case results and Git mutation commands are in `runs/full-01/generated/docs/p4/validation/cr-p4-005/governance-results.json`, independently produced in the focused scope run too.

Approved G3 passes. Source G2 document and old G2 pin are explicitly rejected by additional executed `runs/transition-controls/` using the actual G3 receipt in R3. Existing cases execute rejection of unauthorized bytes, HEAD/index/working drift, file mode/type/conflict, absent/forged ancestry, pin changes, and forbidden neighboring paths. P04 executes an evidence-only descendant and retains the valid G3 authority without repin. None of these controls modify the real audited checkout.

P05 is a scoped synthetic future-authority simulation; it does not manufacture a real owner decision. N09 and the additional actual-receipt comparison explicitly retain the human approval boundary: a deliberately rewritten local verifier trust anchor can mechanically accept its replacement, while the independent policy and unchanged owner receipt reject it. This limitation is preserved and not presented as cryptographic human authentication.

## Existing integration, recovery and resource checks

Fresh F38/X19/W45 maps all PASS; two real P0 goldens PASS. The immutable approved pack/strict verifier returns `STATIC_PINS_REFS_AND_P0_CONTRACTS_PASS`: 36 schema-valid operations, 2 schema-invalid rejections, 1 semantic-invalid case, 2 goldens, 45 precision cases, and **9/9 isolated mutations rejected**. Real Git checkout P0 schemas were used; no synthetic/replacement fixture or limit weakening was introduced.

Original failure/rollback, SIGKILL/reopen, recovery/stale-run and retry tests execute unchanged, with actual X19 and subprocess evidence in `runs/full-01/generated/`. The 100000×200 workload succeeds with 90000×200 output and all **18,000,000** cells checked. Actual runtime **63.032924s** (limit 120s), additional peak RSS **293326848 bytes** (limit 536870912), scratch peak **180144042 bytes** (limit 2147483648), fan-in **16**. Output SHA-256 `ea277f2873ed3bd712c7148c2b87035c42ed4cdbbec54edee2d59d63a6b5420b`. Existing injected resource-limit cases also PASS; full command/output/environment is preserved.

## Evidence, limits and handoff

The existing recorder snapshots old validation outputs, captures fresh emitted data separately, restores old bytes and verifies unchanged implementation inputs and HEAD/tree after each phase. All phases returned clean checkouts. The supplied receipts' historical preparation/publication text and old P4/G2/G3/R3 evidence were not rewritten. New evidence is confined to `docs/p4/validation/g3-limited-repin/`. Its exact file inventory is `EVIDENCE_FILES.txt`; `MANIFEST.sha256` hashes every new artifact except itself. Original commands/logs/XML/data are retained as observed, not reconstructed from summaries.

No discrepancy or substantive scope deviation was found. Limits: same Linux/Python3.12.14 environment, no independent-host/Windows/CI/physical-power-loss/manual-browser proof; RSS sampled and deadline soft; inherited P0 P-C 13-file discrepancy unchanged; P05/N09 approval-boundary limitations above. A technical PASS does not grant owner acceptance, main integration or P5 authorization.

**Return to Main Managing Chat — Part 2. Publish only this new branch after all mandatory checks pass; preserve G3/R3/main. Do not merge, start P5 design/implementation or request automatic merge. Stop after publication verification and handoff.**
