"""Separate-process SIGKILL/commit witnesses; never imported by runtime."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import signal
import sys

from vde.bootstrap import bootstrap
from vde.config import Config
from vde.errors import StorageError
from vde.persistence.uow import UnitOfWork
from vde.persistence.repositories import EventLogRepository
from vde.workflow.service import ManualWorkflow
from vde.execution.service import ExecutionService


def main():
    root, stage = Path(sys.argv[1]), sys.argv[2]
    env = bootstrap(Config(root))
    assert env.health == 'ready'
    with UnitOfWork(env.database, env.workspace) as uow:
        order = uow.orders.list()[0]
    handoff = ManualWorkflow(env).p4_handoff(order.id)
    if stage == 'handoff':
        print(json.dumps(asdict(handoff)))
        return
    if stage == 'event_insert_failure':
        append = EventLogRepository.append

        def fail_artifact(self, record):
            if record.event_type == 'ARTIFACT_REGISTERED':
                raise StorageError('Injected Artifact EventLog append failure')
            return append(self, record)
        EventLogRepository.append = fail_artifact

    def checkpoint(current):
        if current == stage:
            os.kill(os.getpid(), signal.SIGKILL)
    try:
        ExecutionService(env, checkpoint=checkpoint).execute(order.id, order, handoff)
    except StorageError as exc:
        if stage != 'event_insert_failure':
            raise
        print(json.dumps(exc.public()))


if __name__ == '__main__':
    main()
