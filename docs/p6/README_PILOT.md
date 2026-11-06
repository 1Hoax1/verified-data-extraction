# Pilot Slice V1 — local operator manual

This manual covers the approved P6 workflow in [Design Pack v0.2](design/P6_DESIGN_PACK_v0.2.md), under [CR-P6-001](decisions/CR-P6-001_OWNER_DECISION_2026-11-06.md). Gate A is owner-closed in the [later direction decision](decisions/P6_DIRECTION_OWNER_DECISION_2026-11-06.md). Implementation validation, Gate B closure, merge and Pilot release are separate decisions. These instructions alone do not certify a release; use the [release checklist](RELEASE_CHECKLIST.md).

**Known integration blocker:** a newly published P-B Brief receives a UUID from the frozen P3 UI, while the frozen P5 PB-AC-002 exception recognizes only the literal ID `brief-pb-v1`. The legally identity-adapted six-column P-B path consequently produces `NEEDS_FIX / FAIL`, not its required `READY / PASS_WITH_WARNINGS`. Preserve that diagnostic result; do not force IDs, change criteria, or deliver it as accepted output. The proposed CR-P6-002 in new validation evidence requests a narrowly reviewed P5 correction. It is not approved or implemented; the existing P5 code remains unchanged.

The supported runtime is Linux, including Linux in Docker Desktop on an Apple Silicon or Intel Mac. Native macOS execution is unsupported: frozen P2 reads Linux `/proc` for resource checks. Use one person, one Streamlit process and one local persistent workspace. The workspace contains confidential input/result bytes and SQLite records; restrict its directory to the operator. SQLite is authoritative for metadata, exact versions, Approvals, Runs and QAReports; controlled workspace files are authoritative for payload bytes. Keep both together on a filesystem supporting SQLite WAL, hard links and file/directory `fsync`.

## Linux installation and launch

Use a writable checkout of the exact package commit selected for validation/release. The owner-start commit is `b93e0ef4ed69343968ff7ae4188d586c0d1485a5`; it contains the approved design, not an implemented release. Record the actual implementation commit, tree and package SHA-256 in the release checklist before distributing a package. Retain `pecs/pilot_slice_v1/` alongside `src/`: the editable installation reads that frozen contract pack from the checkout.

The reproducible toolchain below selects `uv==0.12.19` and Python `3.12.14`. Start in the selected checkout with Python 3 and its `venv` support available. Replace the two absolute paths with private local directories outside the checkout:

```bash
set -eu
export VDE_TOOLS=/absolute/local/vde-tools-uv-0.12.19
export VDE_WORKSPACE=/absolute/local/vde-pilot-workspace
umask 077
python3 -m venv "$VDE_TOOLS"
"$VDE_TOOLS/bin/python" -m pip install 'uv==0.12.19'
"$VDE_TOOLS/bin/uv" python install 3.12.14
"$VDE_TOOLS/bin/uv" sync --frozen --python 3.12.14 --extra test
.venv/bin/python -c 'import sys; assert sys.version_info[:3] == (3, 12, 14); print(sys.version)'
"$VDE_TOOLS/bin/uv" --version
"$VDE_TOOLS/bin/uv" pip freeze --python .venv/bin/python
mkdir -p "$VDE_WORKSPACE"
chmod 700 "$VDE_WORKSPACE"
.venv/bin/python -m streamlit run src/vde/app.py \
  --server.address=127.0.0.1 --server.port=8501 \
  --server.headless=true --browser.gatherUsageStats=false
```

Open `http://127.0.0.1:8501`. Initial bootstrap creates `app.sqlite3` and controlled directories inside `VDE_WORKSPACE`; a fresh workspace should show `Storage: ready` and no Orders. Reuse this exact absolute workspace path on every restart. Stop with Ctrl-C and wait for the process to exit before copying or changing the workspace.

`uv sync --frozen` consumes the unchanged `uv.lock`; do not run `uv lock`, upgrade dependencies or edit the lock to make installation succeed. Frozen direct runtime packages are `jsonschema==4.26.0`, `referencing==0.37.0`, `rfc8785==0.1.4`, `streamlit==1.50.0` and `openpyxl==3.1.5`; the test extra is `pytest==8.4.2`. Transitive versions and platform markers come from `uv.lock`. The uv bootstrap tool is separate from application dependencies. Installation needs access to the configured package and Python distribution sources; ingestion and business processing use local files.

## Mac: local Linux container

Install and start Docker Desktop, then open a terminal in the selected checkout. This command supports Docker's native Linux architecture on either Mac CPU family. It mounts the repository read-only at `/source` and the same private host workspace read/write at `/data`. An ephemeral `/tmp/code` copy and `/tmp/vde-venv` let setuptools create editable build metadata without writing to the repository mount. No Dockerfile or repository build script is required.

