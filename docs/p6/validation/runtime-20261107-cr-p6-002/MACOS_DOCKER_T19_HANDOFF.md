# Actual macOS Docker P6-T19 — NOT RUN / BLOCKED

Test exact implementation `245b1ccf5d4212d3f34973e526172f20a4928539`, tree `0db696f5e14284849f969310fadf4ee585713045`.


Run this on an actual Mac with Docker Desktop, using an isolated acceptance workspace, never the operator's existing workspace. Select the exact corrected implementation commit and tree from the new validation report; the owner-authority commit `66c2b4f...` alone is not an implementation. Keep evidence outside the checkout and workspace. Do not reuse earlier Linux output as Mac proof.

1. Before launch, save the actual commands and outputs of `date -u`, `uname -s`, `uname -m`, `sw_vers`, `docker version`, `docker info --format '{{.OSType}} {{.Architecture}}'`, image RepoDigests, `git rev-parse HEAD`, `git rev-parse HEAD^{tree}`, `git status --porcelain`, and `shasum -a 256 pyproject.toml uv.lock`. The host must actually report Darwin; the container must report Linux. Record Docker Desktop version and the read-only source/read-write persistent workspace mounts (`docker inspect vde-pilot --format '{{json .Mounts}}'` while running). Retain installation/app stdout and stderr, all exit codes and frozen installed package versions.
2. Launch the exact Mac recipe above and save `curl --fail --show-error --include http://127.0.0.1:8501/_stcore/health`; require HTTP 200 and `ok`. In the Mac browser perform the documented P-A and fresh P-B workflows with actual explicit test-operator clicks and two separately reviewed Approvals per isolated Order. Only adapt fixture Order/input/version bindings in the UI draft; preserve semantics and recompute actual hashes through normal P3 publication. P-B publishes v1 then approved v2 with PB-AC-007; do not import fixture Approvals or force IDs.
3. Save the actual downloaded Result and QAReport, filenames/response metadata, `shasum -a 256` and byte sizes, Order/Brief/Spec/Approval/Run/Artifact/report identities and statuses. Independently check P-A's exact 277-byte golden. For P-B require READY/PASS_WITH_WARNINGS, 24 checks, DQ-017/PB-AC-006 and PB-AC-007 PASS, retained formula-cache warning, one XLSX, six ordered columns, three data rows/18 values and no exported formulas. Verify the actual saved QA JSON against the existing P0 schema and exact links; read-only verification through the installed container is permitted. No database or workspace edits may prepare a result.
4. Stop and remove the container, retaining the complete host workspace. Restart the exact source/image with the **same** host data mount. Require health 200, unchanged persisted IDs/rows/payload hashes and no new Approvals/Runs/Artifacts/QAReports. A fresh browser session must have no prepared download; explicitly prepare again, save both files and compare their hashes to the first downloads. Save both launch logs and the before/after observations. Preserve failed attempts as well.
5. Publish the raw Mac command log, environment, saved-file checksums, read-only state observations, test-operator action record and finite SHA-256 manifest for independent review. Only after actual execution produce the T19 input JSON: `host_system` from the host, `container_system` from the container, actual `launch_http_status`/`restart_http_status`, observed `workspace_persisted`/`explicit_ui_workflow_completed`, `commands`, `stdout`, `docker_info`, plus full tested commit/tree, image digest, evidence file paths/hashes and reviewer provenance. Those fields are a summary of real proof, not permission to fill successful values without execution.
6. On the same corrected implementation source, rerun `PYTHONPATH=src:tests P6_MAC_DOCKER_EVIDENCE=/absolute/reviewed/mac-evidence.json P6_RESULTS_DIR=/absolute/new/t19-observations .venv/bin/python -m pytest tests/p6/test_acceptance.py::test_T19_documented_linux_launch_restart_and_actual_mac_docker -q --junitxml=/absolute/new/t19-results.xml` in the Linux validation environment. Save the new command, SHA/tree, stdout/stderr, exit and JUnit separately; never overwrite the earlier NOT RUN/FAIL. The original 20-ID run and subsequent T19 rerun remain distinct evidence. A JSON claim alone is not independent Mac verification or owner Gate B authority.

If Mac hardware, Docker, the exact image/lock, real browser workflow, hashes or restart proof is unavailable, record the missing step **NOT RUN / BLOCKED**. Do not use skip/xfail, Linux-host substitution or a fabricated success receipt.


## Concrete read-only checks of the Mac-saved P-B downloads

These are instructions, **NOT RUN on a Mac here**. Run them on the actual Mac
after the manual browser workflow, while its README container is running.
Select actual saved filenames in a private evidence directory outside the
workspace. The commands only read downloaded bytes and the frozen golden; they
never approve, execute, repair or update SQLite. Keep stdout/stderr and exits.

```bash
export VDE_SAVED_XLSX=/absolute/private/evidence/orders_clean.xlsx
export VDE_SAVED_QA=/absolute/private/evidence/qa_report_actual_id.json
shasum -a 256 "$VDE_SAVED_XLSX" "$VDE_SAVED_QA"
cat "$VDE_SAVED_XLSX" | docker exec -i vde-pilot /tmp/vde-venv/bin/python -c '
import hashlib, io, sys
from openpyxl import load_workbook
raw = sys.stdin.buffer.read()
actual = load_workbook(io.BytesIO(raw), read_only=True, data_only=False, keep_links=False)
golden = load_workbook("/tmp/code/pecs/pilot_slice_v1/fixtures/P-B_xlsx_sheet/expected_result.xlsx", read_only=True, data_only=False, keep_links=False)
try:
    assert actual.sheetnames == ["Data"]
    rows = list(actual["Data"].rows)
    assert len(rows) == 4 and all(len(row) == 6 for row in rows)
    assert all(cell.data_type != "f" for row in rows for cell in row)
    assert [[cell.value for cell in row] for row in rows] == [[cell.value for cell in row] for row in golden.active.rows]
    print("18 values and six headers PASS", len(raw), hashlib.sha256(raw).hexdigest())
finally:
    actual.close()
    golden.close()
'
cat "$VDE_SAVED_QA" | docker exec -i vde-pilot /tmp/vde-venv/bin/python -c '
import json, sys
from vde.contracts import validate
report = json.load(sys.stdin)
validate(report, "qa_report")
assert report["overall_status"] == "PASS_WITH_WARNINGS" and not report["blocking_issues"]
assert report["dataset_summary"]["row_count"] == 3 and report["dataset_summary"]["column_count"] == 6
checks = report["deterministic_checks"]
assert len(checks) == 24 and not any(c["status"] == "FAIL" for c in checks)
assert {c["criterion_id"]: c["status"] for c in checks if c["check_id"] == "DQ-017"} == {"PB-AC-006": "PASS", "PB-AC-007": "PASS"}
assert report["warnings"] and len(report["artifacts"]) == 1
print(json.dumps({k: report[k] for k in ("report_id", "run_id", "brief_version_id", "transformation_spec_version_id", "dataset_summary", "artifacts", "warnings")}, ensure_ascii=False, indent=2))
'
```

Compare the XLSX SHA-256/length printed by the first command to the Artifact and
dataset summary from the QA and the UI. Match the actual Run/version/report IDs
to the two independently approved business versions and persisted context.
Retain original browser response metadata, explicit operator action record and
before/after restart proof; these readback commands alone do not complete T19.
Do not fabricate successful fields in the Mac evidence JSON. Gate B and release
still require separate owner decisions.
