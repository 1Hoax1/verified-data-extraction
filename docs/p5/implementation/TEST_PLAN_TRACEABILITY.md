# P5 runtime test traceability

The immutable handoff defines 76 IDs. The original Design v0.2a and Supplement v0.2b remain under the unchanged source handoff ZIP; v0.2c CR-P5-003 changes only the authorized numeric boundary. All runtime assertions use actual computed observations. TEST_ONLY fixture or approval records are never business authority.

| IDs | Execution and oracles |
|---|---|
| T01–T46 | 23 DQ positive/negative pairs from the immutable external `dq_cases.json`; exact status/severity/affected_count/actual/schema. Additional actual service/readback cases cover P-B local order semantics, integer/decimal positive/negative conversions, two range criteria, six-column/all-cell numeric roundtrip. Shared pure predicates also evaluate actual runtime observations. |
| T47–T54 | Eight explicit not-applicable CheckResult instances are SKIPPED/INFO; each pytest acceptance test itself must PASS, with no pytest skip/xfail. |
| T55 | Actual P4 P-A → exact 277-byte CSV golden + PASS; P4 bytes and Run unchanged; additional NFD Unicode/quoting/newline preservation. |
| T56 | Actual P-B new immutable v2 Spec with isolated exact simulated Approval → one XLSX 3×6, 18 cells, 24 results and cached-formula warning; explicit formula-like text remains text. |
| T57 | Actual P-B semantic rows → exact 245-byte CSV projection in test scratch only; no second production Artifact. |
| T58 | Actual P-D → exact diagnostic CSV, lexical readback PASS, typed DQ-011/012/014 FAIL, QA_BLOCKER and NEEDS_FIX. |
| T59/T66 | Forged Approval/wrong selected context fail before writes; published P-C schema negatives and exact 10-available/13-missing inventory; old P-B Spec does not authorize criterion 007. |
| T60 | Missing required output column → safe FAILED, no fabricated final Artifact/report. |
| T61/T62 | Real duplicates and parse SET_NULL → deterministic blockers; approved parse warning does not hide an actual wrong date; null/empty lexical policy remains distinct from typed QA. |
| T63/T64 | Writer errors; dangerous CSV strings after whitespace/C0 prefixes; actual numeric precision preflight and bypass/readback failures; full signed64 CSV boundaries in integer and decimal fields; XML/reader/type mutations; XLSX text capacity; changed staged CSV. |
| T65 | Corrupt referenced internal bytes → blocked storage and zero business writes. |
| T67 | Two competing initial calls and terminal repeats → one Artifact/report; later calls read-only. |
| T68–T71 | Actual SIGKILL before metadata/after Artifact/after final commit; orphan detect-only, committed Artifact reuse, report-UoW rollback and read-only terminal restart. |
| T72 | Separate actual CSV/XLSX 100000×200 successes, each full 20M-cell independent comparison and sampled incremental RSS ≤512MiB; separate actual full-shape expanded-text refusal plus forced-budget control. No replacement of either success with a safe failure. |
| T73 | External actual 212 historical JUnit/complete IDs plus 76 P5 definitions; no recursive whole-suite invocation. Actual collected IDs/outcomes independently checked by outer runner. |
| T74 | Real P0 schemas and supplied immutable report specimens; duplicate DQ-ID/criterion multiplicity; original contradictory P-B golden and missing ref remain recorded. |
| T75 | Actual Streamlit AppTest click once, passive rerender twice, no duplicate records. |
| T76 | Successor whole-application audit with protected files/HEAD/index/modes/governance; finite P5 paths; negative code/test/schema/fixture/migration/dependency/pin/policy/import/dynamic-execution/operation/UI/file probes; ambiguous final Artifact rejection. |

The runner reports three separate result families: historical 212 at frozen base, unchanged legacy compatibility on actual P5 tree (including exact scope-only failures), and actual P5 T01–T76. It never claims an integrated 288/288 PASS without that actual outcome. Detailed commands, observations, failures, limitations and hashes belong to new validation evidence; this definition document is not a runtime PASS claim.
