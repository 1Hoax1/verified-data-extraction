from dataclasses import dataclass
import hashlib
from pathlib import Path
import sqlite3

from ..errors import StorageError, utc_now


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str

    @property
    def checksum(self):
        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()


def packaged_migrations():
    return tuple(Migration(int(p.stem.split("_", 1)[0]), p.stem, p.read_text(encoding="utf-8")) for p in sorted(Path(__file__).with_name("migrations").glob("*.sql")))


def connect(path):
    connection = None
    try:
        connection = sqlite3.connect(path, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        if connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] != "wal":
            raise StorageError("WAL journaling unavailable")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection
    except (sqlite3.Error, OSError, StorageError) as exc:
        if connection:
            connection.close()
        if isinstance(exc, StorageError):
            raise
        raise StorageError("Database open or connection policy failed") from exc


def check_integrity(connection):
    try:
        if [row[0] for row in connection.execute("PRAGMA integrity_check")] != ["ok"]:
            raise StorageError("Database integrity check failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise StorageError("Database foreign-key integrity failed")
    except sqlite3.Error as exc:
        raise StorageError("Database integrity check failed") from exc


def statements(sql):
    buffer = ""
    for character in sql:
        buffer += character
        if character == ";" and sqlite3.complete_statement(buffer):
            yield buffer
            buffer = ""
    if buffer.strip() and not all(not line.strip() or line.lstrip().startswith("--") for line in buffer.splitlines()):
        raise StorageError("Incomplete migration definition")


def migrate(connection, migrations=None):
    migrations = packaged_migrations() if migrations is None else migrations
    versions = [m.version for m in migrations]
    if versions != sorted(set(versions)):
        raise StorageError("Migration definitions are not strictly ordered")
    try:
        connection.execute("BEGIN IMMEDIATE")
        exists = connection.execute("SELECT 1 FROM sqlite_master WHERE name='schema_migrations'").fetchone()
        applied = connection.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall() if exists else []
        if [row["version"] for row in applied] != versions[:len(applied)]:
            raise StorageError("Unknown or non-prefix migration history")
        for row, definition in zip(applied, migrations):
            if (row["name"], row["checksum"]) != (definition.name, definition.checksum):
                raise StorageError("Migration name/checksum drift")
        for definition in migrations[len(applied):]:
            # executescript implicitly commits; execute complete statements instead.
            for statement in statements(definition.sql):
                connection.execute(statement)
            connection.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (definition.version, definition.name, definition.checksum, utc_now()))
        connection.commit()
    except (sqlite3.Error, StorageError) as exc:
        connection.rollback()
        if isinstance(exc, StorageError):
            raise
        raise StorageError("Migration failed and rolled back") from exc
