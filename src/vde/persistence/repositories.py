from dataclasses import asdict, fields
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
import sqlite3

from jsonschema.exceptions import ValidationError

from ..contracts import content_hash, dumps, loads, validate
from ..errors import StorageError
from ..models import (OrderRecord, InputAssetRecord, BriefVersionRecord,
                      TransformationSpecVersionRecord, ApprovalRecord,
                      ExecutionRunRecord, ArtifactRecord, QAReportRecord, EventRecord)


def boundary(method):
    @wraps(method)
    def guarded(self, *args, **kwargs):
        try:
            self.uow.ensure_active()
            return method(self, *args, **kwargs)
        except (sqlite3.Error, OSError, ValidationError, ValueError, TypeError, KeyError, InvalidOperation, StorageError) as exc:
            self.uow.rollback_only = True
            if isinstance(exc, StorageError):
                raise
            raise StorageError("Persistence constraint or document validation failed") from exc
    return guarded


def verify_values(record):
    for field in fields(record):
        value = getattr(record, field.name)
        if value is not None and field.name in {"created_at", "updated_at", "approved_at", "started_at", "finished_at", "generated_at", "deadline"}:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo != timezone.utc or parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != value:
                raise StorageError("Timestamp must use UTC Z at second precision")
    if isinstance(record, OrderRecord) and record.budget is not None:
        if not isinstance(record.budget, str):
            raise StorageError("Budget must be normalized decimal text")
        number = Decimal(record.budget)
        normalized = format(number, "f").rstrip("0").rstrip(".") if "." in format(number, "f") else format(number, "f")
        if not number.is_finite() or record.budget != ("0" if number == 0 else normalized):
            raise StorageError("Budget must be normalized decimal text")


class Repository:
    table = ""
    model = None
    pk = "id"

    def __init__(self, uow):
        self.uow = uow

    def _insert(self, record):
        verify_values(record)
        values = asdict(record)
        for key in values:
            if key.endswith("_json") and values[key] is not None:
                values[key] = dumps(values[key])
        names = list(values)
        self.uow.connection.execute(
            f"INSERT INTO {self.table} ({','.join(names)}) VALUES ({','.join('?' for _ in names)})", tuple(values.values()))
        return record

    def _decode(self, row):
        if row is None:
            raise StorageError("Stored record not found")
        values = dict(row)
        for key in values:
            if key.endswith("_json") and values[key] is not None:
                values[key] = loads(values[key])
        record = self.model(**values)
        verify_values(record)
        return record

    @boundary
    def get(self, identity):
        return self._decode(self.uow.connection.execute(f"SELECT * FROM {self.table} WHERE {self.pk}=?", (identity,)).fetchone())

    def _list(self, column, identity, order):
        return [self._decode(row) for row in self.uow.connection.execute(f"SELECT * FROM {self.table} WHERE {column}=? ORDER BY {order}", (identity,))]


class OrderRepository(Repository):
    table, model = "orders", OrderRecord

    def _references(self, record):
        for identity, repo in [(record.selected_brief_version_id, self.uow.briefs), (record.selected_transformation_spec_version_id, self.uow.specs)]:
            if identity is not None and repo.get(identity).order_id != record.id:
                raise StorageError("Selected version belongs to another order")

    @boundary
    def add(self, record):
        self._references(record)
        return self._insert(record)

    @boundary
    def list(self):
        return [self._decode(row) for row in self.uow.connection.execute("SELECT * FROM orders ORDER BY created_at,id")]

    @boundary
    def update(self, record, *, expected):
        old = self.get(record.id)
        # Full-record CAS also detects two reruns within the same UTC second.
        if old != expected:
            raise StorageError("Stale Order compare-and-set")
        if old.created_at != record.created_at:
            raise StorageError("Order creation time is immutable")
        self._references(record)
        verify_values(record)
        values = asdict(record)
        del values["id"]
        cursor = self.uow.connection.execute(
            f"UPDATE orders SET {','.join(key+'=?' for key in values)} WHERE id=? AND status=? AND updated_at=?",
            (*values.values(), record.id, expected.status, expected.updated_at))
        if cursor.rowcount != 1:
            raise StorageError("Stale Order compare-and-set")
        return record


