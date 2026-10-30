"""Fresh immutable P1/P3 admission checks, before any source byte I/O."""
from copy import deepcopy
from dataclasses import dataclass

from vde.contracts import content_hash, validate
from vde.ingestion.local import source_type
from vde.workflow.read_model import VerifiedSelection
from vde.workflow.validation import validate_spec
from .errors import require


@dataclass(frozen=True)
class Plan:
    order: object
    brief: object
    spec: object
    brief_approval: object
    spec_approval: object
    asset: object
    handoff: object

    @property
    def pipeline(self):
        return self.spec.document_json['pipeline']

    @property
    def dataset_id(self):
        return self.spec.document_json['output']['dataset_id']


def verify_and_plan(uow, order_id, expected_order, handoff):
    require(handoff.order_id == order_id, 'VERSION_INCOMPATIBLE', 'Handoff Order differs')
    order = uow.orders.get(order_id)
    require(order == expected_order, 'STATE_INVALID_TRANSITION', 'Stale Order CAS snapshot')
    require(order.status in {'APPROVED', 'FAILED'} and order.approval_stage == 'COMPLETE',
            'STATE_INVALID_TRANSITION', 'Approved or explicitly retried failed Order required')
    require((order.selected_brief_version_id, order.selected_transformation_spec_version_id) ==
            (handoff.brief_version_id, handoff.transformation_spec_version_id),
            'VERSION_INCOMPATIBLE', 'Selected version pointers differ')
    brief, spec = uow.briefs.get(handoff.brief_version_id), uow.specs.get(handoff.transformation_spec_version_id)
    require(brief.order_id == spec.order_id == order_id and
            (spec.brief_version_id, spec.brief_content_hash) == (brief.id, brief.content_hash),
            'VERSION_INCOMPATIBLE', 'Exact version/Brief context differs')
    require((handoff.brief_content_hash, handoff.transformation_content_hash) ==
            (content_hash(brief.document_json, 'brief_version'),
             content_hash(spec.document_json, 'transformation_spec_version')),
            'APPROVAL_HASH_MISMATCH', 'Handoff version hash differs')
    require(handoff.brief_approval_id and handoff.transformation_approval_id,
            'APPROVAL_MISSING', 'Both explicit Approval IDs required')
    ba = uow.approvals.find_valid('BRIEF', brief.id, brief.content_hash)
    sa = uow.approvals.find_valid('TRANSFORMATION_SPEC', spec.id, spec.content_hash,
                                 brief_id=brief.id, brief_hash=brief.content_hash)
    require(ba is not None and sa is not None and
            (ba.id, sa.id) == (handoff.brief_approval_id, handoff.transformation_approval_id),
            'APPROVAL_MISSING', 'Exact immutable Approval facts required')
    asset = next((a for a in uow.inputs.list_for_order(order_id) if a.id == handoff.asset_id), None)
    require(asset is not None, 'INPUT_NOT_FOUND', 'Order-owned InputAsset required')
    require(asset.byte_sha256 == handoff.byte_sha256, 'APPROVAL_HASH_MISMATCH', 'Source byte hash differs')
    source = spec.document_json['inputs'][0]
    require(source['asset_id'] == asset.id, 'INPUT_NOT_FOUND', 'Source asset differs from Spec')
    selection = {k: deepcopy(source[k]) for k in ('source_type', 'sheet_name', 'csv_options')}
    require(handoff.input_selection == selection, 'VALIDATION_TRANSFORMATION_SCHEMA', 'Read selection differs from approved Spec')
    require(source_type(asset.original_filename) == source['source_type'], 'INPUT_NOT_FOUND', 'Stored filename/source type mismatch')
    verified = VerifiedSelection(order_id, asset.id, asset.byte_sha256, source['source_type'],
                                 {k: deepcopy(source[k]) for k in ('sheet_name', 'csv_options')}, [], [])
    validate(brief.document_json, 'brief_version')
    validate_spec(spec.document_json, order, (brief, ba), verified)
    return Plan(order, brief, spec, ba, sa, asset, deepcopy(handoff))
