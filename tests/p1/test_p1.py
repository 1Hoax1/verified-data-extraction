"""One collected test per approved P1 ID; variants execute inside each test."""
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest

from vde.bootstrap import bootstrap
from vde.config import Config
from vde.contracts import PACK, content_hash, dumps, hash_payload, loads, validate, validators
from vde.errors import StorageError, utc_now
from vde.models import (OrderRecord, BriefVersionRecord, TransformationSpecVersionRecord,
                        ApprovalRecord, ExecutionRunRecord, QAReportRecord, EventRecord)
from vde.persistence.database import Migration, connect, migrate, packaged_migrations
from vde.persistence.uow import UnitOfWork
from vde.storage import Storage
from vde.workspace import Workspace

NOW = "2026-10-08T12:00:00Z"
FIX = PACK / "fixtures/P-A_dirty_csv"
BASE = PACK.parents[1]


def document(filename, folder=FIX):
    return loads((folder / filename).read_text(encoding="utf-8"))


def uow(env):
    return UnitOfWork(env.database, env.workspace)


def order(identity="order-pa"):
    return OrderRecord(identity, "Test order", "Local listing", NOW, NOW, budget="12.5", deadline=NOW, notes="Примечание", listing_url="https://example.org/listing")


def seed(env, *, runs=True):
    brief = BriefVersionRecord.from_document(document("brief_version.json"))
    spec = TransformationSpecVersionRecord.from_document(document("transformation_spec_version.json"))
    ba = ApprovalRecord.from_document(document("approvals/brief_approval.json"))
    sa = ApprovalRecord.from_document(document("approvals/transformation_approval.json"))
    report = QAReportRecord.from_document(document("expected_qa_report.json"))
    run = ExecutionRunRecord(report.run_id, brief.order_id, brief.id, ba.id, spec.id, sa.id, "succeeded", NOW, {"asset_id": "asset-pa-csv"}, {"rows": 3}, NOW)
    with uow(env) as u:
        u.orders.add(order())
        u.briefs.append(brief)
        u.specs.append(spec)
        u.approvals.append(ba)
        u.approvals.append(sa)
        if runs:
            u.runs.append(run)
    return brief, spec, ba, sa, run, report


def raw_insert(connection, table, record):
    values = asdict(record) if not isinstance(record, dict) else record
    values = {key: dumps(value) if key.endswith("_json") and value is not None else value for key, value in values.items()}
    connection.execute(f"INSERT INTO {table} ({','.join(values)}) VALUES ({','.join('?' for _ in values)})", tuple(values.values()))


def reject_raw(env, table, records):
    connection = connect(env.database)
    try:
        before = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for record in records:
            connection.execute("BEGIN IMMEDIATE")
            with pytest.raises(sqlite3.IntegrityError):
                raw_insert(connection, table, record)
            connection.rollback()
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == before
    finally:
        connection.close()


def public(error):
    doc = error.public()
    validate(doc, "execution_error")
    assert doc["code"] == "STORAGE_ERROR" and doc["category"] == "STORAGE"
    return doc


def restart(env):
    return bootstrap(Config(env.workspace.root))


