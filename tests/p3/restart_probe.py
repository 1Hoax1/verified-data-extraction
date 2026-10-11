"""Fresh-process trusted loads and durable business snapshot (test driver only)."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
from vde.bootstrap import bootstrap
from vde.config import Config
from vde.persistence.uow import UnitOfWork
from vde.workflow.service import ManualWorkflow
from vde.persistence.repositories import EventLogRepository

env = bootstrap(Config(Path(sys.argv[1])))
assert env.health == 'ready'
if len(sys.argv) > 3:
    role, phase = sys.argv[3:5]
    if phase == 'before_commit':
        append = EventLogRepository.append
        def crash(self, record):
            append(self, record)
            os._exit(76)  # Uncommitted Approval/Order/EventLog all exist on connection.
        EventLogRepository.append = crash
    service = ManualWorkflow(env)
    with UnitOfWork(env.database, env.workspace) as uow:
        order = uow.orders.get(sys.argv[2])
    if role == 'brief':
        service.approve_brief(order.id, order.selected_brief_version_id, order)
    else:
        service.approve_spec_and_finish(order.id, order.selected_transformation_spec_version_id, order)
    os._exit(77)  # Commit finished, no response delivered to caller.
view = ManualWorkflow(env).view_current_approvals(sys.argv[2])
with UnitOfWork(env.database, env.workspace) as uow:
    tables = ('orders', 'input_assets', 'brief_versions', 'transformation_spec_versions',
              'approvals', 'event_log', 'execution_runs', 'artifacts', 'qa_reports')
    snapshot = {t: [dict(r) for r in uow.connection.execute(f'SELECT * FROM {t} ORDER BY 1')] for t in tables}
print(json.dumps({'view': asdict(view), 'snapshot': snapshot}, ensure_ascii=False))
