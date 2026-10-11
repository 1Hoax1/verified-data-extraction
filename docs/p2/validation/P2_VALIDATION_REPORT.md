# P2 validation report — runtime checks PASS; owner Gate B closure pending

Report date: 2026-10-11, Europe/Moscow. **P2 is NOT_VALIDATED. Gate B is NOT_PASSED pending the separate explicit owner decision. PR #2 remains Draft; no merge or P3 work.** All required runtime acceptance tests now pass. The earlier stopped/failed report and original XML/traces remain in [history/initial](history/initial/P2_VALIDATION_REPORT.md).

## Checked code and approved basis

- Repository: `1Hoax1/verified-data-extraction`; branch `feat/p2-local-ingestion`; [PR #2](https://github.com/1Hoax1/verified-data-extraction/pull/2), target `main`.
- Synchronized main/base: **`129300728c446b82eaeafe1068e27339eb7176dd`**. Merged into the existing branch before continuing implementation.
- Exact tested commit: **`a6c845b552656b42d81850fc3372871df979f6c2`**. Both final test commands below ran after this commit, with source/tests/lock unchanged. Later commits contain validation documentation/evidence only. RSS and fixture JSON explicitly record this tested commit.
- Authority: `DECISIONS.md`, P2 Gate A, unchanged P2 Implementation Pack v1.0, unchanged validated P0/P1 contracts/runtime, and **APPROVED [CR-P2-001](../../change_requests/CR-P2-001.md)**.
- ZIP SHA-256: `1fed602bcea695be892150581b9cbcb00807681f0a389f598bd54fac9e504d84` (308,846 B). The archive was never changed.

## CR-P2-001 implementation and changes

P1-T30 retains its test ID, forbidden imports/module names and exact table-set assertion. Its historical import audit now checks the explicit 13-file P1 inventory, excluding the authorized P2 integration entry point `app.py`. All other P1 test bodies remain unchanged. [Versioned test-plan amendment](../../p1/amendments/v1.1/P1_TEST_PLAN_AMENDMENT.md) and [traceability amendment](../../p1/amendments/v1.1/TRACEABILITY_AMENDMENT.md) describe the approved boundary; original `docs/p1/v1.0/` is immutable.

P2-T40 independently audits all application source, including the entry point/P2 readers/UI, and all changed/untracked repository paths. Its reviewed versioned policy enumerates paths, imports, call/definition surfaces and frozen P1/migration SHA-256. Direct/optional/build dependencies, existing transitive lock graphs/artifacts/versions/sources and entry points are checked. New source or policies require a visible reviewed policy diff; the test does not regenerate its own allowlist. Negative copied-tree probes reject external integrations, ORM, LLM, Telegram, browser automation, service/queue/worker imports, dynamic import/exec/eval/subprocess, JSON/URL ingestion, Order/P3/workflow/execution/QA/export calls, new migrations/tables and altered dependencies. Full application inventory has no additional database model, migration or runtime service.

P2 ingestion now maps corrupt deflate `zlib.error` and malformed/truncated ZIP/XML to unchanged P0 `INPUT_UNREADABLE`, with no success result. The guarded ZIP adapter also counts actual inflater output before `ZipExtFile` could trim it to a forged declared size. Global metadata limits precede expansion. Selected-only read-only openpyxl traversal avoids opening unselected sheet/chart payloads; shared-string limits, DTD/entity rejection, typed projections, formula cache checks to EOF, first-five retention and sampled RSS checkpoints remain enforced. P0 P-B's approved generic XML content-type fallback is preserved; explicit incompatible/macro workbook types fail closed.

T35 uses an actual Streamlit `UploadedFile` with a string filename: preview/reruns add no InputAsset/EventLog, and explicit repeat upload creates a separate immutable asset. T51 uses P1's actual `.staging` directory and validates degraded opt-in verified reads, denied writes and blocked reads/writes without repair. T54 runs deterministic regeneration and fresh-process CSV/XLSX probes with actual uploader buffers. Source path → requirements → all tests: [IMPLEMENTATION_TRACEABILITY.md](IMPLEMENTATION_TRACEABILITY.md).

## Environment and dependency reproduction

Linux 6.18.44, x86_64, glibc 2.41; writable `/workspace` overlay filesystem. Python **3.12.14** (Clang 22.1.3). pytest **8.4.2**, Streamlit **1.50.0**, openpyxl **3.1.5**, et-xmlfile **2.0.0**, jsonschema **4.26.0**, referencing **0.37.0**, rfc8785 **0.1.4**. [runtime-and-hashes.json](runtime-and-hashes.json) records interpreter/platform, versions, archive/golden/policy/lock hashes and checked code SHA.

Actual setup/check commands, from repository root:

```sh
UV_CACHE_DIR=/tmp/vde-uv-cache uv lock --check
UV_CACHE_DIR=/tmp/vde-uv-cache uv sync --extra test --frozen
```

Both succeeded. Only approved openpyxl and its et-xmlfile dependency were added to the P1 lock; existing transitive dependency records, including distinct numpy resolution branches, are unchanged. The temporary cache avoids the read-only home cache. uv used its normal copy fallback when cross-filesystem hard links were unavailable.

## Final actual execution results

At checked commit `a6c845b552656b42d81850fc3372871df979f6c2`:

```sh
.venv/bin/python -m pytest tests/p2 -q --junitxml=docs/p2/validation/p2-results.xml > docs/p2/validation/p2-run.log 2>&1
.venv/bin/python -m pytest tests/p1 -q --junitxml=docs/p2/validation/p1-results.xml > docs/p2/validation/p1-run.log 2>&1
```

| Suite | PASS | FAIL | ERROR | SKIP | pytest duration | Exit |
|---|---:|---:|---:|---:|---:|---:|
| P2-T01..P2-T54 | **54** | **0** | **0** | **0** | 18.16 s | 0 |
| P1-T01..P1-T42 | **42** | **0** | **0** | **0** | 4.89 s | 0 |

No deselection, skip, xfail, removed IDs or audit bypass in the final commands. The recorded XML was parsed and checked for complete distinct ID sets (54 P2 and 42 P1) and zero failure/error/skip counts. P2-T39 additionally executed all 42 P1 tests as a separate subprocess and asserted the same complete ID/count conditions; the following standalone command produced the final P1 XML.

Actual JUnit: [p2-results.xml](p2-results.xml), [p1-results.xml](p1-results.xml). Full stdout/stderr: [p2-run.log](p2-run.log), [p1-run.log](p1-run.log). Every ID and actual status: [TEST_RESULTS.md](TEST_RESULTS.md). Host timestamps are UTC in XML; the final runs started on October 11 at approximately 02:24 Moscow time.

## Golden/fixture/resource evidence

**P0 golden equality PASS:** T03 deep-equals the immutable P-A CP1251/comma preview; T25 deep-equals the immutable P-B `Orders` preview, four cached numeric formula cells and exact one-warning summary. Their binary/input/preview SHA-256 values are in the runtime/hash artifact. T39 asserts no diff in P0 or original P1 pack against main.

**Fixtures PASS:** the pytest session extracts the approved ZIP into temp storage and checks all **57 manifest entries**, exact byte lengths and SHA-256. T37 actually reads every one of **12 CSV / 21 XLSX** catalog cases and checks preview/error outcomes and unchanged P0 diagnostic schemas. T54 regenerates all **21 XLSX** binaries by running the unchanged approved builder in a different temporary directory, then compares each whole file byte-for-byte. [fixture-verification.json](fixture-verification.json) records the builder argv/stdout, checked SHA, archive hash and all generated XLSX/CSV hashes.

Additional static verifier actually rerun:

```sh
python /tmp/vde-p2-_su_4kc6/P2_Implementation_Pack_v1.0_APPROVED/fixtures/verify_materialized_fixtures.py
```

It returned exit 0/PASS for binary hashes/cache metadata/ZIP caps/guard reachability. Its final `NOT_RUN` line is the immutable pack's historical design-only runtime disclaimer, **not** this implementation's test result; runtime evidence is the executed suites above.

**Fail-closed/resource checks PASS:** T30/T44..T47 spy on the inflater to prove metadata rejection before expansion. T52/T53 first confirm prior ZIP guards pass, then reach exact row/column/preview-cell guards; CSV row/column and 1 MiB retained JSON limits also execute. T29 adds unsafe-path/duplicate-normalized-name/symlink/encrypted-metadata, UTF-8/UTF-16 DTD/entity, corrupt compressed-member and forged inflated-size checks. T27 proves selected missing cache after preview row five is fatal; T28 proves unselected unsafe sheet XML is not opened. P1 fault/promotion/checksum/cross-order/restart and degraded/blocked tests pass. No partial result, persisted parse status, business-state transition, versions/Approval/run/QA/export is produced. Header-only success carries no QA verdict.

## Real RSS results

T54 launches fresh Linux processes with P1 bootstrap/seed completed before measuring current idle RSS. It then includes deterministic fixture creation, real Streamlit `UploadedFile` buffers, registration, P1 verified byte read and full preview. Independent `/proc/self/status` VmRSS samples run every 5 ms; Linux `ru_maxrss` (KiB ×1024) supplies an additional conservative lifetime peak. The accepted delta is `max(sampled_peak, kernel_peak) - idle_baseline`. Runtime checkpoints inside the actual readers sample after source load/preflight/chunks and every 1,000 rows. A separate injected-observation test proves the checkpoint returns P0 `INPUT_UNREADABLE/RUNTIME_RSS_LIMIT` above the budget.

| Probe | Raw B | Rows / columns | Idle RSS B | Sampled peak B | Kernel lifetime peak B | Conservative incremental peak B | Limit B |
|---|---:|---|---:|---:|---:|---:|---:|
| CSV | 99,000,880 | 100,000 / 198 | 50,360,320 | 248,549,376 | 248,434,688 | **198,189,056** | 536,870,912 |
| XLSX | 1,384,403 | 100,000 / 2 | 50,380,800 | 64,806,912 | 200,519,680 | **150,138,880** | 536,870,912 |

Both probes **PASS**. Both retained five rows and no dataset handle. Raw stress checksums, interpreter/platform, start UTC, durations, argv, buffers and all exact readings: [rss-csv.json](rss-csv.json), [rss-xlsx.json](rss-xlsx.json). T54 generated both outputs at the checked SHA. XLSX stress deterministically removes only the last over-limit row from a temporary copy of the approved row-limit binary and preserves original ZIP metadata; the fixture pack is unchanged. Large bombs are rejected by metadata and are never expanded by these probes.

Kernel lifetime high-water may include startup/fork/fixture-generation allocations before the idle reading; it is intentionally conservative and not an exact attribution to worksheet traversal. For XLSX, the separately observed preview-period VmRSS peak is much lower than that lifetime high-water. Reported deltas use the higher value rather than hiding it.

## Scope/immutability checks and limitations

`git diff --check`: **PASS**. Whole-application/source/dependency/changed-path audit: **PASS**. Diff against synchronized main is empty for `pecs/pilot_slice_v1/`, `docs/p1/v1.0/`, the approved P2 archive and P1-owned production files/migration. Their frozen runtime bytes are additionally SHA-checked by T40. `app.py` changes only the approved local upload/preview integration. `DECISIONS.md` and the approved CR record are not rewritten by this PR; their earlier failure/status descriptions are historical owner records, superseded for runtime evidence by this report, not by a new Gate B decision.

Remaining limitations, none waived by passing tests:

- Linux/overlayfs, Python 3.12.14 and pinned openpyxl were actually tested; Windows, other Python versions, network filesystems and physical power loss are unvalidated.
- Sampled RSS is best effort, **not an OS hard sandbox**. The two representative stress scenarios do not promise every valid near-limit workbook completes under all host conditions. Source bytes remain whole-buffered by P1; no O(1) memory claim.
- openpyxl and Python ZipExtFile internals are used by the guarded selected-sheet adapter; changing parser/interpreter versions requires rerunning compatibility/safety/RSS checks.
- Formula caches are never calculated or refreshed; freshness is the operator's responsibility. Nonstandard/ambiguous packages or unsupported projections fail closed.
- Static allowlist/negative scope tests supplement source review, not semantic proof against deliberately obfuscated behavior inside an already permitted call. P1 persisted workflow models remain present, while P2 does not author them.
- Streamlit AppTest validates options/preview/reruns and an actual UploadedFile exercises the shared registration helper; browser-native file chooser interaction was not automated. Production still needs a pre-existing P1 Order; no Order-create UI was added.
- No separate CI, independent-host validation, standalone-wheel packaging or multiuser/concurrent filesystem mutation guarantee was added. P1 recovery remains detect-only.

**No remaining implementation failure or newly discovered normative contradiction is known from these checks.** CR-P2-001's corrective work is implemented and tested. The remaining release blocker is the separate owner review/closure of P2 Gate B. No merge, P2 VALIDATED declaration or P3 start is performed.
