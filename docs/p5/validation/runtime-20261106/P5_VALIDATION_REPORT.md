# P5 Export and Deterministic QA — technical validation report

Date: 2026-11-06T17:56:03.411778+03:00.

**Result: IMPLEMENTED / TECHNICALLY VALIDATED / NOT MERGED.** This is a technical result for owner review; it is not owner acceptance or closure of P5 Gate B. Gate B remains NOT_PASSED pending the owner's separate decision. No P6, merge or governance repin was performed.

## Authority, implementation and exact tested tree

The owner explicitly approved Gate A/Q01–Q08, CR-P5-001/002 and CR-P5-003. The latter's separate decision was read first from GitHub commit `820245fc544fc66c393db548151e6d281e03d414`. Versioned technical addendum v0.2c was committed as `20e78e55c8f461d01b9671c475ba7fa98ae0a745` before implementing its numeric behavior; original source archives and historical PROPOSED text remain unchanged.

- Branch: `feature/p5-export-deterministic-qa`.
- Owner-authorized start: `820245fc544fc66c393db548151e6d281e03d414`.
- **Tested implementation commit: `801cc2ba5db46494eaa93e5b963c3bc2f936ddc2`.**
- **Tested implementation tree: `2fc4b0dee77c6040cddf9831aecd253e9aa96a9b`.**
- The subsequent evidence-only commit/publication head is recorded separately after its creation. No full runtime regression on that descendant is claimed merely because its source bytes match.

P5 consumes real verified P4_INTERNAL_V2, keeps original P4 bytes/tags/checksum/Run unchanged, and applies only the approved exact integer→Decimal projection in approved decimal fields. It produces one authorized CSV or XLSX, performs full readback and all 23 DQ IDs, and uses existing P1 Artifact+Event then QAReport+Order+completion-Event commits. Existing committed Artifact reuse, detect-only orphan recovery, strict version/Approval binding, no resurrection of failed P5 Runs, read-only terminal replay and an explicit Streamlit action are implemented.

## Three separate regression families — CR-P5-002

| Family | Exact source | Observed outcome |
|---|---|---|
| Historical P1–P4 | `fd39aa1bed480313504ae8b1f76e77e170cb72ba`, tree `9d9f492491792a75b76954b3a17d1a376bc333e9` | **212/212 PASS**: P1 42, P2 54, P3 52, P4 64; zero fail/error/skip/xfail; pytest wall time 359.145s |
| Original legacy tests on actual P5 tree | Tested implementation SHA/tree above | **206 PASS; 6 pytest FAIL classified EXPECTED_HISTORICAL_SCOPE_CONFLICT; 0 blocking behavioral regressions** |
| P5 runtime acceptance on actual P5 tree | Same tested implementation SHA/tree above | **76/76 PASS**, complete actual ID inventory, zero fail/error/skip/xfail |

The integrated legacy exit code remains **1**, not 0. The exact conflict IDs are `P2-T40, P3-T50, P3-T51, P4-T61, P4-T62, P4-T63`. P2-T40/P3-T51/P4-T61/T62 reject the added approved P5 application scope. P3-T50 fails because its nested unchanged P2 suite fails P2-T40; P4-T63 contains the corresponding nested P2/P3 scope failures. The classifier checks actual child JUnit and exact assertions, and the new successor audit independently verifies the allowed integrated scope. These failures are never PASS, skip or xfail. No integrated 212/212 or combined 288/288 PASS claim is made.

## Actual stress and resource controls

| Format | Actual output / independent check | Entire P5 incremental sampled RSS | P5 export+QA wall time |
|---|---|---|---|
| CSV | READY + QA PASS, 100000×200, **20000000 cells independently checked** | 171479040 bytes | 101.505s |
| XLSX | READY + QA PASS, 100000×200, **20000000 cells independently checked** | 189489152 bytes | 557.092s |

Both are distinct isolated simulated approved Orders. Each uses the exact pinned 40500998-byte CSV source (SHA-256 `353698a4bab0ffc54633cb3fabad7eb404821b5f97dfeb7eb9676dafec4d9239`) with separately approved CSV/XLSX output format. This proves actual export and QA for both formats; it is not an XLSX input-ingestion stress claim. All headers, every output cell, actual output size/hash and zero-formula semantics are checked. Runtime RSS sampling is 10ms; the independent worker samples at 5ms. Each is within the approved 536870912-byte incremental bound. No new hard P5 time SLA is invented.

A separate actual approved-operation 100000×200 expanded-text P4 result of **299601477 bytes** reaches P5 and is rejected before unsafe full-buffer allocation: EXPORT_FAILED, FAILED Order, zero new final Artifact/report, original P4 checksum unchanged. A forced-budget control, oversized XLSX text, signed64/Decimal precision extremes and intentionally bypassed preflight are additional negatives. None replaces either successful fixed workload.

## Goldens, numerical semantics and deterministic QA