class FileRepository(Repository):
    @boundary
    def _append_promoted(self, record):
        checksum = record.byte_sha256 if isinstance(record, InputAssetRecord) else record.checksum
        size, actual = self.uow.workspace.inspect(record.workspace_relpath)
        if checksum != actual or (isinstance(record, InputAssetRecord) and size != record.size_bytes):
            raise StorageError("Promoted payload metadata mismatch")
        return self._insert(record)

    def _decode(self, row):
        record = super()._decode(row)
        self.uow.workspace.path(record.workspace_relpath)
        return record


class InputAssetRepository(FileRepository):
    table, model = "input_assets", InputAssetRecord

    @boundary
    def list_for_order(self, identity):
        return self._list("order_id", identity, "created_at,id")


class VersionRepository(Repository):
    kind = ""

    def _verify(self, record):
        document = record.document_json
        validate(document, self.kind)
        for field in fields(record):
            if field.name == "document_json":
                continue
            key = "version_id" if field.name == "id" else field.name
            if getattr(record, field.name) != document[key]:
                raise StorageError("Authoritative version JSON/index mismatch")
        if content_hash(document, self.kind) != record.content_hash:
            raise StorageError("Authoritative version content-hash mismatch")
        if self.kind == "transformation_spec_version":
            brief = self.uow.briefs.get(record.brief_version_id)
            if (brief.order_id, brief.content_hash) != (record.order_id, record.brief_content_hash):
                raise StorageError("TransformationSpec exact Brief mismatch")

    def _decode(self, row):
        record = super()._decode(row)
        self._verify(record)
        return record

    @boundary
    def append(self, record):
        self._verify(record)
        return self._insert(record)

    @boundary
    def list_for_order(self, identity):
        return self._list("order_id", identity, "version_number")

    @boundary
    def latest_version_number(self, identity):
        return self.uow.connection.execute(f"SELECT COALESCE(MAX(version_number),0) FROM {self.table} WHERE order_id=?", (identity,)).fetchone()[0]


class BriefVersionRepository(VersionRepository):
    table, model, kind = "brief_versions", BriefVersionRecord, "brief_version"


class TransformationSpecVersionRepository(VersionRepository):
    table, model, kind = "transformation_spec_versions", TransformationSpecVersionRecord, "transformation_spec_version"


class ApprovalRepository(Repository):
    table, model = "approvals", ApprovalRecord

    def _verify(self, record):
        validate({"schema_version": "1.1", **asdict(record)}, "approval")
        repo = self.uow.briefs if record.target_type == "BRIEF" else self.uow.specs
        target = repo.get(record.target_version_id)
        if (target.order_id, target.content_hash) != (record.order_id, record.target_content_hash):
            raise StorageError("Approval exact target mismatch")
        if record.target_type == "TRANSFORMATION_SPEC" and (target.brief_version_id, target.brief_content_hash) != (record.context_brief_version_id, record.context_brief_content_hash):
            raise StorageError("Approval exact Brief context mismatch")

    def _decode(self, row):
        record = super()._decode(row)
        self._verify(record)
        return record

    @boundary
    def append(self, record):
        self._verify(record)
        return self._insert(record)

    @boundary
    def find_valid(self, target_type, version_id, recalculated_hash, *, brief_id=None, brief_hash=None):
        repo = self.uow.briefs if target_type == "BRIEF" else self.uow.specs
        version = repo.get(version_id)  # always repeats schema/index/hash checks
        if version.content_hash != recalculated_hash:
            return None
        for record in self.list_for_order(version.order_id):
            if (record.target_type, record.target_version_id, record.target_content_hash, record.context_brief_version_id, record.context_brief_content_hash) == (target_type, version_id, recalculated_hash, brief_id, brief_hash):
                return record
        return None

    @boundary
    def list_for_order(self, identity):
        return self._list("order_id", identity, "approved_at,id")


