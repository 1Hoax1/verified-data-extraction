# CR-P4-005 Stage B — integration validation evidence

**Technical result: PASS. Gate B: NOT_CLOSED. PR #4: DRAFT / UNMERGED.**

Integration branch: https://github.com/1Hoax1/verified-data-extraction/tree/integration/p4-cr-p4-005-20261101

Exact implementation/tested HEAD: `a868134fb9f3118bd5e56c26662db55fe281430d`. Exact tested tree: `0150b2eccb498d86b6e0ecf2cbc854a6de381f39`.
Main parent: `966f2dd98c897302940d6b200769bfe640f57bef`; PR #4 head: `222869da1d56c833851d44f25b87e8180f97562d`; isolated integration merge: `2658ad92d54c6eb6ed017be4dde4acff436c20df`. Neither main nor PR #4 was updated/merged. All final phase results refer to the same committed tree. Evidence is deliberately packaged outside the Git tree so the published integration HEAD remains the exact tested commit.

## Authority and mechanism

Real fetched GitHub objects independently confirmed the owner's G/B/H/L/M and ancestry before implementation. G `f65e175708bc52058cbaf288d6953f2ac5ba5a50`, B `fee2ec5795db8307f6201ea2883d37b508ffd366`, H `0eb02c0a72188b14c24ee2f247f5bf036736033b84611f5f07035352b0564c00`, L 33056, M 100644. Exact approved proposal SHA-256 also matched. See `independent-stage-a-verification.json` and immutable Stage A receipt copy.

One closed-schema pin, SHA-256 **`9d75ee4d3f7cd03cf111f070dad73e8b6fe4590fc910abf0fedf880072743f0f`**, is independently fixed in the test verifier and P4 policy. It binds exact Git ancestry, HEAD/index/working document bytes and mode. No normalization, alternate hashes, automatic latest-main or general DECISIONS allowlist. Historical singleton negatives, baseline, all source/dependency/schema/migration protections and P4's full independent audit/frozen/T63 checks remain. Copied-tree probes require verified real authority. Versioned amendment v1.3 documents the exact test-only change.

## Actual final phases

| Phase | Exact argv (cwd `/workspace/p4-cr005-integration`) | Result |
|---|---|---|
| positive-02 | `python -m pytest tests/p2/test_p2.py::test_T40_scope_dependencies tests/p3/test_p3.py::test_T51_whole_application_scope -q` | 2 PASS; exit 0 |
| scope-02 | `python -m pytest tests/p4/test_execution.py::test_T61_forbidden_scope tests/p4/test_execution.py::test_T62_whole_application_scope_CR_P4_001 tests/p4/test_execution.py::test_T63_frozen_regression_evidence_and_p0 -q` | 3 PASS; exit 0 |
| full-01 | `python -m pytest tests/p1 tests/p2 tests/p3 tests/p4 -q` | **212 PASS; exit 0** |

P1 42/42, P2 54/54, P3 52/52, P4 64/64; zero failures/errors/skips/xfails. Pytest 8.4.2, Python 3.12.14, jsonschema 4.26.0; full platform/packages/env and timestamps in each `runs/*/command-environment.json`. `PYTEST_ADDOPTS` explicitly records the JUnit output path; the requested argv remains unchanged. Full stdout/stderr, exit code, JUnit and per-ID results are retained for each phase. Empty stderr where observed is retained as a zero-byte file.

F38/X19/W45 all PASS after initializing fresh test-output maps; P0 goldens/strict verifier PASS, 9/9 isolated mutations rejected, original crash/load and nested regressions executed. Stress runtime 58.054262s, additional measured peak RSS 293617664 bytes. Generated outputs, subprocess commands and complete runtime logs are in `runs/full-01/generated/`.

## P01–P05 / N01–N14

All **19 criteria PASS** (59 recorded subcases). Full details and the 52 isolated Git driver commands/stdout/stderr are in `runs/full-01/generated/docs/p4/validation/cr-p4-005/governance-results.json`. An additional N09 check on the same source commit/tree is captured with its full command/output in `runs/independent-n09/`.

P01 real exact authority, P02 actual changed/untracked inventory and historical positives, P03 authorized clean copy, P04 unchanged document on descendant history all execute positive checks. **P05** exercises future repin only with scoped synthetic test authority in a disposable clone; it does not rotate or approve the real active pin. **N09** executes independent comparison to the actual owner receipt and confirms the documented human-review boundary. Its extra isolated check actually replaces both candidate pin and verifier P: the rewritten verifier mechanically accepts its own new trust anchor, while P4's separate policy and the unchanged owner receipt reject it. This is not owner approval and does not claim local tests can authenticate an owner after all trust anchors are rewritten. Every other N criterion exercises actual rejected mutations/provenance/pin/frozen/path conditions. Negative success means the unauthorized state was rejected.

## Scope, evidence integrity and deviations

Exactly nine files changed by CR-P4-005, listed in `CHANGED_FILES.txt`. All 42 production files, P0 schemas/fixtures, original approved packs/ZIPs, dependencies/lock and SQLite migrations equal PR #4. DECISIONS, approval records and Stage A receipt equal official main. Two historical test files have only the approved positive-call context substitution; all old negatives are retained.

Each phase snapshotted old validation files, captured generated results separately, restored original bytes, verified unchanged code/test input hashes and returned a clean checkout. Original 2026-10-30 failure artifacts/archive are also hash-verified unchanged. No new P4 Pack, production implementation, Gate B closure or merge was performed.

`development-attempts/` retains the earlier test-only Unicode probe failure. The approved real document contains no decomposable codepoints; the probe was corrected to use changed Unicode spellings and a scoped exact G2 normalization check. No verifier/runtime policy was weakened. All three final phases then passed on the single SHA above.

Limits: P05 and N09 have the explicit approval-boundary meanings above; Linux/Python 3.12.14 only, no independent-host/CI assertion, inherited P0 P-C discrepancy unchanged, existing sampled-RSS/soft-timeout limits unchanged. No contract conflict or scope expansion was discovered. Main managing chat alone decides Gate B.

Remote post-publish verification: integration HEAD equals the tested SHA; main remains `966f2dd98c897302940d6b200769bfe640f57bef`; PR #4 remains open/Draft/unmerged at `222869da1d56c833851d44f25b87e8180f97562d`. See `POST_PUBLISH_VERIFICATION.json`.