```bash
set -eu
export VDE_REPO="$(pwd -P)"
export VDE_DATA=/absolute/local/vde-pilot-workspace
umask 077
mkdir -p "$VDE_DATA"
chmod 700 "$VDE_DATA"
docker run --rm --init --name vde-pilot \
  --user "$(id -u):$(id -g)" \
  --publish 127.0.0.1:8501:8501 \
  --mount "type=bind,source=$VDE_REPO,target=/source,readonly" \
  --mount "type=bind,source=$VDE_DATA,target=/data" \
  --env VDE_WORKSPACE=/data \
  --env UV_CACHE_DIR=/tmp/uv-cache \
  --env UV_PROJECT_ENVIRONMENT=/tmp/vde-venv \
  --env UV_PYTHON_DOWNLOADS=never \
  --workdir /tmp \
  python:3.12.14-slim-bookworm sh -eu -c '
    python -c "import sys; assert sys.version_info[:3] == (3, 12, 14)"
    python -m venv /tmp/vde-tools
    /tmp/vde-tools/bin/python -m pip install "uv==0.12.19"
    python -c "import shutil; shutil.copytree(\"/source\", \"/tmp/code\", ignore=shutil.ignore_patterns(\".git\", \".venv\", \".workspace\", \"__pycache__\", \"*.egg-info\"))"
    cd /tmp/code
    /tmp/vde-tools/bin/uv sync --frozen --python /usr/local/bin/python3.12 --extra test
    /tmp/vde-tools/bin/uv --version
    /tmp/vde-tools/bin/uv pip freeze --python /tmp/vde-venv/bin/python
    exec /tmp/vde-venv/bin/python -m streamlit run src/vde/app.py \
      --server.address=0.0.0.0 --server.port=8501 \
      --server.headless=true --browser.gatherUsageStats=false
  '
```

Open `http://127.0.0.1:8501` on the Mac. The `0.0.0.0` address is inside the container; the published host port remains loopback-only. Stop with Ctrl-C, or `docker stop vde-pilot` from another terminal, and wait for exit and automatic removal. Before reusing the name, `docker inspect vde-pilot` must report that no such container exists; removal can finish shortly after `docker stop` returns. Repeat the same command, source checkout and `VDE_DATA` to restart. `/tmp/code`, installed tools, the virtual environment and browser preparation state are disposable; `/data/app.sqlite3` and `/data/orders/` remain on the host. Do not start a second process on that directory. Record the pulled image digest (`docker image inspect python:3.12.14-slim-bookworm --format '{{json .RepoDigests}}'`), Docker/Desktop version, host CPU/OS and actual smoke outcomes in release evidence. A versioned image tag alone is not a recorded image digest or proof of a Mac test.

This is a local Docker Desktop recipe, with no managed-cloud credentials or proxy material. A site requiring an HTTPS proxy or private CA must configure Docker/package tooling with its approved local trust settings; do not disable TLS verification. Failure to pull the exact image or install the frozen lock leaves the container smoke check pending/failed until resolved without changing dependencies. Actual Mac-host execution is required for the Mac portion of P6-T19; Linux-host Docker evidence cannot replace it.

## Explicit operator workflow

