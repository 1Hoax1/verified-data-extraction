
# Verified Data Extraction — P1

Local Streamlit/Python application substrate: SQLite metadata, validated P0
contract persistence, filesystem payloads and detect-only restart recovery.
P1 implementation is submitted for review. P1 is **not declared VALIDATED**;
P2 remains outside this change.

## Development

Python 3.11+ and `uv` are required. Run from this checkout:

```sh
uv sync --frozen --extra test
.venv/bin/python -m pytest tests/p1 -q
VDE_WORKSPACE=/absolute/local/workspace .venv/bin/streamlit run src/vde/app.py \
  --server.headless=true --browser.gatherUsageStats=false
```

In the cloud sandbox, set `UV_CACHE_DIR=/workspace/.cache/uv` before `uv sync`.
The checkout must remain available: editable installation reads the approved
P0 pack directly from `pecs/pilot_slice_v1/`. No P0 artifact is copied or modified.
`VDE_WORKSPACE` is the only app setting; default `.workspace` is ignored by Git.
The SQLite file is always `app.sqlite3` inside that root. Use a local filesystem
supporting WAL, hard links and file/directory `fsync`.

The shell shows `ready`, `degraded` or `blocked`. It performs no ingestion,
transformation, approval actions, execution or QA computation.
To repeat the shell checks without a browser:

```sh
.venv/bin/python scripts/smoke_shell.py
```

## Persistence API

Use `vde.bootstrap.bootstrap(Config(root))` first and inspect its health result.
Blocked storage must be corrected before normal writes. All repository writes
use one caller-owned `UnitOfWork(database, workspace)` context. Successful exit
commits once; exceptions (including caught repository failures) roll back.
Repositories do not commit themselves. Do not nest contexts on the same UoW.

`OrderRepository.update(record, expected=loaded_record)` compares the complete
prior record, including edits within the same second. Version records provide
`from_document`, append and verified load APIs; they have no update/delete API.
Approval is an immutable persistence fact, not an implemented approval workflow.
The only mutable ExecutionRun fields are status, finished_at, metrics and error.

Use `Storage.register_input` and `Storage.register_artifact` for new opaque bytes.
They derive controlled paths from identifiers and follow staging → file fsync →
atomic no-overwrite hard link → directory fsync → metadata + EventLog → one DB
commit. An existing final path always fails, even for identical bytes.
`Storage.read_input` / `read_artifact` verify checksums before returning bytes.
Raw metadata registration is internal to this protocol.

Recovery fully scans persisted contracts and file references. It retains and
reports staging leftovers, empty staging operations and orphan payloads;
it never imports them or rewrites metadata. Missing/changed bytes, corrupt
contracts and migration drift block storage. A stale `running` record is reported
without mutating its state. Inspect/reconcile recovery findings manually;
P1 provides no cleanup or resume workflow.

## Requirements and evidence

- [Approved P1 pack](docs/p1/v1.0/README.md)
- [P1 validation report](docs/p1/validation/P1_VALIDATION_REPORT.md)
- [Implementation traceability](docs/p1/validation/IMPLEMENTATION_TRACEABILITY.md)
- [Recorded test results](docs/p1/validation/p1-results.xml)

**Source-document notice:** `docs/product/Product Specification v0.1` and
`docs/implementation/MVP-0_Implementation_Scope_v1.1` each contain only a newline.
They are placeholders, not normative documents. Implementation used the actual
PDF/DOCX attached by the owner; their provenance is recorded in the report.
The approved P1 pack and `DECISIONS.md` remain unchanged.
