# P5 — Export and deterministic QA

Owner-authorized implementation under Design Pack v0.2a, P-B Supplement v0.2b, Q01–Q08, CR-P5-001/002 and the [v0.2c numeric addendum](../design_addenda/P5_DESIGN_ADDENDUM_v0.2c_CR_P5_003.md). Original source ZIPs and P0–P4 tests/contracts stay immutable. This document does not close P5 Gate B or authorize merge/P6.

`P5Service(env).complete(run_id, expected_order)` is an explicit local action after successful P4 transformation. It verifies source bytes, exact immutable Brief/Spec/Approval links and canonical P4_INTERNAL_V2. Only decimal fields in the approved Spec get exact integer→Decimal semantic projection. P4 bytes, tags, checksum and Run stay unchanged. Wrong type/null/range/uniqueness remains visible to deterministic QA; no arbitrary parsing, Unicode data normalization or LLM override is performed.

One approved-format result is written to bounded scratch, fully reopened and checked before publication. CSV uses strict UTF-8/LF, approved dialect and exact lexical projection; formula-like strings fail closed. XLSX uses explicit text cells, conservative numeric admission and independent XML/openpyxl comparisons; no numeric-as-text fallback. P1 stores an extensionless opaque `payload`, so XLSX readback opens a binary stream rather than inferring a filename extension.

The existing P1 Artifact+Event commit and a separate QAReport+Order+completion-Event UoW are preserved. A deterministic Artifact ID and bounded process-local locks prevent local double publication. Explicit retry verifies/reuses a committed final Artifact; an orphan or blocked/degraded workspace is detect-only. A terminal repeat verifies the existing report/artifact read-only; CAS is retained for every mutating transaction. QA FAIL yields NEEDS_FIX and a clearly diagnostic file. Pre-publication export/roundtrip failure yields FAILED when a safe failure transaction is possible. Report-transaction abort leaves EXECUTING with one committed Artifact eligible for explicit reuse. P4 Run remains succeeded.

The Streamlit integration adds one explicit Export + deterministic QA action; passive renders do not start it. Download/delivery workflow is P6 and is absent.

## Validation protocol

The historical 212 tests run unchanged at `fd39aa1bed480313504ae8b1f76e77e170cb72ba`. On the actual committed P5 tree, ALL old tests run separately. Only precise old whole-application scope assertions caused by approved P5 are recorded as EXPECTED_HISTORICAL_SCOPE_CONFLICT; they remain pytest failures, never PASS/skip/xfail. Any behavioral regression blocks. The successor P5 audit freezes all existing files at owner start commit `820245fc544fc66c393db548151e6d281e03d414`, permits only its finite P5 paths and exact two-line app append, and retains G3 governance verification. New evidence needs its own finite SHA-256 manifest under the specified new root. No old audit/pin is changed.

Run on a clean committed P5 checkout with existing pinned dependencies:

```bash
PYTHONPATH=src:tests python -m p5.run_validation \
  --historical-run /absolute/path/to/fresh-historical-212-run \
  --out /absolute/path/outside-repository/p5-validation
```

The historical run must include actual JUnit and `command-environment.json` for that exact base, with all 212 IDs and unchanged-source/evidence checks. A preserved example runner is `docs/p5/validation/implementation-admission-20261106/historical_recorder.py`; record any absolute worktree/output-path adaptation separately. The outer P5 runner records exact implementation commit/tree, commands/environment, stdout/stderr/JUnit and all 76 P5 IDs; it captures/restores old tests' generated evidence without rewriting historical reports. Test-only stress runs use two distinct simulated approved Orders, both from the pinned 100000×200 CSV source, with independently approved CSV/XLSX output formats. Both actual outputs and all 20M cells per output are checked. This does not claim a 100000×200 XLSX ingestion benchmark. An additional actual expanded-text 100000×200 P4 result proves bounded P5 preallocation rejection. Sampled RSS is measured, not hard OS isolation; no new hard P5 time SLA is asserted.

P-B v2 positives are isolated tests with simulated local-user workflow actions. Supplied TEST_ONLY/future Approval is not imported as live authority. Actual business operation still needs its own exact real Approval. Thirteen original P-C manifest files remain missing; only available negatives are supported. No complete P-C positive, Windows durability or arbitrary worst-case resource success is claimed.

The integrated legacy probe also records cascaded scope failures: P3-T50 invokes P2-T40, and P4-T63 invokes the corresponding P1–P3 regressions. Classification checks their actual nested JUnit and exact scope assertions; it does not exempt arbitrary nested failures. A failed P5 Run is never resurrected after another P4 execution. The UI's terminal view uses the verified read-only decision API, and reuses extensionless stored XLSX bytes through a binary reader. Nullable trailing XLSX cells retain their logical header-defined width; physical out-of-contract columns are rejected. Both Brief and Spec field domains/uniqueness remain enforced. Temporary workbook XML is cleaned after failed staging as well as after success.