1. Confirm fresh storage health is `ready`. In **Create Order**, enter a nonblank title and listing text and explicitly submit the form. Submission creates a DRAFT only. Listing text is retained verbatim; a listing URL is stored as text and is never fetched. Leave unused optional fields empty. A supplied budget must already be finite canonical Decimal text; a deadline must be exact UTC `YYYY-MM-DDTHH:MM:SSZ`. Failed submissions retain the form token; resubmitting identical fields with that token reuses the Order. An explicit new Order uses a new token. Browser loss before successful submission does not provide global content deduplication.
2. In the original input panel, select that **Existing Order**, choose one **Local CSV or XLSX**, and click **Upload**. Select the **Registered input**. For CSV choose encoding, delimiter and header row; for XLSX explicitly select one **Worksheet**. Click **Preview** and review warnings. Preview is not a QA verdict.
3. Open **Open manual workflow**, select the same **P3 existing Order** and **P3 registered input**, and set the corresponding CSV options or worksheet. Click **Verify P3 input and preview**, inspect the selected asset ID/checksum/options, then **Begin manual review**. Draft JSON lives only in the browser session until published.
4. Enter the human-reviewed contract in **Brief JSON draft**. It must refer to this actual input/context and conform to the existing P0 schema. Use **Validate Brief draft**, then **Save new Brief version**. Inspect the published document, version ID, canonical content hash and diff. Only the person authorized to approve the business Brief checks **Confirm this exact Brief ID and hash** and clicks **I approve this Brief version**.
5. Enter the human-reviewed **TransformationSpec JSON draft**, linked to that exact approved Brief ID/hash and selected input. It must define only existing operations, acceptance criteria and the approved output filename/format. Validate and **Save new TransformationSpec version**. Review its published ID/hash, source selection and Brief link separately. The authorized person checks **Confirm this exact Spec ID, hash and approved Brief context** and clicks **I approve TransformationSpec**. Both immutable Approvals are required. Neither creating an Order, validating JSON, saving a version, nor this manual grants an Approval. Supplied fixture/TEST_ONLY Approvals and automated test-user actions never authorize a real business Order.
6. Open **Open deterministic transformation**, choose the same **P4 existing Order**, inspect source checksum, input selection, pipeline and original limits, confirm the selection and click **Execute**. Wait for the succeeded Run and note its ID. Rendering or restarting does not execute it.
7. Open **Open export and QA**, select the same **P5 existing Order** and succeeded Run, then click **Export + deterministic QA**. This is a separate explicit action. Review QA status, blockers, warnings and dataset summary; do not reinterpret deterministic FAIL as success.
8. In the P6 delivery panel select the intended Order and exact Run. Review the version IDs/hashes, recorded Approval provenance, final artifact format/checksum/size and QA status. Click **Prepare verified download**. After preparation, save the offered result/diagnostic and QA JSON to a private local folder. Compare an independently computed SHA-256 of the saved result with the displayed Artifact/report checksum (`sha256sum /path/to/saved/result.csv` on Linux; `shasum -a 256 /path/to/saved/result.xlsx` on Mac). Retain the matching QAReport with that result. Do not publish an internal path or `P4_INTERNAL` payload.

Use the actual selected IDs in every panel; each original panel has its own selector. The existing P3 JSON editor remains the way to create/review contracts. No ordinary workflow step requires SQLite editing, fixture rewriting, Python calls or workspace file editing. The frozen panels contain historical captions, including the old P3 “P4 execution unavailable” caption; the separate deterministic transformation panel provides the explicit P4 operation.

## Interpreting a prepared download

| Persisted state and verified health | Available output |
|---|---|
| `READY` + `PASS` | Approved-format verified CSV/XLSX and matching QAReport. |
| `READY` + `PASS_WITH_WARNINGS` with zero blockers | The same outputs, with warnings retained for review. |
| `NEEDS_FIX` + QA `FAIL` | Associated diagnostic result with `_DIAGNOSTIC_NOT_FOR_DELIVERY` before the extension, conspicuous **NOT FOR DELIVERY** labeling, and QAReport. Do not send the diagnostic as an accepted delivery. |
| Other/inconsistent status, missing approval/report/artifact, or `degraded`/`blocked` | No prepared download; inspect the safe diagnostic and stop the business action. |

Viewing, preparing and transferring P6 downloads are read-only: they create no Artifact, Event, Approval, Run or QAReport and do not rerun QA. QA JSON is deterministic UTF-8 serialization of the existing validated report, linked to the exact Run, versions and final Artifact. CSV uses `text/csv`; XLSX uses `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`; QA uses `application/json; charset=utf-8`. Only the approved safe output basename/extension is used.

Preparation rereads current ownership/context/health and verifies actual result bytes against both persisted Artifact and QA summary length/hash before retaining an immutable bytes snapshot. Streamlit's download button transfers that prepared copy. It does not reread disk at the last HTTP/browser click. A prepared copy can remain a valid checksum-verified copy even if disk bytes subsequently change; a new prepare must reject corruption. Selection changes, failed subsequent context/health checks, errors, restart or browser session loss invalidate preparation. Prepare again after restart; never treat session state as business authority.

P6 admits downloads within **536870912 bytes (512 MiB) incremental sampled process RSS above preparation baseline**. Its preflight allocation estimate is at least `3 × result_file_size + serialized_QA_bytes + 64 MiB`; it includes the payload, retained snapshot and Streamlit-buffer allowance, and actual RSS is checked during preparation/rebinding. At most one selected run's result and one QA buffer are retained. This is sampled Linux RSS and conservative admission, not OS isolation, a peak-memory guarantee or proof that every nominal maximum export fits. `P6_DOWNLOAD_RESOURCE_LIMIT` exposes no new payload and changes no business/QA state. If an ordinary approved Pilot workload cannot be downloaded, record the actual characteristics and seek a new owner CR; do not reduce the workload silently or declare T17 passed from refusal alone. P5's 100000×200 export success is not P6 browser-download evidence.