def child_record(env, repository, identity):
    script = """
from dataclasses import asdict
import json, sys
from pathlib import Path
from vde.bootstrap import bootstrap
from vde.config import Config
from vde.persistence.uow import UnitOfWork
b=bootstrap(Config(Path(sys.argv[1])))
assert b.health in ('ready','degraded'), b.recovery.errors
with UnitOfWork(b.database,b.workspace) as u:
    record=getattr(u,sys.argv[2]).get(sys.argv[3])
    print(json.dumps(asdict(record)))
"""
    result = subprocess.run([sys.executable, "-c", script, str(env.workspace.root), repository, identity], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def register_input(env, **kwargs):
    return Storage(env.database, env.workspace).register_input(id="asset-test", order_id="order-pa", original_filename="../../untrusted.csv", data=b"opaque\x00payload", **kwargs)


def test_T01_clean_bootstrap(env):
    connection = connect(env.database)
    try:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert connection.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        migration = connection.execute("SELECT * FROM schema_migrations").fetchone()
        assert (migration["version"], migration["checksum"]) == (1, packaged_migrations()[0].checksum)
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        connection.close()
    assert all((env.workspace.root / name).is_dir() for name in ["orders", ".staging", "recovery/quarantine"])


def test_T02_idempotent_bootstrap(env):
    seed(env)
    connection = connect(env.database)
    before = list(connection.iterdump())
    connection.close()
    assert restart(env).health == "ready"
    connection = connect(env.database)
    assert list(connection.iterdump()) == before
    connection.close()


def test_T03_migration_checksum_drift(env):
    connection = connect(env.database)
    connection.execute("UPDATE schema_migrations SET checksum=?", ("0" * 64,))
    connection.close()
    result = restart(env)
    assert result.health == "blocked"
    validate(result.recovery.errors[0], "execution_error")
    connection = connect(env.database)
    assert connection.execute("SELECT checksum FROM schema_migrations").fetchone()[0] == "0" * 64
    connection.close()


def test_T04_failed_migration_rollback(env):
    connection = connect(env.database)
    definitions = (*packaged_migrations(), Migration(2, "002_failure", "CREATE TABLE should_rollback(id TEXT); INSERT INTO nonexistent VALUES (1);\n"))
    with pytest.raises(StorageError) as error:
        migrate(connection, definitions)
    public(error.value)
    assert connection.execute("SELECT 1 FROM sqlite_master WHERE name='should_rollback'").fetchone() is None
    assert connection.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 1
    connection.close()
    assert restart(env).health == "ready"


def test_T05_foreign_key_enforcement(env):
    with pytest.raises(StorageError) as error:
        with uow(env) as u:
            u.orders.add(order())
            u.events.append(EventRecord("event-bad", "missing-order", "TEST", NOW))
    public(error.value)
    with uow(env) as u:
        assert u.orders.list() == []
    reject_raw(env, "event_log", [EventRecord("event-raw", "missing-order", "TEST", NOW)])
    # Catching an error inside a UoW must still prevent a partial commit.
    with pytest.raises(StorageError):
        with uow(env) as u:
            u.orders.add(order())
            with pytest.raises(StorageError):
                u.events.append(EventRecord("event-caught", "missing-order", "TEST", NOW))
    with uow(env) as u:
        assert u.orders.list() == []


def test_T06_exact_states_and_approval_stages(env):
    states = document("order_statuses.json", PACK / "registries")["values"]
    stages = document("approval_stages.json", PACK / "registries")["values"]
    assert len(states) == 10 and len(stages) == 3
    with uow(env) as u:
        for index, state in enumerate(states):
            u.orders.add(replace(order(f"order-{index}"), status=state))
        for index, stage in enumerate(stages):
            u.orders.add(replace(order(f"stage-{index}"), approval_stage=stage))
    reject_raw(env, "orders", [replace(order("bad-state"), status="UNKNOWN"), replace(order("bad-stage"), approval_stage="UNKNOWN")])


def test_T07_order_restart(env):
    with uow(env) as u:
        u.orders.add(order())
    assert child_record(env, "orders", "order-pa") == asdict(order())
    with pytest.raises(StorageError):
        with uow(env) as u:
            u.orders.update(replace(order(), title="Changed"), expected=replace(order(), status="FAILED"))
    with uow(env) as u:
        updated = replace(order(), title="Changed")
        u.orders.update(updated, expected=order())
    assert child_record(env, "orders", "order-pa") == asdict(updated)
    with pytest.raises(StorageError):
        with uow(env) as u:
            u.orders.update(replace(order(), title="Stale same-second edit"), expected=order())


def test_T08_input_byte_roundtrip(env):
    seed(env)
    asset = register_input(env)
    assert child_record(env, "inputs", asset.id) == asdict(asset)
    assert env.workspace.path(asset.workspace_relpath).read_bytes() == b"opaque\x00payload"
    assert asset.size_bytes == len(b"opaque\x00payload")
    assert asset.byte_sha256 == hashlib.sha256(b"opaque\x00payload").hexdigest()
    assert Storage(env.database, env.workspace).read_input(asset.id) == b"opaque\x00payload"


def test_T09_path_traversal(env, tmp_path):
    for path in ["/tmp/outside", "../outside", "orders/../../outside", "C:/payload", "C:payload", "orders/a\x00b", "orders\\outside", "orders/./file", "orders//file"]:
        with pytest.raises(StorageError) as error:
            env.workspace.path(path)
        public(error.value)
    (env.workspace.root / "orders/link").symlink_to(tmp_path)
    with pytest.raises(StorageError) as error:
        env.workspace.path("orders/link/outside")
    public(error.value)
    invalid_root = bootstrap(Config(Path("invalid\x00root")))
    assert invalid_root.health == "blocked"
    validate(invalid_root.recovery.errors[0], "execution_error")


def test_T10_workspace_relocation(env, tmp_path):
    seed(env)
    asset = register_input(env)
    destination = tmp_path / "relocated"
    shutil.move(str(env.workspace.root), destination)
    moved = bootstrap(Config(destination))
    assert moved.health == "ready"
    with uow(moved) as u:
        loaded = u.inputs.get(asset.id)
    assert loaded == asset
    assert moved.workspace.path(loaded.workspace_relpath).read_bytes() == b"opaque\x00payload"


def test_T11_brief_append_only(env):
    brief, *_ = seed(env)
    doc = deepcopy(brief.document_json)
    doc.update(version_id="brief-pa-v2", version_number=2, objective="Changed requirement")
    doc["content_hash"] = content_hash(doc, "brief_version")
    with uow(env) as u:
        assert not hasattr(u.briefs, "update") and not hasattr(u.briefs, "delete")
        u.briefs.append(BriefVersionRecord.from_document(doc))
        assert u.briefs.get(brief.id) == brief
        assert [v.version_number for v in u.briefs.list_for_order("order-pa")] == [1, 2]
        assert u.briefs.latest_version_number("order-pa") == 2


def test_T12_spec_exact_brief_link(env):
    _, spec, *_ = seed(env)
    for change in [{"brief_version_id": "missing-brief"}, {"brief_content_hash": "f" * 64}, {"order_id": "order-other"}]:
        doc = deepcopy(spec.document_json)
        doc.update(change, version_id="spec-bad", version_number=2)
        doc["content_hash"] = content_hash(doc, "transformation_spec_version")
        with pytest.raises(StorageError):
            with uow(env) as u:
                u.specs.append(TransformationSpecVersionRecord.from_document(doc))


def test_T13_p0_hash_vectors_persistence(env):
    folder = PACK / "specifications/hash_vectors"
    vectors = document("vectors_manifest.json", folder)["vectors"]
    records = []
    for index, vector in enumerate(vectors):
        payload = document(vector["input"], folder)
        assert hash_payload(payload) == vector["expected_sha256"]
        doc = {**payload, "order_id": "order-pc", "version_id": "brief-pc-v1" if index == 0 else "transform-pc-v1", "version_number": 1, "created_at": NOW, "content_hash": vector["expected_sha256"]}
        if index == 0:
            doc["source_refs"] = ["asset-pc-csv"]
        records.append((BriefVersionRecord if index == 0 else TransformationSpecVersionRecord).from_document(doc))
    with uow(env) as u:
        u.orders.add(order("order-pc"))
        u.briefs.append(records[0])
        u.specs.append(records[1])
    for repo, record, kind in [("briefs", records[0], "brief_version"), ("specs", records[1], "transformation_spec_version")]:
        loaded = child_record(env, repo, record.id)
        assert content_hash(loaded["document_json"], kind) == record.content_hash


def test_T14_no_approval_fields_on_versions(env):
    connection = connect(env.database)
    for table, model in [("brief_versions", BriefVersionRecord), ("transformation_spec_versions", TransformationSpecVersionRecord)]:
        columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        assert not {"is_approved", "approved_at"} & columns
        assert not {"is_approved", "approved_at"} & model.__dataclass_fields__.keys()
    connection.close()


def test_T15_brief_duplicate_approval(env):
    _, _, approval, *_ = seed(env)
    with pytest.raises(StorageError):
        with uow(env) as u:
            u.approvals.append(replace(approval, id="approval-duplicate"))
    reject_raw(env, "approvals", [replace(approval, id="approval-duplicate")])


def test_T16_spec_duplicate_and_context(env):
    _, _, _, approval, *_ = seed(env)
    for changed in [replace(approval, id="approval-duplicate"), replace(approval, id="approval-no-context", context_brief_version_id=None, context_brief_content_hash=None)]:
        with pytest.raises(StorageError):
            with uow(env) as u:
                u.approvals.append(changed)
        reject_raw(env, "approvals", [changed])


def test_T17_approval_immutability(env):
    seed(env)
    with uow(env) as u:
        assert not hasattr(u.approvals, "update") and not hasattr(u.approvals, "delete")
    connection = connect(env.database)
    for statement in ["UPDATE approvals SET approved_by='local_user'", "DELETE FROM approvals"]:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(statement)
    assert connection.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 2
    connection.close()


def test_T18_approval_after_corrupt_content(env):
    brief, _, approval, *_ = seed(env)
    with uow(env) as u:
        assert u.approvals.find_valid("BRIEF", brief.id, brief.content_hash) == approval
        assert u.approvals.find_valid("BRIEF", brief.id, "f" * 64) is None
    mutated = deepcopy(brief.document_json)
    mutated["objective"] = "Never approved"
    connection = connect(env.database)
    connection.execute("UPDATE brief_versions SET document_json=? WHERE id=?", (dumps(mutated), brief.id))
    connection.close()
    with pytest.raises(StorageError) as error:
        with uow(env) as u:
            u.approvals.find_valid("BRIEF", brief.id, brief.content_hash)
    public(error.value)
    assert restart(env).health == "blocked"
    # Exercise P-C against existing targets, so missing parents cannot make a
    # negative test pass accidentally. Its changed Brief carries a valid NEW
    # hash, but the old immutable Approval still targets the original hash.
    pc = PACK / "fixtures/P-C_approval_safety/invalid_examples"
    vectors = PACK / "specifications/hash_vectors"
    pc_brief_doc = document("brief_vector_01.input.json", vectors)
    pc_brief_doc.update(version_id="brief-pc-v1", order_id="order-pc", version_number=1, created_at="2026-07-12T11:00:00Z", source_refs=["asset-pc-csv"])
    pc_brief_doc["content_hash"] = content_hash(pc_brief_doc, "brief_version")
    pc_brief = BriefVersionRecord.from_document(pc_brief_doc)
    pc_spec_doc = document("transformation_vector_01.input.json", vectors)
    pc_spec_doc.update(version_id="transform-pc-v1", order_id="order-pc", version_number=1, created_at=NOW)
    pc_spec_doc["content_hash"] = content_hash(pc_spec_doc, "transformation_spec_version")
    with uow(env) as u:
        u.orders.add(order("order-pc"))
        u.briefs.append(pc_brief)
        u.specs.append(TransformationSpecVersionRecord.from_document(pc_spec_doc))
        u.approvals.append(ApprovalRecord("approval-pc-original", "order-pc", "BRIEF", pc_brief.id, pc_brief.content_hash, None, None, "local_user", NOW))
    with pytest.raises(StorageError, match="Approval exact target mismatch"):
        with uow(env) as u:
            u.approvals.append(ApprovalRecord.from_document(document("approval_target_hash_wrong.json", pc)))
    changed_pc = document("brief_mutated_after_approval.json", pc)
    assert content_hash(changed_pc, "brief_version") == changed_pc["content_hash"]
    connection = connect(env.database)
    connection.execute("PRAGMA foreign_keys=OFF")
    connection.execute("UPDATE brief_versions SET document_json=?,content_hash=? WHERE id=?", (dumps(changed_pc), changed_pc["content_hash"], pc_brief.id))
    connection.close()
    with pytest.raises(StorageError, match="Approval exact target mismatch") as error:
        with uow(env) as u:
            u.approvals.find_valid("BRIEF", pc_brief.id, changed_pc["content_hash"])
    public(error.value)


def test_T19_event_immutability_and_order(env):
    seed(env)
    events = [EventRecord("event-later", "order-pa", "TEST", "2026-10-08T12:00:01Z"), EventRecord("event-first", "order-pa", "TEST", NOW)]
    with uow(env) as u:
        for event in events:
            u.events.append(event)
        assert u.events.list_for_order("order-pa") == events[::-1]
        assert not hasattr(u.events, "update") and not hasattr(u.events, "delete")
    connection = connect(env.database)
    for sql in ["UPDATE event_log SET event_type='TEST'", "DELETE FROM event_log"]:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(sql)
    connection.close()


def crash_registration(env, stage):
    script = """
import os, sys
from pathlib import Path
from vde.workspace import Workspace
from vde.storage import Storage
w=Workspace(Path(sys.argv[1]))
def checkpoint(stage):
    if stage==sys.argv[2]: os._exit(77)
Storage(w.path('app.sqlite3'),w,checkpoint).register_input(id='asset-crash-'+sys.argv[2],order_id='order-pa',original_filename='opaque',data=b'crash')
"""
    result = subprocess.run([sys.executable, "-c", script, str(env.workspace.root), stage], capture_output=True)
    assert result.returncode == 77, result.stderr


def test_T20_crash_before_promotion(env):
    seed(env)
    crash_registration(env, "staged")
    result = restart(env)
    assert result.health == "degraded" and len(result.recovery.staging) == 1 and not result.recovery.orphans
    with uow(env) as u:
        assert u.inputs.list_for_order("order-pa") == []
        assert u.events.list_for_order("order-pa") == []
    (env.workspace.root / ".staging/empty-operation").mkdir()
    assert len(restart(env).recovery.staging) == 2


def test_T21_crash_after_promotion(env):
    seed(env)
    for index, phase in enumerate(["promoted", "metadata", "event"], start=1):
        crash_registration(env, phase)
        result = restart(env)
        assert result.health == "degraded" and len(result.recovery.orphans) == index and not result.recovery.staging
        with uow(env) as u:
            assert u.inputs.list_for_order("order-pa") == []
            assert u.events.list_for_order("order-pa") == []


def test_T22_referenced_file_missing(env):
    seed(env)
    asset = register_input(env)
    env.workspace.path(asset.workspace_relpath).unlink()
    result = restart(env)
    assert result.health == "blocked"
    validate(result.recovery.errors[0], "execution_error")
    with uow(env) as u:
        assert u.inputs.get(asset.id) == asset
    with pytest.raises(StorageError):
        Storage(env.database, env.workspace).read_input(asset.id)


def test_T23_checksum_mismatch(env):
    seed(env)
    asset = register_input(env)
    env.workspace.path(asset.workspace_relpath).write_bytes(b"altered")
    result = restart(env)
    assert result.health == "blocked"
    validate(result.recovery.errors[0], "execution_error")
    with uow(env) as u:
        assert u.inputs.get(asset.id).byte_sha256 == asset.byte_sha256
    with pytest.raises(StorageError):
        Storage(env.database, env.workspace).read_input(asset.id)


def test_T24_atomic_collision(env, monkeypatch):
    seed(env)
    asset = register_input(env)
    for data in [b"opaque\x00payload", b"different"]:
        with pytest.raises(StorageError) as error:
            Storage(env.database, env.workspace).register_input(id=asset.id, order_id="order-pa", original_filename="other", data=data)
        public(error.value)
        assert env.workspace.path(asset.workspace_relpath).read_bytes() == b"opaque\x00payload"
    with uow(env) as u:
        assert len(u.inputs.list_for_order("order-pa")) == 1
        assert len(u.events.list_for_order("order-pa")) == 1
    def unsupported_link(*args, **kwargs):
        raise OSError("Atomic hard-link primitive unavailable")
    monkeypatch.setattr(os, "link", unsupported_link)
    with pytest.raises(StorageError):
        Storage(env.database, env.workspace).register_input(id="asset-unsupported", order_id="order-pa", original_filename="opaque", data=b"unsupported")
    assert not env.workspace.path("orders/order-pa/input/asset-unsupported/payload").exists()
    with uow(env) as u:
        assert len(u.inputs.list_for_order("order-pa")) == 1


def test_T25_execution_run_restart(env):
    *_, run, _ = seed(env)
    assert child_record(env, "runs", run.id) == asdict(run)
    changed = replace(run, status="failed", metrics_json={"elapsed": 1}, error_json=StorageError("Test persisted failure").public())
    with uow(env) as u:
        u.runs.update(changed)
    assert child_record(env, "runs", run.id) == asdict(changed)
    connection = connect(env.database)
    for field, value in [("brief_approval_id", "other-approval"), ("started_at", "2026-10-08T12:00:01Z"), ("input_snapshot_json", "{}")]:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(f"UPDATE execution_runs SET {field}=? WHERE id=?", (value, run.id))
    connection.close()


def test_T26_artifact_restart(env):
    *_, run, _ = seed(env)
    storage = Storage(env.database, env.workspace)
    artifact = storage.register_artifact(id="artifact-one", run_id=run.id, artifact_type="SNAPSHOT", format="BIN", data=b"artifact-one")
    assert child_record(env, "artifacts", artifact.id) == asdict(artifact)
    storage.register_artifact(id="artifact-two", run_id=run.id, artifact_type="SNAPSHOT", format="BIN", data=b"artifact-two")
    assert env.workspace.path(artifact.workspace_relpath).read_bytes() == b"artifact-one"
    assert storage.read_artifact(artifact.id) == b"artifact-one"
    with uow(env) as u:
        assert len(u.artifacts.list_for_run(run.id)) == 2
    with pytest.raises(StorageError):
        storage.register_artifact(id="artifact-one", run_id=run.id, artifact_type="SNAPSHOT", format="BIN", data=b"changed")


def test_T27_qa_report_restart(env):
    *_, report = seed(env)
    with uow(env) as u:
        u.reports.append(report)
    assert child_record(env, "reports", report.report_id) == asdict(report)
    with uow(env) as u:
        assert u.reports.list_for_run(report.run_id) == [report]


def test_T28_stale_running_detect_only(env):
    *_, run, _ = seed(env)
    running = replace(run, status="running", finished_at=None)
    with uow(env) as u:
        u.runs.update(running)
    result = restart(env)
    assert result.health == "degraded" and result.recovery.stale_runs == [run.id]
    assert child_record(env, "runs", run.id) == asdict(running)


def test_T29_database_integrity_failure(env):
    # All connections are closed before tampering with a real on-disk DB.
    with env.database.open("r+b") as stream:
        stream.write(b"corrupt SQLite header")
    before = env.database.read_bytes()
    result = restart(env)
    assert result.health == "blocked"
    validate(result.recovery.errors[0], "execution_error")
    assert env.database.read_bytes() == before


def test_T30_p1_scope_audit(env):
    import ast
    modules = set()
    forbidden = {"sqlalchemy", "httpx", "requests", "urllib3", "openai", "telegram", "fastapi", "celery", "rq", "pandas", "openpyxl", "csv"}
    for path in (BASE / "src/vde").rglob("*.py"):
        modules.add(path.stem)
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not {alias.name.split('.')[0] for alias in node.names} & forbidden
            if isinstance(node, ast.ImportFrom):
                assert (node.module or '').split('.')[0] not in forbidden
    assert not modules & {"ingestion", "engine", "executor", "qa_engine", "llm", "worker", "approval_workflow"}
    connection = connect(env.database)
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {"schema_migrations", "orders", "input_assets", "brief_versions", "transformation_spec_versions", "approvals", "execution_runs", "artifacts", "qa_reports", "event_log"}
    connection.close()


def test_T31_brief_approval_raw_guard(env):
    _, _, approval, *_ = seed(env)
    with uow(env) as u:
        u.orders.add(order("order-other"))
    reject_raw(env, "approvals", [replace(approval, id="bad-a", target_version_id="nonexistent"), replace(approval, id="bad-b", order_id="order-other"), replace(approval, id="bad-c", target_content_hash="f" * 64)])


def test_T32_spec_approval_raw_guard(env):
    brief, _, _, approval, *_ = seed(env)
    second = deepcopy(brief.document_json)
    second.update(version_id="brief-second", version_number=2)
    with uow(env) as u:
        u.orders.add(order("order-other"))
        u.briefs.append(BriefVersionRecord.from_document(second))
    reject_raw(env, "approvals", [replace(approval, id="bad-a", target_content_hash="f" * 64), replace(approval, id="bad-b", order_id="order-other"), replace(approval, id="bad-c", context_brief_version_id="missing-brief"), replace(approval, id="bad-d", context_brief_content_hash="f" * 64), replace(approval, id="bad-e", context_brief_version_id="brief-second")])


def test_T33_execution_exact_raw_guard(env):
    brief, spec, ba, sa, run, _ = seed(env)
    doc = deepcopy(brief.document_json)
    doc.update(version_id="brief-second", version_number=2)
    second = BriefVersionRecord.from_document(doc)
    with uow(env) as u:
        u.orders.add(order("order-other"))
        u.briefs.append(second)
        u.approvals.append(replace(ba, id="approval-second", target_version_id=second.id))
    reject_raw(env, "execution_runs", [replace(run, id="bad-a", brief_approval_id=sa.id), replace(run, id="bad-b", transformation_approval_id=ba.id), replace(run, id="bad-c", order_id="order-other"), replace(run, id="bad-d", brief_approval_id="approval-second"), replace(run, id="bad-e", brief_version_id=second.id, brief_approval_id="approval-second")])
    # Simulate offline stale-hash corruption. Run guard checks indexed hashes;
    # repository/recovery separately recompute authoritative JSON hashes.
    connection = connect(env.database)
    connection.execute("PRAGMA foreign_keys=OFF")
    connection.execute("UPDATE transformation_spec_versions SET content_hash=? WHERE id=?", ("f" * 64, spec.id))
    connection.close()
    reject_raw(env, "execution_runs", [replace(run, id="bad-stale")])


def test_T34_qa_exact_run_versions(env):
    brief, _, _, _, _, report = seed(env)
    doc = deepcopy(brief.document_json)
    doc.update(version_id="brief-second", version_number=2)
    with uow(env) as u:
        u.briefs.append(BriefVersionRecord.from_document(doc))
    changed = deepcopy(report.report_json)
    changed["brief_version_id"] = "brief-second"
    record = QAReportRecord.from_document(changed)
    with pytest.raises(StorageError):
        with uow(env) as u:
            u.reports.append(record)
    reject_raw(env, "qa_reports", [record])


def test_T35_event_run_order(env):
    *_, run, _ = seed(env)
    with uow(env) as u:
        u.orders.add(order("order-other"))
    record = EventRecord("event-wrong", "order-other", "TEST", NOW, run.id)
    with pytest.raises(StorageError):
        with uow(env) as u:
            u.events.append(record)
    reject_raw(env, "event_log", [record])


def test_T36_selected_same_order(env):
    brief, spec, *_ = seed(env)
    with uow(env) as u:
        u.orders.add(order("order-other"))
        u.orders.update(replace(order(), selected_brief_version_id=brief.id, selected_transformation_spec_version_id=spec.id), expected=order())
    for field, values in [("selected_brief_version_id", [brief.id, "missing-brief"]), ("selected_transformation_spec_version_id", [spec.id, "missing-spec"])]:
        for value in values:
            with pytest.raises(StorageError):
                with uow(env) as u:
                    u.orders.update(replace(order("order-other"), **{field: value}), expected=order("order-other"))
            connection = connect(env.database)
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(f"UPDATE orders SET {field}=? WHERE id='order-other'", (value,))
            connection.close()


def test_T37_brief_authoritative_write(env):
    brief, *_ = seed(env)
    invalid = deepcopy(brief.document_json)
    invalid["is_approved"] = True
    for record in [replace(brief, document_json=invalid), replace(brief, id="mismatching-index"), replace(brief, content_hash="f" * 64)]:
        with pytest.raises(StorageError) as error:
            with uow(env) as u:
                u.briefs.append(record)
        public(error.value)


def test_T38_spec_authoritative_write(env):
    _, spec, *_ = seed(env)
    invalid = deepcopy(spec.document_json)
    invalid["is_approved"] = True
    bad_hash = deepcopy(spec.document_json)
    bad_hash["content_hash"] = "f" * 64
    wrong_brief = deepcopy(spec.document_json)
    wrong_brief.update(brief_content_hash="f" * 64)
    wrong_brief["content_hash"] = content_hash(wrong_brief, "transformation_spec_version")
    for record in [replace(spec, document_json=invalid), replace(spec, id="mismatch-index"), TransformationSpecVersionRecord.from_document(bad_hash), TransformationSpecVersionRecord.from_document(wrong_brief)]:
        with pytest.raises(StorageError) as error:
            with uow(env) as u:
                u.specs.append(record)
        public(error.value)


def test_T39_version_corruption_recovery(env):
    brief, spec, *_ = seed(env)
    for table, record, repo in [("brief_versions", brief, "briefs"), ("transformation_spec_versions", spec, "specs")]:
        mutations = [("document_json", "{}"), ("document_json", dumps({**record.document_json, "version_number": 99})), ("document_json", dumps({**record.document_json, "content_hash": "f" * 64}))]
        for field, value in mutations:
            connection = connect(env.database)
            connection.execute(f"UPDATE {table} SET {field}=? WHERE id=?", (value, record.id))
            connection.close()
            with pytest.raises(StorageError):
                with uow(env) as u:
                    getattr(u, repo).get(record.id)
            assert restart(env).health == "blocked"
            connection = connect(env.database)
            assert connection.execute(f"SELECT document_json FROM {table} WHERE id=?", (record.id,)).fetchone()[0] == value
            connection.execute(f"UPDATE {table} SET document_json=? WHERE id=?", (dumps(record.document_json), record.id))
            connection.close()


def test_T40_qa_json_index_validation(env):
    *_, report = seed(env)
    invalid = deepcopy(report.report_json)
    invalid["extra"] = True
    for record in [replace(report, report_json=invalid), replace(report, report_id="bad-index"), replace(report, overall_status="FAIL")]:
        with pytest.raises(StorageError):
            with uow(env) as u:
                u.reports.append(record)
    with uow(env) as u:
        u.reports.append(report)
    connection = connect(env.database)
    connection.execute("UPDATE qa_reports SET overall_status='FAIL'")
    connection.close()
    assert restart(env).health == "blocked"
    connection = connect(env.database)
    assert connection.execute("SELECT overall_status FROM qa_reports").fetchone()[0] == "FAIL"
    connection.close()


def test_T41_file_and_audit_single_commit(env, monkeypatch):
    seed(env)
    for target in ["metadata", "event"]:
        table = "input_assets" if target == "metadata" else "event_log"
        connection = connect(env.database)
        connection.execute(f"CREATE TRIGGER injected_failure BEFORE INSERT ON {table} BEGIN SELECT RAISE(ABORT,'Injected DB failure'); END")
        connection.close()
        with pytest.raises(StorageError):
            Storage(env.database, env.workspace).register_input(id=f"asset-{target}", order_id="order-pa", original_filename="opaque", data=b"fault")
        connection = connect(env.database)
        assert connection.execute("SELECT COUNT(*) FROM input_assets").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM event_log").fetchone()[0] == 0
        connection.execute("DROP TRIGGER injected_failure")
        connection.close()
    assert len(restart(env).recovery.orphans) == 2
    from vde.persistence import uow as uow_module
    trace = []
    original_connect = uow_module.connect
    def traced_connect(path):
        connection = original_connect(path)
        connection.set_trace_callback(trace.append)
        return connection
    monkeypatch.setattr(uow_module, "connect", traced_connect)
    storage = Storage(env.database, env.workspace, lambda stage: trace.append("PHASE " + stage))
    asset = storage.register_input(id="asset-test", order_id="order-pa", original_filename="opaque", data=b"opaque\x00payload")
    assert trace.index("PHASE promoted") < trace.index("BEGIN IMMEDIATE")
    metadata_index = next(i for i, value in enumerate(trace) if value.startswith("INSERT INTO input_assets"))
    event_index = next(i for i, value in enumerate(trace) if value.startswith("INSERT INTO event_log"))
    assert metadata_index < event_index < trace.index("COMMIT")
    assert trace.count("COMMIT") == 1
    with uow(env) as u:
        assert u.inputs.list_for_order("order-pa") == [asset]
        assert len(u.events.list_for_order("order-pa")) == 1


def test_T42_public_error_contract(env):
    seed(env)
    errors = []
    with pytest.raises(StorageError) as error:
        env.workspace.path("../outside")
    errors.append(error.value)
    asset = register_input(env)
    with pytest.raises(StorageError) as error:
        register_input(env)
    errors.append(error.value)
    with pytest.raises(StorageError) as error:
        with uow(env) as u:
            u.events.append(EventRecord("event-bad", "missing-order", "TEST", NOW))
    errors.append(error.value)
    env.workspace.path(asset.workspace_relpath).unlink()
    recovery = restart(env)
    codes = document("error_codes.json", PACK / "registries")["values"]
    for doc in [*(public(error) for error in errors), *recovery.recovery.errors]:
        validate(doc, "execution_error")
        assert doc["code"] in codes and doc["code"] == "STORAGE_ERROR"
        assert doc["category"] == "STORAGE" and "storage_reason" not in doc
        assert set(doc) == set(validators()["execution_error.schema.json"].schema["required"])