class ExecutionRunRepository(Repository):
    table, model = "execution_runs", ExecutionRunRecord

    def _verify(self, record):
        brief = self.uow.briefs.get(record.brief_version_id)
        spec = self.uow.specs.get(record.transformation_spec_version_id)
        ba = self.uow.approvals.get(record.brief_approval_id)
        sa = self.uow.approvals.get(record.transformation_approval_id)
        if not (brief.order_id == spec.order_id == record.order_id and (spec.brief_version_id, spec.brief_content_hash) == (brief.id, brief.content_hash)):
            raise StorageError("Run exact version references mismatch")
        if (ba.order_id, ba.target_type, ba.target_version_id, ba.target_content_hash) != (record.order_id, "BRIEF", brief.id, brief.content_hash):
            raise StorageError("Run Brief Approval mismatch")
        if (sa.order_id, sa.target_type, sa.target_version_id, sa.target_content_hash, sa.context_brief_version_id, sa.context_brief_content_hash) != (record.order_id, "TRANSFORMATION_SPEC", spec.id, spec.content_hash, brief.id, brief.content_hash):
            raise StorageError("Run Transformation Approval mismatch")
        if record.error_json is not None:
            validate(record.error_json, "execution_error")

    def _decode(self, row):
        record = super()._decode(row)
        self._verify(record)
        return record

    @boundary
    def append(self, record):
        self._verify(record)
        return self._insert(record)

    @boundary
    def list_for_order(self, identity):
        return self._list("order_id", identity, "started_at,id")

    @boundary
    def update(self, record):
        old = self.get(record.id)
        mutable = {"status", "finished_at", "metrics_json", "error_json"}
        if any(getattr(old, field.name) != getattr(record, field.name) for field in fields(record) if field.name not in mutable):
            raise StorageError("Run identity/reference fields are immutable")
        self._verify(record)
        verify_values(record)
        self.uow.connection.execute("UPDATE execution_runs SET status=?,finished_at=?,metrics_json=?,error_json=? WHERE id=?", (record.status, record.finished_at, dumps(record.metrics_json), dumps(record.error_json) if record.error_json is not None else None, record.id))
        return record


class ArtifactRepository(FileRepository):
    table, model = "artifacts", ArtifactRecord

    @boundary
    def list_for_run(self, identity):
        return self._list("run_id", identity, "created_at,id")


class QAReportRepository(Repository):
    table, model, pk = "qa_reports", QAReportRecord, "report_id"

    def _verify(self, record):
        validate(record.report_json, "qa_report")
        for field in fields(record):
            if field.name != "report_json" and getattr(record, field.name) != record.report_json[field.name]:
                raise StorageError("QAReport JSON/index mismatch")
        run = self.uow.runs.get(record.run_id)
        if (run.brief_version_id, run.transformation_spec_version_id) != (record.brief_version_id, record.transformation_spec_version_id):
            raise StorageError("QAReport exact run/version mismatch")

    def _decode(self, row):
        record = super()._decode(row)
        self._verify(record)
        return record

    @boundary
    def append(self, record):
        self._verify(record)
        return self._insert(record)

    @boundary
    def list_for_run(self, identity):
        return self._list("run_id", identity, "generated_at,report_id")


class EventLogRepository(Repository):
    table, model = "event_log", EventRecord

    def _verify(self, record):
        self.uow.orders.get(record.order_id)
        if record.run_id is not None and self.uow.runs.get(record.run_id).order_id != record.order_id:
            raise StorageError("Event run/order mismatch")

    def _decode(self, row):
        record = super()._decode(row)
        self._verify(record)
        return record

    @boundary
    def append(self, record):
        self._verify(record)
        return self._insert(record)

    @boundary
    def list_for_order(self, identity):
        return self._list("order_id", identity, "created_at,id")

    @boundary
    def list_for_run(self, identity):
        return self._list("run_id", identity, "created_at,id")
