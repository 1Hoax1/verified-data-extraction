"""Detect only: never change business records or adopt filesystem payloads."""
from dataclasses import dataclass, field
import os
import sqlite3

from .errors import StorageError
from .persistence.database import check_integrity
from .persistence.uow import UnitOfWork


@dataclass
class RecoveryReport:
    errors: list[dict] = field(default_factory=list)
    staging: list[str] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)
    stale_runs: list[str] = field(default_factory=list)

    @property
    def health(self):
        if self.errors:
            return "blocked"
        if self.staging or self.orphans or self.stale_runs:
            return "degraded"
        return "ready"


def recover(database, workspace):
    report = RecoveryReport()
    try:
        with UnitOfWork(database, workspace) as uow:
            check_integrity(uow.connection)
            # Check all entities, including exact polymorphic guards which
            # foreign_key_check alone cannot detect after offline corruption.
            for repo in [uow.orders, uow.briefs, uow.specs, uow.approvals, uow.runs, uow.reports, uow.events]:
                identities = [row[0] for row in uow.connection.execute(f"SELECT {repo.pk} FROM {repo.table}")]
                for identity in identities:
                    repo.get(identity)
            referenced = set()
            for repo, checksum_field in [(uow.inputs, "byte_sha256"), (uow.artifacts, "checksum")]:
                for row in uow.connection.execute(f"SELECT * FROM {repo.table}").fetchall():
                    record = repo._decode(row)
                    referenced.add(record.workspace_relpath)
                    size, checksum = workspace.inspect(record.workspace_relpath)
                    if checksum != getattr(record, checksum_field) or (repo is uow.inputs and size != record.size_bytes):
                        raise StorageError("Referenced file size/checksum mismatch")
            report.stale_runs = [row[0] for row in uow.connection.execute("SELECT id FROM execution_runs WHERE status='running' ORDER BY id")]
            for area, output in [(".staging", report.staging), ("orders", report.orphans)]:
                def walk_error(exc):
                    raise StorageError("Workspace recovery traversal failed") from exc
                for directory, directories, files in os.walk(workspace.path(area), followlinks=False, onerror=walk_error):
                    for name in directories + files:
                        path = workspace.root / directory / name
                        relative = path.relative_to(workspace.root).as_posix()
                        checked = workspace.path(relative)
                        if name in files and checked.is_file() and relative not in referenced:
                            output.append(relative)
            report.staging.sort()
            report.orphans.sort()
    except (StorageError, sqlite3.Error, OSError, ValueError, TypeError, KeyError) as exc:
        error = exc if isinstance(exc, StorageError) else StorageError("Persisted record or recovery scan failed")
        report.errors.append(error.public())
    return report
