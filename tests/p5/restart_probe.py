"""Separate-process SIGKILL witness. Test-only; no application import of it."""
import os
from pathlib import Path
import signal
import sys
from vde.bootstrap import bootstrap
from vde.config import Config
from vde.persistence.uow import UnitOfWork
from vde.p5.service import P5Service


def main():
    workspace,run_id,stage=Path(sys.argv[1]),sys.argv[2],sys.argv[3]
    env=bootstrap(Config(workspace));assert env.health=='ready'
    with UnitOfWork(env.database,env.workspace) as u:
        order=u.orders.get(u.runs.get(run_id).order_id)
    def checkpoint(current):
        if current==stage:os.kill(os.getpid(),signal.SIGKILL)
    P5Service(env,checkpoint=checkpoint).complete(run_id,order)
    raise AssertionError('Requested crash checkpoint was not reached')


if __name__=='__main__':main()
