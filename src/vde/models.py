"""Plain persistence records. No active-record or workflow behavior."""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OrderRecord:
    id: str
    title: str
    listing_text: str
    created_at: str
    updated_at: str
    status: str = "DRAFT"
    approval_stage: str | None = None
    listing_url: str | None = None
    selected_brief_version_id: str | None = None
    selected_transformation_spec_version_id: str | None = None
    budget: str | None = None
    deadline: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class InputAssetRecord:
    id: str
    order_id: str
    original_filename: str
    workspace_relpath: str
    size_bytes: int
    byte_sha256: str
    created_at: str
    media_type: str | None = None


@dataclass(frozen=True)
class BriefVersionRecord:
    id: str
    order_id: str
    version_number: int
    schema_version: str
    content_hash: str
    document_json: dict[str, Any]
    created_at: str

    @classmethod
    def from_document(cls, doc):
        return cls(doc["version_id"], doc["order_id"], doc["version_number"], doc["schema_version"], doc["content_hash"], doc, doc["created_at"])


@dataclass(frozen=True)
class TransformationSpecVersionRecord(BriefVersionRecord):
    brief_version_id: str
    brief_content_hash: str

    @classmethod
    def from_document(cls, doc):
        return cls(doc["version_id"], doc["order_id"], doc["version_number"], doc["schema_version"], doc["content_hash"], doc, doc["created_at"], doc["brief_version_id"], doc["brief_content_hash"])


@dataclass(frozen=True)
class ApprovalRecord:
    id: str
    order_id: str
    target_type: str
    target_version_id: str
    target_content_hash: str
    context_brief_version_id: str | None
    context_brief_content_hash: str | None
    approved_by: str
    approved_at: str

    @classmethod
    def from_document(cls, doc):
        return cls(**{key: value for key, value in doc.items() if key != "schema_version"})


@dataclass(frozen=True)
class ExecutionRunRecord:
    id: str
    order_id: str
    brief_version_id: str
    brief_approval_id: str
    transformation_spec_version_id: str
    transformation_approval_id: str
    status: str
    started_at: str
    input_snapshot_json: Any
    metrics_json: Any
    finished_at: str | None = None
    error_json: dict | None = None


@dataclass(frozen=True)
class ArtifactRecord:
    id: str
    run_id: str
    artifact_type: str
    format: str
    workspace_relpath: str
    checksum: str
    created_at: str


@dataclass(frozen=True)
class QAReportRecord:
    report_id: str
    run_id: str
    brief_version_id: str
    transformation_spec_version_id: str
    generated_at: str
    overall_status: str
    report_json: dict[str, Any]

    @classmethod
    def from_document(cls, doc):
        return cls(*(doc[key] for key in ("report_id", "run_id", "brief_version_id", "transformation_spec_version_id", "generated_at", "overall_status")), doc)


@dataclass(frozen=True)
class EventRecord:
    id: str
    order_id: str
    event_type: str
    created_at: str
    run_id: str | None = None
    payload_json: Any = None
