"""Internal diagnostics mapped to the unchanged P0 public error contract."""
from datetime import datetime, timezone
from uuid import uuid4
from .contracts import validate


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class StorageError(Exception):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)

    def public(self):
        document = {
            "schema_version": "1.1", "error_id": str(uuid4()),
            "code": "STORAGE_ERROR", "category": "STORAGE",
            "severity": "BLOCKER", "stage": "STORAGE",
            "message": "Local storage integrity or persistence operation failed.",
            "details": {"reason": self.reason[:1000]},
            "order_id": None, "run_id": None, "source_id": None,
            "operation_id": None, "dataset_id": None, "column": None,
            "row_ids": [], "retryable": False, "created_at": utc_now(),
        }
        validate(document, "execution_error")
        return document
