"""P3 commands compose unchanged P1 repositories in one owned transaction."""
from copy import deepcopy
from dataclasses import replace
from uuid import uuid4
from vde.contracts import content_hash, validate
from vde.errors import StorageError, utc_now
from vde.models import BriefVersionRecord, TransformationSpecVersionRecord, ApprovalRecord, EventRecord
from vde.persistence.uow import UnitOfWork
from vde.ingestion.local import LocalIngestion, source_type
from vde.ingestion.limits import Budget, raw_check, RAW
from vde.ingestion.csv_reader import read_csv
from vde.ingestion.xlsx_reader import read_xlsx
from .errors import require
from .validation import validate_brief, validate_spec
from .read_model import VerifiedSelection, VersionReview, ApprovalView, P4Handoff, json_diff


class ManualWorkflow:
    def __init__(self, env, *, allow_degraded_read=False):
        self.env = env
        self.allow_degraded_read = allow_degraded_read
        self.selections = {}  # Ephemeral user choices; never a durable approval cache.

    def _health(self, *, write=False):
        if self.env.health == 'blocked' or (self.env.health != 'ready' and
                (write or not self.allow_degraded_read)):
            raise StorageError('P3 operation blocked by workspace health; no repair attempted')

    def _uow(self):
        return UnitOfWork(self.env.database, self.env.workspace)

    def list_existing_orders(self):
        self._health()
        with self._uow() as uow:
            return uow.orders.list()

    def choose_input(self, order_id, asset_id, read_selection):
        self._health()
        reader = LocalIngestion(self.env, allow_degraded_read=self.allow_degraded_read)
        require(isinstance(read_selection, dict) and set(read_selection) == {'source_type', 'sheet_name', 'csv_options'},
                'VALIDATION_TRANSFORMATION_SCHEMA', 'Explicit complete reading selection required')
        if read_selection['source_type'] == 'LOCAL_CSV':
            require(read_selection['sheet_name'] is None and isinstance(read_selection['csv_options'], dict),
                    'VALIDATION_TRANSFORMATION_SCHEMA', 'CSV options required')
            require(set(read_selection['csv_options']) == {'encoding', 'delimiter', 'header_row'},
                    'VALIDATION_TRANSFORMATION_SCHEMA', 'Explicit encoding, delimiter and header row required')
            read = reader.preview_csv(order_id, asset_id, **read_selection['csv_options'])
        else:
            require(read_selection['source_type'] == 'LOCAL_XLSX' and read_selection['csv_options'] is None,
                    'VALIDATION_TRANSFORMATION_SCHEMA', 'Selected XLSX worksheet required')
            read = reader.preview_xlsx(order_id, asset_id, read_selection['sheet_name'])
        chosen = VerifiedSelection(order_id, asset_id, read.byte_sha256, read.source_type,
                                   deepcopy({k: read_selection[k] for k in ('sheet_name', 'csv_options')}),
                                   deepcopy(read.columns), deepcopy(read.first_rows), deepcopy(read.warnings))
        self.selections[order_id] = chosen
        return chosen

    def _current(self, uow, order_id, expected_order):
        old = uow.orders.get(order_id)
        if old != expected_order:
            raise StorageError('Stale Order compare-and-set')
        return old

    def _change(self, uow, old, event_type, **changes):
        new = replace(old, updated_at=utc_now(), **changes)
        uow.orders.update(new, expected=old)
        uow.events.append(EventRecord(str(uuid4()), old.id, event_type, new.updated_at,
                          payload_json={'status': new.status, 'approval_stage': new.approval_stage,
                                        'brief_id': new.selected_brief_version_id,
                                        'spec_id': new.selected_transformation_spec_version_id}))
        return new

    def _asset(self, uow, order_id, asset_id):
        asset = next((a for a in uow.inputs.list_for_order(order_id) if a.id == asset_id), None)
        require(asset is not None, 'INPUT_NOT_FOUND', 'Asset missing or owned by another Order')
        return asset

    def _source(self, uow, order_id, asset_id, selection=None):
        """Repeat verified P1 bytes + unchanged P2 readers under the final UoW.

        LocalIngestion opens its own BEGIN IMMEDIATE; calling it here would nest
        a second writer. Use its same P1 verification and P2 reader APIs with the
        already-owned InputAsset record instead. No new ingestion implementation.
        """
        asset = self._asset(uow, order_id, asset_id)
        budget = Budget()
        require(0 < asset.size_bytes <= RAW, 'INPUT_NOT_FOUND', 'Asset exceeds the approved local byte limit')
        raw = self.env.workspace.read_verified(asset.workspace_relpath, asset.byte_sha256, asset.size_bytes)
        raw_check(raw)
        budget.check()
        if selection is not None:
            require(selection['source_type'] == source_type(asset.original_filename),
                    'INPUT_NOT_FOUND', 'Source type differs from the registered asset')
            if selection['source_type'] == 'LOCAL_CSV':
                read = read_csv(raw, asset_id=asset.id, byte_sha256=asset.byte_sha256,
                                budget=budget, **selection['csv_options'])
            else:
                read = read_xlsx(raw, asset_id=asset.id, byte_sha256=asset.byte_sha256,
                                 budget=budget, sheet_name=selection['sheet_name'])
            return asset, VerifiedSelection(order_id, asset.id, read.byte_sha256,
                         read.source_type, deepcopy({k: selection[k] for k in ('sheet_name', 'csv_options')}),
                         read.columns, read.first_rows, read.warnings)
        return asset, None

    def _brief_source(self, uow, order, brief):
        source = brief.document_json['inputs_expected'][0]
        selection = self.selections.get(order.id)
        if selection is not None:
            require(selection.asset_id == source['asset_id'], 'INPUT_NOT_FOUND', 'Brief asset differs from explicit selection')
        options = None if selection is None else {'source_type': selection.source_type, **selection.selection}
        asset, _ = self._source(uow, order.id, source['asset_id'], options)
        require(source['input_type'] == source_type(asset.original_filename), 'INPUT_NOT_FOUND', 'Brief source type differs')
        if selection is not None:
            require(source['sheet_name'] == selection.selection['sheet_name'], 'INPUT_NOT_FOUND', 'Brief worksheet differs')
        validate_brief(brief.document_json, order, asset)
        return asset

    def _brief_approval(self, uow, order):
        require(order.selected_brief_version_id is not None, 'APPROVAL_MISSING', 'Selected Brief required')
        brief = uow.briefs.get(order.selected_brief_version_id)
        approval = uow.approvals.find_valid('BRIEF', brief.id, content_hash(brief.document_json, 'brief_version'))
        require(approval is not None, 'APPROVAL_MISSING', 'Exact selected Brief approval required')
        return brief, approval

    def _approval(self, uow, order, version, target, brief=None):
        doc = dict(schema_version='1.1', id=str(uuid4()), order_id=order.id,
                   target_type=target, target_version_id=version.id,
                   target_content_hash=version.content_hash,
                   context_brief_version_id=None if brief is None else brief.id,
                   context_brief_content_hash=None if brief is None else brief.content_hash,
                   approved_by='local_user', approved_at=utc_now())
        validate(doc, 'approval')
        return uow.approvals.append(ApprovalRecord.from_document(doc))

    def begin_manual_review(self, order_id, expected_order):
        self._health(write=True)
        with self._uow() as uow:
            old = self._current(uow, order_id, expected_order)
            require(old.status in {'DRAFT', 'NEEDS_CLARIFICATION', 'READY_FOR_APPROVAL'},
                    'STATE_INVALID_TRANSITION', 'Cannot begin manual review from this status')
            return self._change(uow, old, 'MANUAL_REVIEW_STARTED', status='ANALYZING')

    def request_clarification(self, order_id, expected_order):
        self._health(write=True)
        with self._uow() as uow:
            old = self._current(uow, order_id, expected_order)
            require(old.status == 'ANALYZING', 'STATE_INVALID_TRANSITION', 'Clarification requires ANALYZING')
            return self._change(uow, old, 'MANUAL_CLARIFICATION_REQUESTED', status='NEEDS_CLARIFICATION')

    def validate_brief(self, document, order, asset):
        self._health()
        require(order.status != 'APPROVED', 'STATE_INVALID_TRANSITION', 'Approved Brief authoring is deferred')
        return validate_brief(document, order, asset)

    def validate_spec(self, document, order, approved_brief, selection):
        self._health()
        return validate_spec(document, order, approved_brief, selection)

    def publish_brief(self, order_id, document, expected_order):
        self._health(write=True)
        with self._uow() as uow:
            old = self._current(uow, order_id, expected_order)
            require(old.status in {'ANALYZING', 'READY_FOR_APPROVAL'}, 'STATE_INVALID_TRANSITION',
                    'Brief publication requires manual review; APPROVED revisions are deferred')
            # Validate structural errors before resolving draft-controlled references.
            from .validation import _prepare
            doc = _prepare(document, 'brief_version')
            asset = self._asset(uow, order_id, doc['inputs_expected'][0]['asset_id'])
            doc = validate_brief(doc, old, asset)
            chosen = self.selections.get(order_id)
            require(chosen is not None, 'INPUT_NOT_FOUND', 'Explicit verified P2 selection is required before publication')
            doc['version_number'] = uow.briefs.latest_version_number(order_id) + 1
            record = BriefVersionRecord.from_document(doc)
            self._brief_source(uow, old, record)
            uow.briefs.append(record)
            self._change(uow, old, 'BRIEF_VERSION_PUBLISHED', status='READY_FOR_APPROVAL',
                         approval_stage='BRIEF_PENDING', selected_brief_version_id=record.id,
                         selected_transformation_spec_version_id=None)
            return record

    def approve_brief(self, order_id, brief_id, expected_order):
        self._health(write=True)
        with self._uow() as uow:
            old = self._current(uow, order_id, expected_order)
            require(old.selected_brief_version_id == brief_id, 'VERSION_INCOMPATIBLE', 'Brief is not selected')
            brief = uow.briefs.get(brief_id)
            existing = uow.approvals.find_valid('BRIEF', brief.id, content_hash(brief.document_json, 'brief_version'))
            self._brief_source(uow, old, brief)
            if existing is not None:
                return existing
            require(old.status == 'READY_FOR_APPROVAL' and old.approval_stage == 'BRIEF_PENDING',
                    'STATE_INVALID_TRANSITION', 'Brief approval requires READY_FOR_APPROVAL/BRIEF_PENDING')
            approval = self._approval(uow, old, brief, 'BRIEF')
            self._change(uow, old, 'BRIEF_APPROVED', approval_stage='TRANSFORMATION_PENDING')
            return approval

    def publish_spec(self, order_id, document, expected_order):
        self._health(write=True)
        with self._uow() as uow:
            old = self._current(uow, order_id, expected_order)
            require(old.status == 'READY_FOR_APPROVAL', 'STATE_INVALID_TRANSITION', 'Spec publication requires READY_FOR_APPROVAL')
            brief, approval = self._brief_approval(uow, old)
            chosen = self.selections.get(order_id)
            require(chosen is not None, 'INPUT_NOT_FOUND', 'Explicit verified P2 selection required')
            # Validate draft context before any input read, then repeat against fresh P2 bytes.
            doc = validate_spec(document, old, (brief, approval), chosen)
            self._brief_source(uow, old, brief)
            _, fresh = self._source(uow, order_id, chosen.asset_id, {'source_type': chosen.source_type, **chosen.selection})
            require(fresh.byte_sha256 == chosen.byte_sha256, 'APPROVAL_HASH_MISMATCH', 'Selected byte hash differs')
            doc = validate_spec(doc, old, (brief, approval), fresh)
            doc['version_number'] = uow.specs.latest_version_number(order_id) + 1
            record = uow.specs.append(TransformationSpecVersionRecord.from_document(doc))
            self._change(uow, old, 'TRANSFORMATION_SPEC_PUBLISHED', approval_stage='TRANSFORMATION_PENDING',
                         selected_transformation_spec_version_id=record.id)
            return record

    def approve_spec_and_finish(self, order_id, spec_id, expected_order):
        self._health(write=True)
        with self._uow() as uow:
            old = self._current(uow, order_id, expected_order)
            brief, ba = self._brief_approval(uow, old)
            require(old.selected_transformation_spec_version_id == spec_id, 'VERSION_INCOMPATIBLE', 'Spec is not selected')
            spec = uow.specs.get(spec_id)
            require((spec.brief_version_id, spec.brief_content_hash) == (brief.id, brief.content_hash),
                    'VERSION_INCOMPATIBLE', 'Spec exact selected Brief context differs')
            existing = uow.approvals.find_valid('TRANSFORMATION_SPEC', spec.id,
                        content_hash(spec.document_json, 'transformation_spec_version'), brief_id=brief.id, brief_hash=brief.content_hash)
            self._brief_source(uow, old, brief)
            source = spec.document_json['inputs'][0]
            _, fresh = self._source(uow, order_id, source['asset_id'],
                                    {k: source[k] for k in ('source_type', 'sheet_name', 'csv_options')})
            validate_spec(spec.document_json, old, (brief, ba), fresh)
            if existing is not None:
                require(old.status == 'APPROVED' and old.approval_stage == 'COMPLETE',
                        'STATE_INVALID_TRANSITION', 'Existing final Approval requires an atomically completed Order')
                return existing
            require(old.status == 'READY_FOR_APPROVAL' and old.approval_stage == 'TRANSFORMATION_PENDING',
                    'STATE_INVALID_TRANSITION', 'Final approval requires READY_FOR_APPROVAL/TRANSFORMATION_PENDING')
            approval = self._approval(uow, old, spec, 'TRANSFORMATION_SPEC', brief)
            self._change(uow, old, 'TRANSFORMATION_SPEC_APPROVED', status='APPROVED', approval_stage='COMPLETE')
            return approval

    def view_current_approvals(self, order_id):
        self._health()
        with self._uow() as uow:
            order = uow.orders.get(order_id)
            def review(repo, identity, target, brief=None):
                if identity is None:
                    return None
                record = repo.get(identity)
                prior = [v for v in repo.list_for_order(order_id) if v.version_number < record.version_number]
                approval = uow.approvals.find_valid(target, identity, record.content_hash,
                               brief_id=None if brief is None else brief.version_id,
                               brief_hash=None if brief is None else brief.content_hash)
                if target == 'TRANSFORMATION_SPEC' and (brief is None or brief.approval_id is None):
                    approval = None
                return VersionReview(identity, record.content_hash, deepcopy(record.document_json), True,
                           None if approval is None else approval.id,
                           json_diff({} if not prior else prior[-1].document_json, record.document_json))
            brief = review(uow.briefs, order.selected_brief_version_id, 'BRIEF')
            spec = review(uow.specs, order.selected_transformation_spec_version_id, 'TRANSFORMATION_SPEC', brief)
            return ApprovalView(order, brief, spec)

    def p4_handoff(self, order_id):
        self._health()
        with self._uow() as uow:
            order = uow.orders.get(order_id)
            brief, ba = self._brief_approval(uow, order)
            require(order.selected_transformation_spec_version_id is not None, 'APPROVAL_MISSING', 'Selected Spec required')
            spec = uow.specs.get(order.selected_transformation_spec_version_id)
            sa = uow.approvals.find_valid('TRANSFORMATION_SPEC', spec.id, spec.content_hash,
                                         brief_id=brief.id, brief_hash=brief.content_hash)
            require(sa is not None and order.status == 'APPROVED' and order.approval_stage == 'COMPLETE',
                    'APPROVAL_MISSING', 'Both exact approvals and completed Order required')
            # All hashes/facts checked before source I/O. Handoff itself has no writes.
            self._brief_source(uow, order, brief)
            source = spec.document_json['inputs'][0]
            selection = {k: source[k] for k in ('source_type', 'sheet_name', 'csv_options')}
            asset, fresh = self._source(uow, order_id, source['asset_id'], selection)
            validate_spec(spec.document_json, order, (brief, ba), fresh)
            return P4Handoff(order_id, brief.id, brief.content_hash, ba.id, spec.id, spec.content_hash,
                             sa.id, asset.id, asset.byte_sha256, deepcopy(selection))
