"""Explicit P4 commands; exact admission, P1 commits and detect-only recovery."""
from dataclasses import dataclass, replace
import hashlib
import json
import tempfile
from uuid import uuid4

from vde.errors import StorageError, utc_now
from vde.models import ExecutionRunRecord, EventRecord
from vde.persistence.uow import UnitOfWork
from vde.storage import Storage
from vde.workflow.read_model import P4Handoff
from .budget import Budget
from .commit import publish_internal_result
from .engine import apply, validate_columns
from .errors import ExecutionError, require
from .preflight import verify_and_plan
from .provenance import snapshot, summarize
from .source_adapter import iter_verified_rows
from .wire import serialize, iter_payload, REVISION


@dataclass
class ActiveRun:
    run: object
    plan: object
    source: object
    budget: object

    @property
    def id(self):
        return self.run.id


@dataclass(frozen=True)
class InternalResult:
    run_id: str
    artifact_id: str
    checksum: str
    columns: tuple
    row_count: int
    dataset_id: str


class ExecutionService:
    def __init__(self, env, *, checkpoint=None, budget_factory=Budget):
        self.env = env
        self.checkpoint = checkpoint or (lambda stage: None)
        self.budget_factory = budget_factory

    def _health(self):
        if self.env.health != 'ready':
            raise StorageError('P4 blocked by recovery health; no repair or write attempted')

    def _uow(self):
        return UnitOfWork(self.env.database, self.env.workspace)

    def _event(self, uow, run, event_type, payload):
        uow.events.append(EventRecord(str(uuid4()), run.order_id, event_type, utc_now(), run.id, payload))

    def fresh_handoff(self, order_id):
        """Reload exact existing approvals for an explicit FAILED retry as well.

        Frozen P3 p4_handoff admits only APPROVED; no P3 method is changed and
        no cached DTO is treated as permission for a retry.
        """
        self._health()
        with self._uow() as uow:
            order = uow.orders.get(order_id)
            require(order.status in {'APPROVED', 'FAILED'}, 'STATE_INVALID_TRANSITION', 'No retry of active/completed execution')
            brief = uow.briefs.get(order.selected_brief_version_id)
            spec = uow.specs.get(order.selected_transformation_spec_version_id)
            ba = uow.approvals.find_valid('BRIEF', brief.id, brief.content_hash)
            sa = uow.approvals.find_valid('TRANSFORMATION_SPEC', spec.id, spec.content_hash,
                                         brief_id=brief.id, brief_hash=brief.content_hash)
            require(ba is not None and sa is not None, 'APPROVAL_MISSING', 'Exact approvals required')
            asset = next((a for a in uow.inputs.list_for_order(order_id) if a.id == spec.document_json['inputs'][0]['asset_id']), None)
            require(asset is not None, 'INPUT_NOT_FOUND', 'InputAsset missing')
            source = spec.document_json['inputs'][0]
            handoff = P4Handoff(order_id, brief.id, brief.content_hash, ba.id, spec.id, spec.content_hash,
                                sa.id, asset.id, asset.byte_sha256,
                                {k: source[k] for k in ('source_type', 'sheet_name', 'csv_options')})
            verify_and_plan(uow, order_id, order, handoff)
            return handoff

    def start(self, order_id, expected_order, handoff):
        self._health()
        budget = self.budget_factory()
        with self._uow() as uow:
            plan = verify_and_plan(uow, order_id, expected_order, handoff)
        # All authorization facts have been checked before opening source bytes.
        source = iter_verified_rows(self.env, plan, budget)
        try:
            columns = validate_columns(source.columns, plan.pipeline)
            require(columns == tuple(plan.spec.document_json['output']['column_order']),
                    'SCHEMA_MISMATCH', 'Final column identifiers/order differ from approved Spec')
            with self._uow() as uow:
                plan = verify_and_plan(uow, order_id, expected_order, handoff)
                now = utc_now()
                run = ExecutionRunRecord(str(uuid4()), order_id, plan.brief.id, plan.brief_approval.id,
                                          plan.spec.id, plan.spec_approval.id, 'running', now, snapshot(plan), {})
                uow.orders.update(replace(plan.order, status='EXECUTING', updated_at=now), expected=plan.order)
                uow.runs.append(run)
                self._event(uow, run, 'RUN_STARTED', {'source': snapshot(plan)})
                self.checkpoint('before_run_commit')
            self.checkpoint('after_run_commit')
            return ActiveRun(run, plan, source, budget)
        except BaseException:
            source.close()
            raise

    def _fail(self, active, error):
        self._health()
        with self._uow() as uow:
            run, order = uow.runs.get(active.id), uow.orders.get(active.run.order_id)
            require(run.status == 'running' and order.status == 'EXECUTING', 'STATE_INVALID_TRANSITION', 'Failure requires owned active run')
            now = utc_now()
            public = error.public(order_id=order.id, run_id=run.id, source_id=active.plan.asset.id)
            uow.runs.update(replace(run, status='failed', finished_at=now, error_json=public))
            uow.orders.update(replace(order, status='FAILED', updated_at=now), expected=order)
            self._event(uow, run, 'RUN_FAILED', {'error': public})
            self.checkpoint('during_failure_commit')

    def finish(self, active):
        self._health()
        budget, plan = active.budget, active.plan
        try:
            with self._uow() as uow:
                stored = uow.runs.get(active.id)
                require(stored.status == 'running' and stored.order_id == plan.order.id
                        and uow.specs.get(stored.transformation_spec_version_id) == plan.spec
                        and uow.briefs.get(stored.brief_version_id) == plan.brief,
                        'VERSION_INCOMPATIBLE', 'Active execution plan differs from immutable P1 facts')
            with tempfile.TemporaryDirectory(prefix='p4-', dir=self.env.workspace.path('.staging')) as scratch:
                from pathlib import Path
                table = apply(plan, active.source, budget, scratch)
                output = Path(scratch) / 'internal-result'

                def witnessed_rows():
                    for index, row in enumerate(table.rows):
                        if index == 0:
                            self.checkpoint('mid_pipeline')
                        yield row

                with output.open('xb', buffering=1024*1024) as stream:
                    _, count = serialize(table.columns, witnessed_rows(), plan.dataset_id, budget, sink=stream)
                budget.check()
                # Frozen P1 accepts opaque bytes. Only this boundary allocates
                # the complete serialized payload, never a logical row matrix.
                budget.allocation(output.stat().st_size)
                data = output.read_bytes()
                checksum = hashlib.sha256(data).hexdigest()
                budget.check()
                artifact = publish_internal_result(self.env, active.id, str(uuid4()), data, self.checkpoint)
                del data
                budget.release(output.stat().st_size)
                output.unlink()
            active.source.close()
            self._health()
            budget.check()
            with self._uow() as uow:
                run, order = uow.runs.get(active.id), uow.orders.get(plan.order.id)
                require(run.status == 'running' and order.status == 'EXECUTING' and
                        (order.selected_brief_version_id, order.selected_transformation_spec_version_id) == (plan.brief.id, plan.spec.id),
                        'VERSION_INCOMPATIBLE', 'Completion context changed')
                artifacts = uow.artifacts.list_for_run(run.id)
                if not (len(artifacts) == 1 and artifacts[0] == artifact and artifact.checksum == checksum):
                    raise StorageError('Exactly one matching internal Artifact required')
                _, verified = self.env.workspace.inspect(artifact.workspace_relpath)
                source_size, source_hash = self.env.workspace.inspect(plan.asset.workspace_relpath)
                if not (verified == checksum and source_hash == plan.asset.byte_sha256 and source_size == plan.asset.size_bytes):
                    raise StorageError('Source/Artifact bytes changed; no failure write on corrupt storage')
                metrics = summarize(plan, table, count, checksum, budget, active.source.warnings)
                uow.runs.update(replace(run, status='succeeded', finished_at=utc_now(), metrics_json=metrics))
                self._event(uow, run, 'RUN_SUCCEEDED', {'artifact_id': artifact.id, 'checksum': checksum})
                self.checkpoint('before_success_commit')
            self.checkpoint('after_success_commit')
            return InternalResult(run.id, artifact.id, checksum, table.columns, count, plan.dataset_id)
        except ExecutionError as exc:
            self._fail(active, exc)
            raise
        except OSError as exc:
            error = ExecutionError('STORAGE_ERROR', 'P4_SCRATCH_IO')
            self._fail(active, error)
            raise error from exc
        finally:
            active.source.close()

    def execute(self, order_id, expected_order, handoff):
        return self.finish(self.start(order_id, expected_order, handoff))

    def read_result(self, run_id):
        """Read-only verified internal delivery; no P5 QA/export or state write."""
        self._health()
        with self._uow() as uow:
            run = uow.runs.get(run_id)
            order = uow.orders.get(run.order_id)
            require(run.status == 'succeeded' and order.status == 'EXECUTING', 'STATE_INVALID_TRANSITION', 'Internal result is incomplete')
            require((order.selected_brief_version_id, order.selected_transformation_spec_version_id) ==
                    (run.brief_version_id, run.transformation_spec_version_id),
                    'VERSION_INCOMPATIBLE', 'Selected result versions differ from Run')
            artifacts = uow.artifacts.list_for_run(run.id)
            require(len(artifacts) == 1, 'STORAGE_ERROR', 'Ambiguous/missing internal Artifact')
            artifact = artifacts[0]
            require(artifact.artifact_type == 'P4_INTERNAL' and artifact.format == REVISION,
                    'SCHEMA_MISMATCH', 'Wrong Artifact type/format')
            metrics = run.metrics_json
            spec = uow.specs.get(run.transformation_spec_version_id)
            require(metrics['format_revision'] == REVISION and metrics['logical_result_checksum'] == artifact.checksum
                    and metrics['dataset_id'] == spec.document_json['output']['dataset_id']
                    and metrics['columns'] == spec.document_json['output']['column_order'],
                    'SCHEMA_MISMATCH', 'Internal result metadata/context differs')
            asset = uow.inputs.get(run.input_snapshot_json['asset_id'])
            require(asset.order_id == order.id and asset.byte_sha256 == run.input_snapshot_json['source_byte_sha256'],
                    'VERSION_INCOMPATIBLE', 'Result source differs')
            source = spec.document_json['inputs'][0]
            brief = uow.briefs.get(run.brief_version_id)
            require(run.input_snapshot_json == dict(asset_id=asset.id, source_byte_sha256=asset.byte_sha256,
                        input_selection={k: source[k] for k in ('source_type', 'sheet_name', 'csv_options')},
                        brief_content_hash=brief.content_hash, transformation_content_hash=spec.content_hash)
                    and source['asset_id'] == asset.id and metrics['source'] == run.input_snapshot_json,
                    'VERSION_INCOMPATIBLE', 'Result snapshot differs from source/approvals')
            expected_columns, dataset_id = metrics['columns'], metrics['dataset_id']
        data = Storage(self.env.database, self.env.workspace).read_artifact(artifact.id)
        count = sum(1 for _ in iter_payload(data, expected_columns=expected_columns, dataset_id=dataset_id))
        require(count == metrics['row_count'], 'SCHEMA_MISMATCH', 'Internal row count differs')
        return InternalResult(run.id, artifact.id, artifact.checksum, tuple(expected_columns), count, dataset_id), data