For release maintainers, the pinned Streamlit 1.50.0 implementation registers media before sending a download widget. P6 buffers the session's widget messages through `ScriptRunContext._enqueue` until both button bindings pass their RSS check; failure restores prior media coordinates and removes only newly allocated entries using the media manager's private lock/metadata/deletion interfaces. A dedicated internal `.vde-qa-json` MIME lookup extension preserves `application/json; charset=utf-8` on actual HTTP responses while the saved QA filename remains `.json`. These compatibility points require actual HTTP success and failure-injection tests against the frozen version. Do not upgrade Streamlit or infer compatibility from widget inspection alone.

External marketplace messages, client file transfer and billing remain deliberate human actions outside this application. Review the exact saved result and QA before any external delivery. P6 never sends files or messages automatically.

## Stopped-app checkpoint and backup

Stop Streamlit/container and confirm no second process is using the workspace. Keep the complete directory, including SQLite sidecars and payloads, together. Never copy only `app.sqlite3` while the app runs. On Linux, use the installed environment to checkpoint the existing DB before a complete copy:

```bash
set -eu
export VDE_WORKSPACE=/absolute/local/vde-pilot-workspace
export VDE_BACKUP=/absolute/local/vde-pilot-backup-YYYYMMDDTHHMMSSZ
.venv/bin/python - <<'PY'
import os
import sqlite3
from pathlib import Path
database = Path(os.environ['VDE_WORKSPACE']) / 'app.sqlite3'
connection = sqlite3.connect(database.resolve().as_uri() + '?mode=rw', uri=True)
try:
    outcome = connection.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
    print('checkpoint:', outcome)
    assert outcome[0] == 0, 'Checkpoint busy: stop every workspace user before backup'
finally:
    connection.close()
PY
test ! -e "$VDE_BACKUP"
cp -a "$VDE_WORKSPACE" "$VDE_BACKUP"
```

For Mac, after `docker stop` and exit, checkpoint the same host directory through Linux, then copy on the host:

```bash
set -eu
docker run --rm --user "$(id -u):$(id -g)" \
  --mount "type=bind,source=$VDE_DATA,target=/data" \
  python:3.12.14-slim-bookworm python -c \
  'import sqlite3; c=sqlite3.connect("file:/data/app.sqlite3?mode=rw",uri=True); r=c.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone(); c.close(); print(r); assert r[0] == 0'
export VDE_BACKUP=/absolute/local/vde-pilot-backup-YYYYMMDDTHHMMSSZ
test ! -e "$VDE_BACKUP"
cp -a "$VDE_DATA" "$VDE_BACKUP"
```

Record the package commit/hash and a finite SHA-256 manifest for the backup; verify a restore on a separate disposable directory before relying on it. A backup is a stopped-app filesystem snapshot, not an automatically resumed execution.

## Restart, recovery and rollback

Restart using the same complete workspace and exact selected package. Persisted versions, independent Approvals, Runs, reports and files are reread and verified; unsaved JSON drafts and prepared download buffers must be recreated. No operation is automatically approved, executed, exported, resumed or repaired.

On `degraded` or `blocked`, stop create/execute/export/download actions. Retain the displayed staging/orphan/stale-run/errors and application logs. Stop the app, preserve a complete copy for diagnosis and inspect a disposable copy only. Never update a checksum to match altered bytes, delete orphan/staging files to hide health findings, rewrite an Approval/report, replace missing P-C fixtures, or mark a stale run succeeded. Recovery is detect-only; any reconciliation needs an explicit owner-approved procedure.

For rollback, stop all workspace users and preserve the failing directory unchanged. Select an owner-approved compatible package by its recorded commit/hash. Restore a verified complete stopped-app backup to a new directory, point `VDE_WORKSPACE` (or host `VDE_DATA`) there, and restart that package. Recheck health and the exact persisted context before new manual actions; prepare new downloads. Do not overwrite the only failing workspace or mix a DB from one checkpoint with files from another. No storage migration or automatic repair is introduced by P6.

## Validation limitations

The 13 absent original P-C files remain absent; only available negative guards can run. Original P1–P5 scope tests, including P5-T76, may genuinely fail on the extended P6 inventory; retain their raw failures and classify exact approved scope assertions separately. All behavioral regressions block Gate B. The twenty P6 acceptance IDs in `tests/p6/test_acceptance.py` need runtime evidence on the actual implementation SHA/tree, including independent saved-download readback, corruption/restart probes and actual memory sampling. This manual makes no runtime-PASS claim. Clean Linux and actual Mac Docker smoke results remain pending until their commands and observations are recorded in the release evidence.
