from dataclasses import dataclass
from .config import Config
from .errors import StorageError
from .persistence.database import connect, migrate, check_integrity
from .recovery import RecoveryReport, recover
from .workspace import Workspace


@dataclass
class BootstrapResult:
    workspace: Workspace | None
    recovery: RecoveryReport

    @property
    def health(self):
        return self.recovery.health

    @property
    def database(self):
        if self.workspace is None:
            raise StorageError("Workspace unavailable")
        return self.workspace.path("app.sqlite3")


def bootstrap(config=None):
    workspace = None
    try:
        workspace = Workspace((config or Config.from_environment()).workspace_root)
        workspace.prepare()
        connection = connect(workspace.path("app.sqlite3"))
        try:
            migrate(connection)
            check_integrity(connection)
        finally:
            connection.close()
        return BootstrapResult(workspace, recover(workspace.path("app.sqlite3"), workspace))
    except StorageError as exc:
        return BootstrapResult(workspace, RecoveryReport(errors=[exc.public()]))
