import sqlite3
from ..errors import StorageError
from .database import connect
from .repositories import (OrderRepository, InputAssetRepository, BriefVersionRepository,
                           TransformationSpecVersionRepository, ApprovalRepository,
                           ExecutionRunRepository, ArtifactRepository, QAReportRepository,
                           EventLogRepository)


class UnitOfWork:
    """One owned connection and transaction; the context exit is the only commit."""
    def __init__(self, database, workspace):
        self.database = database
        self.workspace = workspace
        self.connection = None
        self.rollback_only = False
        for name, repo in [("orders", OrderRepository), ("inputs", InputAssetRepository),
                           ("briefs", BriefVersionRepository), ("specs", TransformationSpecVersionRepository),
                           ("approvals", ApprovalRepository), ("runs", ExecutionRunRepository),
                           ("artifacts", ArtifactRepository), ("reports", QAReportRepository), ("events", EventLogRepository)]:
            setattr(self, name, repo(self))

    def ensure_active(self):
        if self.connection is None or not self.connection.in_transaction:
            raise StorageError("Repository requires an active Unit of Work")

    def __enter__(self):
        if self.connection is not None:
            raise StorageError("Nested Unit of Work is forbidden")
        self.rollback_only = False
        self.connection = connect(self.database)
        try:
            self.connection.execute("BEGIN IMMEDIATE")
        except sqlite3.Error as exc:
            self.connection.close()
            self.connection = None
            raise StorageError("Cannot begin Unit of Work") from exc
        return self

    def __exit__(self, kind, value, traceback):
        try:
            if kind is not None or self.rollback_only:
                self.connection.rollback()
                if kind is None:
                    raise StorageError("Unit of Work rolled back after a caught persistence failure")
            else:
                self.connection.commit()
        except sqlite3.Error as exc:
            self.connection.rollback()
            raise StorageError("Database commit failed") from exc
        finally:
            self.connection.close()
            self.connection = None
