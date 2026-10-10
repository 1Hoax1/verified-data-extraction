# P2 validation report — CHANGES_REQUIRED / implementation stopped

Report date: 2026-10-11 (Europe/Moscow). P2 is **NOT_VALIDATED**. Gate B is **NOT_PASSED**. This draft records a partial implementation and real failed checks, not a completed P2 release. P3 has not started.

## Checked code and authority

- Repository: `1Hoax1/verified-data-extraction`.
- Base: `main`, `21b37476ea5792f8a93f31964ed3490ef66191eb`.
- Branch: `feat/p2-local-ingestion`.
- Code tested: `151e25867339785ed0cbe64230c05ec8fa551a78`. The development test command ran before that commit; the commit captured exactly the code tested, with no subsequent source/test corrections. Later commits add evidence only.
- Approved archive: `docs/p2/v1.0/P2_Implementation_Pack_v1.0_APPROVED.zip`.
- Archive SHA-256: `1fed602bcea695be892150581b9cbcb00807681f0a389f598bd54fac9e504d84`, matching `DECISIONS.md`.
- Extracted into `/tmp/vde-p2-_su_4kc6/P2_Implementation_Pack_v1.0_APPROVED`; all 57 manifest entries matched size and SHA-256. All 21 XLSX binaries and 12 CSV fixtures are present. The approved ZIP is unchanged.
- Read Scope/Acceptance, Modules/API, CSV/XLSX Policies, Resource Limits, Preview/Asset, Error/Recovery, Test Plan, Traceability, Release Gate, decisions/open questions, and P1 compatibility audit. Inspected relevant frozen P0 schemas/policies/goldens and P1 runtime/API.
- `git diff origin/main -- pecs/pilot_slice_v1 docs/p1/v1.0 src/vde/storage.py src/vde/workspace.py src/vde/models.py src/vde/persistence`: empty. No normative P0/P1 artifact or P1 persistence runtime was changed. `DECISIONS.md` and Gate A record are unchanged.

## Blocking contract discrepancy / required Change Request

Approved `docs/p1/v1.0/P1_TEST_PLAN.md`, P1-T30:

> No P2+ module, network call, LLM, Telegram, marketplace, queue/worker, dataset-row table or API service exists.

The validated executable `tests/p1/test_p1.py::test_T30_p1_scope_audit` scans **all** `src/vde/**/*.py` and rejects `csv` and `openpyxl` imports. It has no phase-specific boundary excluding an approved P2 ingestion implementation.

Approved P2 D01 and Modules/API require stdlib CSV and openpyxl under `src/vde/ingestion/`; P2-T39 and Gate B require **all 42 P1 tests PASS**. With the existing P1-T30 audit, adding the mandated P2 readers fails that criterion. The actual rerun confirms this: P1-T30 fails on the `openpyxl` import, while the other 41 P1 tests pass.

Implementation stopped at discovery, following the owner's instruction to stop on a normative contradiction. No P1 test was weakened, skipped, monkeypatched or silently reinterpreted. Request an explicit Change Request/authoritative resolution defining how the historical P1-only scope audit applies during approved P2 regression. A proposed resolution is to audit the frozen P1 modules for P1 exclusions, and audit the whole application separately for P2 exclusions; this has **not** been implemented or approved. The source contracts and runtime storage behavior need no change on current evidence.

## Runtime and dependencies

Linux `6.18.44`, x86_64, glibc 2.41, writable `/workspace` overlay filesystem; single local Python process. Python `3.12.14`, Clang `22.1.3`.

Pinned versions used: pytest 8.4.2; Streamlit 1.50.0; openpyxl 3.1.5; et-xmlfile 2.0.0; jsonschema 4.26.0; referencing 0.37.0; rfc8785 0.1.4. `uv.lock` includes only the approved direct reader dependency openpyxl and its et-xmlfile transitive dependency. Dependencies installed into the repository `.venv`.

Actual setup commands:

```sh
UV_CACHE_DIR=/tmp/vde-uv-cache uv lock
UV_CACHE_DIR=/tmp/vde-uv-cache uv sync --extra test --frozen
```

The initial default-cache uv invocation failed because `/home/agent/.cache/uv` is read-only; using the writable temporary cache succeeded.

## Actual commands and results

Static fixture verification:

```sh
cd /tmp/vde-p2-_su_4kc6/P2_Implementation_Pack_v1.0_APPROVED
python fixtures/verify_materialized_fixtures.py
```

**PASS:** 21 XLSX SHA/size, 12 CSV samples, OOXML cache presence, four ZIP-limit metadata cases, corrupt ZIP/XML, row/column counts, preceding ZIP preflight guards for T52/T53 fixtures, exactly 65,537 code points for T53, positive openpyxl scalar smoke. Full deterministic builder regeneration was planned in T54 and is **NOT_RUN**.

Development acceptance run, from repository root:

