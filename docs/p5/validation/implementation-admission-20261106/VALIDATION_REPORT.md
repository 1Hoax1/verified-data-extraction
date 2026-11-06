# P5 implementation admission — blocking numeric contract finding

Date: 2026-11-06 (Europe/Moscow).

**Result: BLOCKED — CR-P5-003 PROPOSED; no completed P5 implementation or Gate B validation is claimed.**

The owner-authorized implementation was started after verifying the supplied archive. Actual P4 integration exposed a new numerical contract conflict. Work on that boundary stopped under the user's explicit instruction to propose a CR when an approved contract needs clarification. The unfinished draft was retained outside the repository; this review commit contains new documentation/evidence only. All 765 existing handoff-HEAD files, including application code, historical tests, fixtures, schemas, dependencies, DECISIONS.md and active G3 pin, are byte-identical.

The decision-ready proposal is [CR-P5-003](../../../change_requests/CR-P5-003_PROPOSED.md). It requests an explicit, lossless integer→Decimal semantic view only for approved decimal fields. It is not enacted by this report.

## Exact source and execution identities

| Item | Full identity |
|---|---|
| Repository | `1Hoax1/verified-data-extraction` |
| Authorized working branch | `feature/p5-export-deterministic-qa` |
| Initial branch HEAD | `d3f5d1898c9e90e08a5e518131e7f32d30b34a65` |
| Initial branch tree | `6946f1c52ed7b991f764573f69d15e1e50075906` |
| Historical test/reproduction commit | `fd39aa1bed480313504ae8b1f76e77e170cb72ba` |
| Historical test/reproduction tree | `9d9f492491792a75b76954b3a17d1a376bc333e9` |
| Main checked through GitHub API before publication | `fd39aa1bed480313504ae8b1f76e77e170cb72ba` |

The handoff commit adds only `docs/p5/OWNER_APPROVAL_AND_CODEX_HANDOFF.md` to the historical base. Production source and original tests are identical at both commits. `BASELINE_DIFF.txt` and `PROTECTED_FILES_BEFORE_AFTER.json` record these checks. API ref snapshots and exact commands are included. Publication commit identity is necessarily recorded separately after commit creation; it is not fabricated inside its own hashed report.

## Source archive integrity and authority

Original handoff ZIP SHA-256: `3e3a2f6a8e65f500fe5bd281ef805d9229d50b96c50433cdda52cbb4fd6d63e4`.

- Handoff manifest: **10/10 PASS**. The packaged validation summary describes an earlier nine-file count; the actual manifest contains ten entries. Actual contents and checksums were used, without rewriting the source archive.
- Design v0.2a archive SHA-256 `a351fb55c5ea3d442cc3ff3e3facc7a09c426569aad476fb713f8f09f10ca3ac`; **60/60 manifest PASS**.
- Supplement v0.2b archive SHA-256 `4e08285b00344f2d00a7af89a723a835f931f4bceb768b11ec1aaf637fd0ae18`; **26/26 manifest PASS**.
- ZIP CRC checks PASS. The unchanged source handoff archive is retained under `docs/p5/handoff/` for reproduction. Its README, owner authority, complete design documents, numeric overrides, supplement and CR texts were reviewed against real GitHub checkout objects.
- Owner authority and current GitHub handoff record supersede the enumerated historical PROPOSED headings. No new owner decision is inferred from checksum or technical validation.

## Executed checks and actual outcomes

| Phase | Exact command / source | Observed result |
|---|---|---|
| Historical original suite | `python -m pytest tests/p1 tests/p2 tests/p3 tests/p4 -q`, cwd `/workspace/p5-historical-regression`; external recorder adds JUnit through `PYTEST_ADDOPTS` | **exit 0; 212 passed in 351.42s**; P1 42, P2 54, P3 52, P4 64; zero failures/errors/skips/xfails |
| Actual P4 numeric compatibility | `python reproduce_numeric_handoff.py --repo /workspace/p5-historical-regression --out .../numeric-handoff/probe`, with frozen checkout `src`/`tests` in `PYTHONPATH` | **exit 1; two failing compatibility cases**, five observed integer-in-decimal cells |
| Strict Design Pack check | `python tools/verify_p5_design_pack.py --p0-root /workspace/p5-historical-regression/pecs/pilot_slice_v1 --require-p0 --mutation-probes` | exit 0; real P0 report schemas and static goldens PASS; 4/4 static mutations rejected |
| v0.2 amendment static check | `python tools/verify_p5_v02_amendments.py --mutation-probes` | exit 0; 9/9 static mutations rejected |
| v0.2a numeric static check | `python tools/verify_p5_v02a_precision.py --mutation-probes` | exit 0; 26 static numeric cases; 14/14 static mutations rejected |
| v0.2b supplement static check | `python tools/verify_gate_a_supplement.py --base-root <unpacked-v0.2a> --mutations` | exit 0; 60 baseline pins checked; 15/15 static mutations rejected |
| Available real P0 schema check | `python validate_available_p0.py --p0-root <frozen-checkout>/pecs/pilot_slice_v1 --out .../schema-results.json --supplement <unpacked-v0.2b>` | exit 0; 20 real schemas checked, 121 positive schema applications PASS, 24 negative examples inspected: 15 schema rejections and 9 requiring semantic guards |

