# P4 Gate B — implementation validation report

**Status: READY FOR INDEPENDENT REVIEW. Gate B NOT_CLOSED; P4 not self-declared VALIDATED.**

Branch: `feature/p4-deterministic-engine`. Exact tested code/tests commit: `420cd3a8b83c32f3f6b6a970b49d07fb42caa1ea`. Authorized baseline: `7685110506d115805c473b064752f86e9e5c045b`.

## Actual required results

| Suite | PASS | FAIL / ERROR / SKIP / XFAIL |
|---|---:|---|
| P1 | 42/42 | 0 / 0 / 0 / 0 |
| P2 | 54/54 | 0 / 0 / 0 / 0 |
| P3 | 52/52 | 0 / 0 / 0 / 0 |
| P4 | 64/64 | 0 / 0 / 0 / 0 |

All **212 exact IDs** were executed in one combined pytest invocation, with original P3's required nested P1/P2 regressions also retained. Exact command, cwd, environment, package versions, timestamps and exit code: `command-environment.json`; complete stdout/stderr: `all-tests.stdout.txt` / `all-tests.stderr.txt`; JUnit: `all-results.xml`; per-ID duration/results: `TEST_STATUS.json`. Exit code 0. Original upstream validation files were restored byte-for-byte; new upstream-run artifacts are retained under `upstream-generated/`.

38/38 F fixtures execute real operations and compare every ordered cell/error. 19/19 X drivers exercise actual immutable-fact admission, failure UoWs, manual UI or separate-process crash/reopen. 45/45 W cases exercise actual parse/encode/decode/Unicode/overflow behavior. P0 P-A/P-B all ordered fields and exact golden CSV SHA match under the approved test-only projection. Frozen P0 NFC/JCS vectors pass. The approved ZIP SHA and 53 payload entries pass, and its actual strict verifier uses real P0 schemas/goldens and rejects 9/9 mutants. Source bytes remain unchanged. Detailed driver records: `f-fixture-results.json`, `x-fixture-results.json`, `w-fixture-results.json`, `golden-results.json`, `fixture-verifier.*`.

## Implemented components

P4-owned execution admission/service, full-row CSV/XLSX adapter reusing frozen P2 SafeZip/cached-cell guards, all 12 closed operations, stable bounded external sort/dedup, checksummed spill records, bounded provenance, sampled resource budget, exact signed64/Decimal/date/Unicode V2 wire, P1-native artifact publication and separate Run completion, read-only internal delivery checks, explicit Streamlit Execute control. P3 P4Handoff fields unchanged. Order stays EXECUTING after Run.succeeded. No QAReport, final CSV/XLSX, READY or automatic retry/recovery.

## Full-density runtime resource evidence

Fresh process reads the reproducible **40,801,000-byte 100000×200** source, raw SHA `5c5d2dbf69c0b8f4d27be5ec8a258677eb883d5ad267a4ec644b0205978aa97d`, executes parse_number→sort→deduplicate and stores **90000×200**. All **18,000,000** resulting typed cells and the canonical digest match an independent streaming modular-arithmetic reference.

- Elapsed from verified start to durable completion: **57.228578 seconds**, limit 120 seconds.
- Independent incremental peak RSS: **293650432 bytes**, limit 536870912 bytes; Linux VmRSS 5 ms sampling and ru_maxrss.
- Runtime scratch peak: **180144042 bytes**, limit 2147483648 bytes.
- Merge fan-in: **16**, limit 16.
- Result canonical SHA-256: `ea277f2873ed3bd712c7148c2b87035c42ed4cdbbec54edee2d59d63a6b5420b`.

Positive workload succeeds; injected RSS/time/scratch/row/column/parse failures additionally exercise actual guards and legal failed-run handling. Corrupted spill records reject by checksum. No controlled failure substitutes for the positive capacity result. Exact resource process output and command: `stress.*`.

## Crash/restart and atomicity

Actual child SIGKILL (-9) before start commit, after start commit, mid-pipeline, after promotion and after final success; injected Artifact EventLog insert failure; additional crash between Artifact commit and Run completion. Fresh bootstrap observes exact statuses, per-attempt events/artifacts/orphans and stale-run counts. X13: no Run/event; X14/15: running+EXECUTING, one event, degraded; X16/X18: one orphan, no Artifact metadata, running, one event; X17: succeeded, one verified Artifact, three events, ready health. Intermediate Artifact commit alone leaves running with two events and no eligible handoff. No adoption, deletion, resume or auto-terminalization. Explicit ready FAILED retry creates a new Run, retaining prior immutable IDs. Full checkpoints/public failures: `x-fixture-results.json` and `restart-*.command.json/stdout.txt/stderr.txt`.

## Scope and authorized amendments

P4-T61/T62 audit all 42 source files, exact P4 paths/hashes/surfaces, frozen legacy source/contracts, dependency/lock/migration inventory and forbidden-feature mutations. CR-P4-001 is implemented in the test boundary only; every original P3-T51 negative probe remains. Frozen P1/P2/P3 production modules and original approved packs are unchanged; app.py only appends the approved P4 panel integration.

Owner explicitly approved during implementation: **CR-P4-002** corrects T13 to four original P-B source rows (T42 remains three final rows); **CR-P4-003** updates only P2-T40/P3-T51 changed-path diff baseline to the authorized start; **CR-P4-004** corrects signed Decimal proper-fraction wire grammar (-0.25), retaining all canonical-spelling rejections. Separate versioned amendments and supplemental Decimal cases document these exact changes. Original ZIP and F/X/W source fixtures are untouched. No other contract deviation, dependency, infrastructure or operation added. DECISIONS.md and authoritative Gate decisions remain unchanged.

## Risks and limits for owner review

Linux/Python 3.12.14/openpyxl 3.1.5 only; no Windows/network-filesystem/physical-power-loss or independent-host/CI validation. RSS is sampled, not hard OS isolation; 120 seconds is a soft cooperative deadline. AppTest is automated, not manual browser sign-off. P1 requires one complete opaque byte allocation at final publication; logical datasets/stream buffers stay bounded and the allocation is budget-checked. Artifact commit and Run completion remain separate P1 UoWs, with the intervening crash explicitly rejected. Static inventory checks are regression controls, not a malicious-code sandbox.

The known 13 missing P0 P-C manifest files remain an inherited separate discrepancy; no synthetic restoration or P0 manifest rewrite. Strict P4 verifier uses the real required P0 subset. The legacy X17 descriptive string mentioning V1 is interpreted under the binding approved Q03 V2 decision; its executable format/checksum/identity assertions use V2. No P5 export/QA, unapproved statuses, new SQLite schema, network ingestion or external automation is implemented.

Changed-file inventory: `CHANGED_FILES.txt`. This report/evidence may be committed after the tested SHA; a later evidence-only commit is not a different tested runtime. Final PR must stay Draft and unmerged. **Main managing chat alone decides P4 Gate B closure.**