```sh
.venv/bin/python -m pytest tests/p2 -q -k 'not T54' --junitxml=/tmp/vde-p2-development.xml
```

Exit 1: **49 PASS, 4 FAIL, 0 SKIP, 1 deselected/NOT_RUN**, 12.12 s. All P2 IDs are implemented as test cases, but P2-T54 was excluded from this first development run. The normative regression discrepancy was then discovered, so the planned final full run did not occur. JUnit records 53 executed cases, zero errors/skips, four failures. The XML was copied unchanged to [p2-results.xml](p2-results.xml).

P1 regression command actually executed by P2-T39:

```sh
.venv/bin/python -m pytest tests/p1 -q --junitxml=docs/p2/validation/p1-results.xml
```

Exit 1: **41 PASS, 1 FAIL, 0 SKIP, 0 errors**, 5.09 s. Failed P1-T30: scope audit rejects the required openpyxl import. [p1-results.xml](p1-results.xml) is the actual subprocess output.

All 96 acceptance IDs and their real individual status: [TEST_RESULTS.md](TEST_RESULTS.md). Full failure traces: [p2-failures.txt](p2-failures.txt), [p1-failures.txt](p1-failures.txt).

`git diff --check` executed: **PASS**.

## Behavior exercised and remaining defects

- P2-T03/T25 **PASS**: exact deep equality with unchanged P0 P-A/P-B previews. P-B cached scalars and one aggregate formula warning match the golden.
- P2-T37 **PASS**: actual readers exercised every approved CSV/XLSX fixture case; expected previews/errors and P0 public diagnostic schema validation passed. The separate corrupt compressed-member case below still fails.
- P2-T27/T42/T43/T50 **PASS**: selected missing cache fatal; `t=str,<v/>` preserved as empty string; cached Excel error projected with a warning. No formula evaluation.
- P2-T30/T44..T47 **PASS**: monkeypatched inflater proves unsafe resource ZIPs reject before member expansion. T52/T53 first verify ZIP preflight acceptance, then reject at row/column/cell caps. CSV row/column caps and retained preview JSON cap were also exercised.
- P2-T02/T11/T33/T34/T36/T38 **PASS**: original byte storage/hash, failed parse retaining bytes, cross-order rejection, restart, checksum failure and metadata fault injection. No versions, approvals, runs, QA reports, artifacts or Order business-state mutation.
- P2-T01/T24 **PASS**: Streamlit AppTest lists P1-created Orders and requires an explicit worksheet selection.
- **P2-T29 FAIL — implementation defect:** corrupted deflate member raises an uncaught `zlib.error` rather than a P0 `INPUT_UNREADABLE`. Needs fail-closed error mapping.
- **P2-T35 FAIL — harness defect:** `Mock(name='local.csv')` sets mock identity rather than its `.name` attribute. The upload test passes a Mock where a filename string is expected; rerun/re-upload behavior is not validated by this case.
- **P2-T39 FAIL — blocking discrepancy:** P1 regression has 41 PASS / P1-T30 FAIL as detailed above.
- **P2-T51 FAIL — harness defect:** test uses `staging/incomplete` instead of P1's actual `.staging/incomplete` path. Full degraded/blocked acceptance remains unproven by T51. Some recovery behavior passed separately in T38.

These failures were not corrected after the instruction-triggering discrepancy was found. Their presence is explicit; the draft is unsuitable for merge or Gate B closure.

## RSS and known limitations

**P2-T54 NOT_RUN.** No real baseline, peak or additional RSS measurement exists for this code. Compliance with the **536,870,912 B incremental peak limit is UNPROVEN**. Runtime `/proc/self/status` checkpoints are drafted; observed-limit rejection still needs a dedicated test. `tests/p2/rss_probe.py` prepares fresh-process Linux sampling plus `ru_maxrss` for near-100 MB/100k-row CSV and 100k-row XLSX, but neither probe was run. No RSS result JSON is fabricated or supplied.

Other unvalidated aspects: full deterministic fixture regeneration, end-to-end uploader simulation (Streamlit's AppTest uploader limitation; helper coverage needs correction), complete adversarial ZIP/XML safety and actual-stream-count cases, library allocations between sampled RSS checkpoints, non-Linux operation, physical power loss and network filesystems. Runtime checkpoints are best effort, not an OS hard memory sandbox. P1 original-byte API remains whole-buffered. No claim of O(1) memory, formula-cache freshness, or deterministic QA PASS is made.

## Release disposition

**CHANGES_REQUIRED / STOPPED_PENDING_CHANGE_REQUEST.** Publish only a draft PR for review of this concrete partial result and blocker. Do not merge, mark P2 VALIDATED or start P3. Required follow-up: resolve P1-T30 acceptance boundary, correct defects, review remaining safety edges, execute all 54 P2 and 42 P1 cases without exclusions, measure RSS, and produce a new report for the final checked code SHA. Gate B closure still requires a separate owner decision.
