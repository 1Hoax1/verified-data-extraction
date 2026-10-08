# P1 Validation Report — implementation review evidence

Run: 2026-10-08T17:59:11+03:00 (Europe/Moscow). Implementation tested: `b88b0da`.
Status: **submitted for review; P1 is not declared VALIDATED**.
`DECISIONS.md` remains `APPROVED_TO_START`. P2 has not started.

## Normative inputs and source-document notice

The approved `DECISIONS.md`, `docs/p1/v1.0/` and `pecs/pilot_slice_v1/`
were read directly and remain byte-for-byte unchanged from base `c9924a0`.
Both source-document paths in the repository are one-byte newline placeholders:

- `docs/product/Product Specification v0.1`
- `docs/implementation/MVP-0_Implementation_Scope_v1.1`

Those placeholders were not used as normative documents and were not replaced.
The owner supplied the actual documents in this task:

| Attachment | Bytes | SHA-256 |
|---|---:|---|
| Product Specification v0.1.pdf | 190742 | `49421af31a1cf2dd838c89372898040c9a4307bd64dcd84114e1ff47a3cbb72c` |
| MVP-0_Implementation_Scope_v1.1.docx | 86600 | `8abb80b3734b9d438b5d24af0d8278d3e27cf5f1b9c39b4547992621dbceccd1` |

PDF text and DOCX document XML were extracted for requirement review. Attached
content was treated as source requirements, not as commands or authorization.
The approved pack's stated precedence resolves older product-model differences:
the Scope v1.1 / P0 model supplies immutable Approval facts and exact version
references; the P1 pack fixes partial indexes for nullable Brief context, limits
P1 to opaque storage and excludes later-stage parsing/workflows. D1–D8 are
retained. No unresolved requirement contradiction or Change Request was found.
The attachments themselves are not distributed in the Git checkout.

## Runtime and commands

Linux, overlayfs; Python 3.12.14; SQLite 3.53.1; Streamlit 1.50.0.
A new checkout-local virtual environment was installed from the frozen `uv.lock`:

```sh
UV_CACHE_DIR=/workspace/.cache/uv uv sync --frozen --extra test
.venv/bin/python -m pytest tests/p1 -q --junitxml=docs/p1/validation/p1-results.xml
.venv/bin/python scripts/smoke_shell.py
```

Final required suite: **42 PASS, 0 FAIL, 0 errors, 0 skipped, 0 xfail**;
runner elapsed time 9.611 seconds. All 42 IDs were collected,
executed and recorded in [p1-results.xml](p1-results.xml). Variants are assertions
within their corresponding test, not separately counted test IDs.

## Actual required results

| ID | Approved check | Actual result |
|---|---|---|
| P1-T01 | Clean bootstrap | PASS |
| P1-T02 | Idempotent bootstrap | PASS |
| P1-T03 | Migration checksum drift | PASS |
| P1-T04 | Failed migration rollback | PASS |
| P1-T05 | Foreign-key enforcement | PASS |
| P1-T06 | Exact 10 Order states / 3 approval stages | PASS |
| P1-T07 | Order round-trip across restart | PASS |
| P1-T08 | InputAsset byte round-trip | PASS |
| P1-T09 | Workspace path traversal | PASS |
| P1-T10 | Workspace relocation | PASS |
| P1-T11 | BriefVersion append-only repository | PASS |
| P1-T12 | TransformationSpec exact Brief link | PASS |
| P1-T13 | P0 hash vector persistence | PASS |
| P1-T14 | No approval fields in versions | PASS |
| P1-T15 | BRIEF Approval duplicate | PASS |
| P1-T16 | Transformation Approval duplicate/context | PASS |
| P1-T17 | Approval immutability | PASS |
| P1-T18 | Approval validity after changed/corrupt content | PASS |
| P1-T19 | EventLog immutability/order | PASS |
| P1-T20 | File-write crash before promotion | PASS |
| P1-T21 | File-write crash after promotion/before DB UoW commit | PASS |
| P1-T22 | DB-referenced file missing | PASS |
| P1-T23 | DB-referenced checksum mismatch | PASS |
| P1-T24 | Atomic final-path collision | PASS |
| P1-T25 | ExecutionRun round-trip | PASS |
| P1-T26 | Artifact round-trip | PASS |
| P1-T27 | QAReport round-trip | PASS |
| P1-T28 | Stale running run | PASS |
| P1-T29 | DB integrity failure | PASS |
| P1-T30 | P1 scope audit | PASS |
| P1-T31 | BRIEF Approval exact target DB guard | PASS |
| P1-T32 | Transformation Approval exact target/context DB guard | PASS |
| P1-T33 | ExecutionRun exact references DB guard | PASS |
| P1-T34 | QAReport exact run/version relation | PASS |
| P1-T35 | EventLog run/order integrity | PASS |
| P1-T36 | Selected version same-order integrity | PASS |
| P1-T37 | Brief authoritative JSON write validation | PASS |
| P1-T38 | Transformation authoritative JSON write validation | PASS |
| P1-T39 | Version trust-boundary/recovery validation | PASS |
| P1-T40 | QAReport JSON/index validation | PASS |
| P1-T41 | File metadata + EventLog single-commit atomicity | PASS |
| P1-T42 | Public storage-error contract compliance | PASS |

