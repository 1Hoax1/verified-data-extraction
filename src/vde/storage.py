"""Filesystem-first registration; metadata and audit share exactly one commit."""
from uuid import uuid4
from .errors import StorageError, utc_now
from .models import InputAssetRecord, ArtifactRecord, EventRecord
from .persistence.uow import UnitOfWork


class Storage:
    def __init__(self, database, workspace, checkpoint=None):
        self.database = database
        self.workspace = workspace
        self.checkpoint = checkpoint or (lambda stage: None)

    def register_input(self, *, id, order_id, original_filename, data, media_type=None, created_at=None):
        relpath = f"orders/{self.workspace.identifier(order_id)}/input/{self.workspace.identifier(id)}/payload"
        payload = self.workspace.promote(data, relpath, self.checkpoint)
        record = InputAssetRecord(id, order_id, original_filename, relpath, payload.size_bytes, payload.checksum, created_at or utc_now(), media_type)
        with UnitOfWork(self.database, self.workspace) as uow:
            uow.orders.get(order_id)
            uow.inputs._append_promoted(record)
            self.checkpoint("metadata")
            uow.events.append(EventRecord(str(uuid4()), order_id, "INPUT_ASSET_REGISTERED", record.created_at, payload_json={"asset_id": id}))
            self.checkpoint("event")
        return record

    def register_artifact(self, *, id, run_id, artifact_type, format, data, created_at=None):
        # Short read transaction resolves immutable run/order references before
        # file I/O; the mutation UoW still opens only after promotion.
        with UnitOfWork(self.database, self.workspace) as uow:
            run = uow.runs.get(run_id)
        self.workspace.reserve_run(run.order_id, run_id)
        relpath = f"orders/{self.workspace.identifier(run.order_id)}/runs/{self.workspace.identifier(run_id)}/artifacts/{self.workspace.identifier(id)}/payload"
        payload = self.workspace.promote(data, relpath, self.checkpoint)
        record = ArtifactRecord(id, run_id, artifact_type, format, relpath, payload.checksum, created_at or utc_now())
        with UnitOfWork(self.database, self.workspace) as uow:
            uow.runs.get(run_id)
            uow.artifacts._append_promoted(record)
            self.checkpoint("metadata")
            uow.events.append(EventRecord(str(uuid4()), run.order_id, "ARTIFACT_REGISTERED", record.created_at, run_id, {"artifact_id": id}))
            self.checkpoint("event")
        return record