- Actual P-A export equals the immutable 277-byte CSV golden, including original P4 `integer:0` in its approved decimal field projected as `0.0`; QA PASS / READY.
- Actual isolated P-B v2 export has six headers, three rows and 18 exact cells, one production RESULT_XLSX and 24 check results including separate DQ-017(PB-AC-006/007); source cached formulas produce PASS_WITH_WARNINGS, exported formulas remain zero. Its 245-byte CSV is only a test projection and is never registered as another production result.
- Actual P-D diagnostic CSV equals the immutable 118-byte golden; lexical roundtrip PASS coexists with typed DQ-011/012/014 blockers, QA_BLOCKER and NEEDS_FIX. No false READY or null→empty typed repair.
- Whole-service signed64 CSV tests include 2^53 boundaries and signed64 extrema in both strict integer and approved decimal fields. All forbidden numeric conversions remain negative. XLSX 15-digit/magnitude admission and independent raw-XML/openpyxl numeric guards reject loss, wrong type and numeric-as-text. NFD Unicode, quoting/newlines and explicit XLSX text remain unchanged data.
- Brief and Spec field domains/uniqueness are both enforced; referenced criterion IDs/targets remain distinct. Full-row metrics, exact rational null thresholds, ordered approved operation bindings, complete mandatory/conditional coverage and deterministic FAIL authority are retained. DQ-020/021 and LLM checks are absent.

## Schema, scope, recovery and failure evidence

Actual real P0 schemas: **20 schemas; 121 positive schema applications PASS**. All 116 present P0 manifest payloads match; 13 original P-C files are still absent. The 24 available negative examples include 15 schema rejections and 9 cases requiring semantic guards; original legacy behavior and available negative assertions remain executed. Full P-C positive/golden coverage is explicitly unavailable.

The four unchanged source verifiers pass against real P0 where applicable; **42/42 static mutation probes rejected** (4+9+14+15). They are static checks, not substitutes for the 76 runtime IDs. Their preserved historical stdout headings do not override subsequent owner approvals.

The successor integrated audit passes and rejects **17/17** mutations covering source, historical tests, P0 schemas/fixtures, migrations, dependencies, DECISIONS, G3 pin, old/new policies, unknown modules/files, imports, arbitrary execution, new operations and UI auto-triggering. Ambiguous final Artifacts are rejected without writes. Its finite new-source/test/document list and committed HEAD/index/mode checks preserve all historical inputs; the active G3 pin stays SHA-256 `95b7c92a417ec06a80f3d4e839e136e00100e4313d1bee021c94f5beda1f0df7`.

Actual SIGKILL witnesses cover orphan-after-promotion detect-only behavior, reuse after Artifact commit and read-only repeat after final commit. Report-UoW abort rolls back report/Order/Event together while retaining exactly one committed Artifact; explicit retry reuses it. Concurrent initial calls create one result/report. Source corruption blocks writes; writer errors, unsafe CSV formulas and altered staged data fail closed; passive Streamlit rerenders add no records.

## Preservation and evidence provenance

`PROTECTED_FILES_BEFORE_AFTER.json` compares every owner-start file: **882 unchanged**, with exactly the authorized two-line `src/vde/app.py` append as the sole old-file edit. There are 23 new implementation/addendum/test/document paths plus that one edit; exact inventory/diff are included. P0–P4 contracts, runtime modules other than the permitted app integration, old tests/assertions, original fixtures/packages/evidence, migrations, dependency/lock files, DECISIONS and G3 pin remain unchanged. Test-generated historical outputs were captured under the new evidence root and the prior bytes restored, with source/commit/tree checks after each phase.

All final mandatory phases belong to the tested implementation SHA/tree above; the historical phase has its separately stated frozen identity. Full raw stdout/stderr, commands/environment/exit codes, JUnit, actual test-ID inventory, reports, small generated golden outputs, hashes and fixture/negative/recovery/resource observations are included. The unchanged original handoff ZIP is already in the repository; temporary unpacked duplicate source files are omitted from this evidence copy and are reproducible from that archive.

Earlier committed candidate `e332519fb10dfb72717876d2cbe502f23b1be54a` and development diagnostics are separate. Its legacy suite also produced 206 PASS/6 scope failures, but the first outer classifier omitted the P3-T50 cascade and stopped before P5 runtime. That new P5 runner was corrected; no historical assertion was altered. Dirty development checks are diagnostics only, not exact-tree Gate B evidence. No earlier validation evidence is overwritten or retroactively marked PASS.

The next candidate `8a8b8ace8944acacc24ba1e33a29f700d5e5b334` executed all 76 P5 tests: 75 passed and T72 failed while preparing the separate expanded-text negative's Spec, because the new generator omitted the existing mandatory `replace.params.regex=false`. Both successful stress exports on that earlier candidate are preserved, but its complete run remains FAILED. Only the new generator was corrected to conform to the unchanged P0 schema, then all mandatory actual-P5 phases were rerun on the final implementation SHA/tree above. No contract, fixture or assertion was relaxed.

## Limits and handoff

- P-C: 13 missing certified historical originals; full positive coverage is not claimed.
- P-B v2 positive mechanics use isolated simulated local-user workflow actions. Supplied future TEST_ONLY Approval is rejected as live authority. No real business Approval is issued by these tests or by the owner's project-level CR approval.
- Local single-process serialization and sampled Linux RSS are measured controls, not distributed locking, OS memory isolation, a universal worst-case success guarantee, Windows validation or physical power-loss proof.
- P5 Gate B, acceptance and integration approval remain solely with the owner/Main Managing Chat. No merge, governance repin or P6 was performed. Remote main/branch and published object verification are recorded separately after publication.

**Handoff recommendation: independent owner review of the technically validated P5 candidate under CR-P5-002. Gate B remains NOT_PASSED until the owner's separate decision.**
