"""Opaque byte storage. POSIX hard-link promotion never overwrites a path."""
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
from urllib.parse import quote
from uuid import uuid4

from .errors import StorageError


@dataclass(frozen=True)
class PromotedPayload:
    relpath: str
    size_bytes: int
    checksum: str


class Workspace:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()

    def path(self, relpath):
        if not isinstance(relpath, str) or not relpath or "\x00" in relpath or "\\" in relpath or ":" in relpath:
            raise StorageError("Invalid workspace-relative path")
        path = PurePosixPath(relpath)
        if path.is_absolute() or PureWindowsPath(relpath).drive or any(part in {"..", ".", ""} for part in relpath.split("/")):
            raise StorageError("Workspace path traversal rejected")
        target = self.root / path
        # Reject symlinks throughout payload paths, including dangling links.
        for candidate in [target, *target.parents]:
            if candidate == self.root:
                break
            if candidate.is_symlink():
                raise StorageError("Workspace symlink path rejected")
        if not target.resolve().is_relative_to(self.root):
            raise StorageError("Workspace path escapes configured root")
        return target

    @staticmethod
    def identifier(value):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", value):
            raise StorageError("Invalid controlled storage identifier")
        return quote(value, safe="")

    def _sync_directory(self, directory):
        # Failure is blocking. No overwrite/copy fallback and no claim of fsync
        # support on filesystems that reject this primitive.
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _mkdir(self, directory):
        missing = []
        current = directory
        while not current.exists():
            missing.append(current)
            current = current.parent
        for item in reversed(missing):
            item.mkdir(exist_ok=True)
            self._sync_directory(item)
            self._sync_directory(item.parent)

    def prepare(self):
        try:
            self._mkdir(self.root)
            for relpath in ["orders", ".staging", "recovery/quarantine"]:
                self._mkdir(self.path(relpath))
            probe = self.path(".staging/" + str(uuid4()))
            with probe.open("xb") as stream:
                stream.write(b"ready")
                stream.flush()
                os.fsync(stream.fileno())
            probe.unlink()
            self._sync_directory(probe.parent)
        except OSError as exc:
            raise StorageError("Workspace preparation or durability barrier failed") from exc

    def reserve_run(self, order_id, run_id):
        try:
            prefix = f"orders/{self.identifier(order_id)}/runs/{self.identifier(run_id)}"
            for name in ["raw", "intermediate", "result", "reports", "artifacts"]:
                self._mkdir(self.path(prefix + "/" + name))
        except OSError as exc:
            raise StorageError("Run directory preparation failed") from exc

    def inspect(self, relpath):
        try:
            path = self.path(relpath)
            digest = hashlib.sha256()
            size = 0
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
            return size, digest.hexdigest()
        except OSError as exc:
            raise StorageError("Referenced file missing or unreadable") from exc

    def promote(self, data, relpath, checkpoint=None):
        checkpoint = checkpoint or (lambda stage: None)
        try:
            target = self.path(relpath)
            if not relpath.startswith("orders/"):
                raise StorageError("Payload must use a controlled orders location")
            staging_dir = self.path(".staging/" + str(uuid4()))
            self._mkdir(staging_dir)
            staged = staging_dir / "payload.tmp"
            with staged.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            self._sync_directory(staging_dir)
            size, checksum = self.inspect(staged.relative_to(self.root).as_posix())
            checkpoint("staged")
            self._mkdir(target.parent)
            # link() is atomic and fails on EEXIST even for identical contents.
            # Staging and destination must use the same mounted filesystem.
            os.link(staged, self.path(relpath), follow_symlinks=False)
            self._sync_directory(target.parent)
            staged.unlink()
            self._sync_directory(staging_dir)
            staging_dir.rmdir()
            self._sync_directory(staging_dir.parent)
            checkpoint("promoted")
            return PromotedPayload(relpath, size, checksum)
        except OSError as exc:
            raise StorageError("Atomic payload promotion or durability barrier failed") from exc