## Additional evidence

- Migration `001_p1_baseline` checksum:
  `186d6415d59f3fa48d8f1d350b3746689bb46f6e129394a4811c8cc717e53d76`.
  Baseline, idempotence, drift rejection and transactional failed-upgrade
  rollback passed. Connection checks confirmed FK=ON, WAL, synchronous=FULL
  and busy_timeout=5000; integrity_check returned `ok`.
- All 20 read-only P0 schemas are meta-validated by the contract loader;
  stored Brief/Transformation/Approval/QA/Error instances are validated against
  those exact schemas. Both NFC + RFC 8785 + SHA-256 vectors were persisted and
  loaded in a separate Python process with exact expected digests.
- The P-C changed-content case invalidated the old Approval even with a valid
  new content hash; the wrong-target-hash case was rejected against an existing target. Indexed
  identity, authoritative JSON/hash and exact polymorphic references were
  checked at write, verified load and recovery boundaries.
- Raw SQL tests exercised constraints and insertion/update/delete guards;
  a caught repository failure also prevented partial UoW commit. Order CAS
  rejected a stale edit even when timestamps and status were unchanged.
- Real subprocess abrupt exits occurred before promotion and after promotion,
  metadata insert and EventLog insert. Reopen found staging/orphans and no
  invented or partially committed DB metadata. EventLog/metadata insertion
  failures rolled back both. SQL trace proved promotion before BEGIN,
  metadata and EventLog before one COMMIT. Missing hard-link support failed
  without overwrite or fallback.
- All nine entity types were persisted and reloaded; Order, InputAsset, both
  versions, ExecutionRun, Artifact and QAReport were loaded in child processes.
  Approval/EventLog were reverified across connection-close/bootstrap cycles.
  Payload checks verified unchanged bytes and checksums; moving the entire
  closed workspace preserved relative references.
- Streamlit AppTest passed ready, rerun, degraded and blocked rendering.
  A real headless server on local port 8501 returned HTTP 200 / `ok` from
  `/_stcore/health` and HTTP 200 with the Streamlit shell from `/`.
  The server started for validation was stopped afterward.
- Scope audit found exactly ten P1/internal tables, no dataset-row tables and
  no app modules importing ingestion, transformations, external network clients,
  ORM, QA computation, LLM, Telegram, workers or API services. Streamlit's
  transitive packages do not introduce application workflows.
- `git diff --check` passed. P0 contracts/registries/fixtures, the approved
  P1 design pack, original placeholders and `DECISIONS.md` were unchanged.

## Known limitations and review boundary

1. Durability is exercised on this Linux overlayfs using file and directory
   fsync plus atomic same-filesystem hard links. Unsupported primitives fail
   writes. Tests prove process-crash/reopen behavior, not physical power loss,
   remote/network filesystem safety or the storage hardware's flush guarantees.
   Windows and other filesystems were not validated.
2. The application is a single local user/process. Path validation rejects
   symlinks and traversal; concurrent hostile filesystem mutation is not an
   adversarial security boundary. This is not a multi-user/authenticated service.
3. Recovery is a full, fail-fast integrity scan: its first blocker is reported;
   no repair/adoption/delete/resume workflow is implemented. Staging, empty
   staging directories, orphan files and stale runs are retained for inspection.
4. Registration accepts opaque byte buffers; datasets are never parsed. Large
   payload streaming, ingestion, transformations, QA computation and approval
   actions are later-stage work. Persisting supplied fixtures is not executing
   those workflows.
5. Only the P1 baseline exists. Failed future-upgrade rollback is fault-injected;
   no down-migration or released prior application schema exists to test.
6. Local editable installation depends on the checkout's unchanged P0 pack.
   Standalone wheel distribution and restoration in a separate cloud task were
   not validated. This report does not claim environment publication.
7. Passing implementation tests does not close the approved release gate.
   Review and explicit owner closure are required; P1 is not marked VALIDATED.