Full command argument arrays, actual cwd, stdout, stderr, exit codes and environment are saved in each run directory. The successful historical 212 JUnit and independently verified complete mandatory-ID inventory are separate from the deliberately failing compatibility JUnit. The probe creates no production P5 RESULT and uses only disposable test databases. Its two cases are not P5-Txx acceptance tests.

Historical validation outputs created by the unchanged old tests were captured under `historical-212/generated/`; every old evidence file was restored to its original bytes. The run recorder verifies a clean committed historical tree, unchanged input hashes and unchanged commit/tree. Existing old audits and their negative assertions were executed without edits.

Static source verifiers retain historical status text such as `NOT_PASSED` and `PROPOSED` in their original stdout. Those fields describe the unchanged historical source verifier, not a reversal of the owner's subsequent approval. Likewise their `P5_runtime=NOT_RUN` is not promoted to runtime PASS.

## Blocking facts and why static PASS does not settle them

Actual immutable P4 results contain:

- P-A row 3 revenue: canonical `integer:0`, although approved field type is decimal.
- P-B rows 1/2 unit_price: `integer:10` / `integer:20`; line_total: `integer:20` / `integer:20`, although those approved fields are decimal.

Literal Q03 runtime-type dispatch produces P-A **275** bytes, SHA-256 `90295d6f974a564dd389de463912c4a0878c8ee000894e0553b5ae4c38d78d20`, instead of the frozen **277** bytes / `c3b4e1f9a885bcf969cd34a9041951c1bed1abcd6aaba4c4f1f2fcd414d86cc9`.

P-B's test-only CSV projection gives **237** bytes / `cd660986eddd4f1977ace62f9762dd94399111e2150bb3bdb6f40b6b142b94d9`, instead of **245** bytes / `1e9449a8ff90f0cac9d62ba94b3d6e812dd565f85e9dd91fb2b48b6cbbf4d3c6`.

The numeric static verifier reconstructs decimal values from golden CSV strings. It does not exercise the actual upstream tags for these goldens. Strict DQ-011/016 typing therefore also needs explicit clarification before the required P-A/P-B runtime positive can honestly pass. The old P4 golden helper's field-aware widening is test-only, not automatic production authority. No numeric coercion has been approved or implemented through this CR.

These are substantive numeric-contract findings and **must not** be classified `EXPECTED_HISTORICAL_SCOPE_CONFLICT`.

## Phase-aware status required by CR-P5-002

| Required evidence family | Current status |
|---|---|
| Original P1–P4 historical base | **212/212 PASS** on exact historical SHA/tree only |
| Legacy compatibility on a completed real P5 implementation tree | **NOT_RUN**; completed P5 implementation tree does not exist |
| New successor integrated P5 scope audit | **NOT_IMPLEMENTED / NOT_RUN** |
| P5-T01…T76 runtime acceptance | **NOT_RUN**, not 76 PASS and not skipped/xfail |
| Actual P5 P-A/P-B positive export | **BLOCKED** by CR-P5-003 |
| P5 CSV and XLSX 100000×200 stress | **NOT_RUN** |
| P5 restart/recovery/idempotency/fault acceptance | **NOT_RUN** |

No integrated 212/212 or combined 288/288 result is claimed. Historical P4 fixture, recovery and stress checks executed by the 212 suite retain their original meaning and do not substitute for P5 tests or P5 CSV/XLSX stress.

## Existing limitations, distinct from the new CR

1. P0 manifest verification found **116/116 present payloads match**, with **13/129 declared originals absent**, all in P-C. Available schema validation passed; complete original P-C positive/golden coverage is **BLOCKED** and not fabricated.
2. P-B v2 exact live local-user Approval remains unissued in the supplied supplement. Its future-2099 TEST_ONLY Approval passes schema/binding checks only, never grants business authority. Isolated simulated workflow approvals used in this reproduction are clearly labeled test data.
3. A first auxiliary P0 negative-classification collection inferred schema names from filenames too broadly. It was corrected to inspect the document's discriminator fields, then rerun. Both original attempt, its exact source snapshot and corrected authoritative result are retained. The original attempt is not used as negative-conformance proof; final results are under `available-p0/`.
4. No final P5 resource, platform-portability, live-business approval or release-readiness claim is possible at this checkpoint.

Environment: Python **3.12.14**, pytest **8.4.2**, jsonschema **4.26.0**, referencing **0.37.0**, rfc8785 **0.1.4**, openpyxl **3.1.5**, Streamlit **1.50.0**, Linux x86_64. Existing dependencies were reused without changes.

## Handoff and scope

All changed paths are new CR/source-copy/evidence documents. Production code, all old test scenarios/assertions, P0–P4 packages, contracts, SQLite migrations, dependency files, DECISIONS.md, active G3 pin, original handoff anchor and historical validation evidence remain unchanged. The unfinished candidate source was removed from the publication tree and retained externally as an unvalidated draft, not offered as a validated implementation.

The proposed CR requires a separate owner decision before applying its new numeric rule. P5 implementation remains authorized within previously approved scope but blocked at this boundary. P4 Gate B remains CLOSED / PASS; P5 Gate A remains CLOSED / PASS; P5 Gate B is not closed. No merge, automatic PR integration, governance repin, new business Approval or P6 action was performed.

**Recommendation: owner review of CR-P5-003; do not claim P5 technical completion or Gate B readiness.**
