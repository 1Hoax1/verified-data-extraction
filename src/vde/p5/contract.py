"""Read-only exact P1/P3/P4 admission. No invented or imported Approvals."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from types import SimpleNamespace
from jsonschema.exceptions import ValidationError
from vde.contracts import content_hash, validate
from vde.execution.service import ExecutionService
from vde.execution.wire import REVISION, iter_payload
from vde.persistence.uow import UnitOfWork
from vde.recovery import recover
from vde.workflow.validation import validate_spec
from vde.workflow.errors import WorkflowError
from .errors import P5Error, require
from .project import describe, semantic_row


@dataclass(frozen=True)
class Context:
    order: object
    run: object
    brief: object
    spec: object
    asset: object
    internal: object
    artifacts: tuple
    reports: tuple
    projection: object


def health(env):
    require(recover(env.database, env.workspace).health == 'ready',
            'STORAGE_ERROR', 'Workspace is blocked or degraded; no P5 writes')


def admit(uow, env, run_id, expected_order=None, *, projection_required=True):
    run = uow.runs.get(run_id)
    order = uow.orders.get(run.order_id)
    terminal_context = (expected_order is not None and order.status in ('READY','NEEDS_FIX') and
                        (expected_order.id,expected_order.selected_brief_version_id,
                         expected_order.selected_transformation_spec_version_id,expected_order.approval_stage) ==
                        (order.id,order.selected_brief_version_id,
                         order.selected_transformation_spec_version_id,'COMPLETE'))
    require(expected_order is None or order == expected_order or terminal_context,
            'STATE_INVALID_TRANSITION', 'Stale P5 Order snapshot')
    require(run.status == 'succeeded' and order.status in ('EXECUTING', 'READY', 'NEEDS_FIX')
            and order.approval_stage == 'COMPLETE', 'STATE_INVALID_TRANSITION', 'P5 requires a succeeded P4 Run and eligible Order')
    require((order.selected_brief_version_id, order.selected_transformation_spec_version_id) ==
            (run.brief_version_id, run.transformation_spec_version_id),
            'VERSION_INCOMPATIBLE', 'Selected versions differ from P4 Run')
    brief, spec = uow.briefs.get(run.brief_version_id), uow.specs.get(run.transformation_spec_version_id)
    require(brief.order_id == spec.order_id == order.id and
            (spec.brief_version_id, spec.brief_content_hash) == (brief.id, brief.content_hash),
            'VERSION_INCOMPATIBLE', 'Spec exact Brief context differs')
    require(content_hash(brief.document_json, 'brief_version') == brief.content_hash and
            content_hash(spec.document_json, 'transformation_spec_version') == spec.content_hash,
            'APPROVAL_HASH_MISMATCH', 'Semantic version hash differs')
    ba, sa = uow.approvals.get(run.brief_approval_id), uow.approvals.get(run.transformation_approval_id)
    require((ba.order_id, ba.target_type, ba.target_version_id, ba.target_content_hash,
             ba.context_brief_version_id, ba.context_brief_content_hash) ==
            (order.id, 'BRIEF', brief.id, brief.content_hash, None, None),
            'APPROVAL_HASH_MISMATCH', 'Exact Brief Approval differs')
    require((sa.order_id, sa.target_type, sa.target_version_id, sa.target_content_hash,
             sa.context_brief_version_id, sa.context_brief_content_hash) ==
            (order.id, 'TRANSFORMATION_SPEC', spec.id, spec.content_hash, brief.id, brief.content_hash),
            'APPROVAL_HASH_MISMATCH', 'Exact Spec Approval differs')
    for approval in (ba, sa):
        require(approval.approved_by == 'local_user' and
                datetime.fromisoformat(approval.approved_at.replace('Z', '+00:00')) <= datetime.now(timezone.utc),
                'APPROVAL_MISSING', 'Actual local-user Approval required; future synthetic record is not authority')
    validate(brief.document_json, 'brief_version')
    source = spec.document_json['inputs'][0]
    asset = uow.inputs.get(source['asset_id'])
    require(asset.order_id == order.id and 0 < asset.size_bytes <= 100000000,
            'VERSION_INCOMPATIBLE', 'Run source differs from Order')
    snapshot = dict(asset_id=asset.id, source_byte_sha256=asset.byte_sha256,
                    input_selection={k: source[k] for k in ('source_type', 'sheet_name', 'csv_options')},
                    brief_content_hash=brief.content_hash, transformation_content_hash=spec.content_hash)
    require(run.input_snapshot_json == snapshot and run.metrics_json['source'] == snapshot,
            'VERSION_INCOMPATIBLE', 'P4 input snapshot differs from exact approved source')
    selection = SimpleNamespace(asset_id=asset.id, order_id=order.id, source_type=source['source_type'],
                                selection={k: source[k] for k in ('sheet_name', 'csv_options')})
    try:
        validated = validate_spec(spec.document_json, order, (brief, ba), selection)
        require(validated == spec.document_json, 'APPROVAL_HASH_MISMATCH', 'Spec would require mutation')
    except WorkflowError as exc:
        raise P5Error(exc.code, exc.reason) from exc
    size, digest = env.workspace.inspect(asset.workspace_relpath)
    require((size, digest) == (asset.size_bytes, asset.byte_sha256), 'STORAGE_ERROR', 'Source bytes differ')
    artifacts = tuple(uow.artifacts.list_for_run(run_id))
    internals = [a for a in artifacts if a.artifact_type == 'P4_INTERNAL']
    require(len(internals) == 1, 'STORAGE_ERROR', 'Exactly one internal P4 Artifact required')
    internal, metrics = internals[0], run.metrics_json
    require(internal.format == metrics['format_revision'] == REVISION and
            internal.checksum == metrics['logical_result_checksum'] and
            metrics['dataset_id'] == spec.document_json['output']['dataset_id'],
            'SCHEMA_MISMATCH', 'P4 internal identity differs')
    projection = describe(brief.document_json, spec.document_json, metrics['columns']) if projection_required else None
    require(env.workspace.inspect(internal.workspace_relpath)[1] == internal.checksum,
            'STORAGE_ERROR', 'P4 Artifact bytes differ')
    reports = tuple(uow.reports.list_for_run(run_id))
    require(len(reports) <= 1, 'STORAGE_ERROR', 'Ambiguous P5 reports')
    return Context(order, run, brief, spec, asset, internal, artifacts, reports, projection)


def read_internal(env, context, budget):
    final = [a for a in context.artifacts if a != context.internal]
    size, _ = env.workspace.inspect(context.internal.workspace_relpath)
    # P4's frozen decoder temporarily holds a second bytes slice.
    budget.check(allocation=size*2)
    if not final:
        handle, data = ExecutionService(env).read_result(context.run.id)
        require((handle.artifact_id, handle.checksum, handle.row_count) ==
                (context.internal.id, context.internal.checksum, context.run.metrics_json['row_count']),
                'SCHEMA_MISMATCH', 'P4 verified delivery differs')
    else:
        # P4 read_result intentionally accepts only its own single Artifact.
        # Retry with an already committed P5 result rechecks the same immutable
        # P4 object directly, rather than changing the frozen P4 API.
        data = env.workspace.read_verified(context.internal.workspace_relpath, context.internal.checksum)
        count = sum(1 for _ in rows(data, context))
        require(count == context.run.metrics_json['row_count'], 'SCHEMA_MISMATCH', 'P4 row count differs')
    budget.check()
    return data


def rows(data, context):
    original = iter_payload(data, expected_columns=context.projection.columns,
                            dataset_id=context.projection.output['dataset_id'])
    return (semantic_row(row, context.projection) for row in original)
