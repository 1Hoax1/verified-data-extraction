"""Executable P4 acceptance oracles; no fixture rewrites or skipped scenarios."""
import hashlib

from vde.execution.service import ExecutionService
from vde.execution.wire import iter_payload
from .support import Approved


def test_T01_approved_csv_vertical(tmp_path):
    a = Approved(tmp_path)
    service = ExecutionService(a.env)
    active = service.start(a.order_id, a.order(), a.handoff)
    assert active.run.status == 'running'
    assert a.order().status == 'EXECUTING' and a.order().approval_stage == 'COMPLETE'
    assert a.counts() == a.before | {'execution_runs': 1, 'event_log': a.before['event_log']+1}
    result = service.finish(active)
    assert result.row_count == 3
    handle, payload = service.read_result(result.run_id)
    rows = list(iter_payload(payload, expected_columns=handle.columns, dataset_id='result'))
    assert [r[0] for r in rows] == ['Алиса Смит', 'Bob Jones', 'Carla Ruiz']
    assert handle.checksum == hashlib.sha256(payload).hexdigest()
    assert a.env.workspace.read_verified(a.asset.workspace_relpath, a.asset.byte_sha256) == a.raw
    with a.uow() as uow:
        run = uow.runs.get(result.run_id)
        assert run.status == 'succeeded' and len(run.metrics_json['operation_audit']) == 14
        assert uow.orders.get(a.order_id).status == 'EXECUTING'
