"""Session-only JSON drafts and two explicit human confirmations."""
from dataclasses import asdict
from uuid import uuid4
import streamlit as st
from vde.contracts import loads, dumps
from vde.errors import StorageError, utc_now
from vde.ingestion.diagnostics import IngestionError
from vde.ingestion.local import LocalIngestion, source_type
from .errors import WorkflowError
from .service import ManualWorkflow


def draft(text, order_id, role):
    try:
        document = loads(text)
        if not isinstance(document, dict):
            raise ValueError('JSON object required')
        # These are version metadata, excluded from the semantic P0 hash.
        document['version_id'] = str(uuid4())
        document['version_number'] = 1  # Service allocates monotonically under UoW.
        document['created_at'] = utc_now()
        document['order_id'] = order_id
        return document
    except (ValueError, TypeError) as exc:
        raise WorkflowError('VALIDATION_BRIEF_SCHEMA' if role == 'brief' else
                            'VALIDATION_TRANSFORMATION_SCHEMA', 'Enter a strict JSON object without duplicate keys') from exc


def panel(env):
    st.subheader('Manual Brief and TransformationSpec')
    st.caption('Unsaved JSON drafts exist only in this session and may be lost on restart.')
    if env.health == 'blocked':
        st.error('P3 is blocked by local storage health.')
        return
    if not st.checkbox('Open manual workflow', key='p3_open'):
        return
    permit = env.health == 'ready' or st.checkbox('Allow P3 verified read-only review', key='p3_read_only')
    if not permit:
        return
    service = ManualWorkflow(env, allow_degraded_read=env.health == 'degraded')
    order_id = asset_id = None
    try:
        orders = service.list_existing_orders()
        if not orders:
            st.info('P3 requires a pre-existing Order and registered input.')
            return
        order_id = st.selectbox('P3 existing Order', [o.id for o in orders], key='p3_order')
        view = service.view_current_approvals(order_id)
        order = view.order
        st.write(f'Status: {order.status}; approval stage: {order.approval_stage or "—"}')
        readonly = env.health != 'ready' or order.status not in {'DRAFT', 'NEEDS_CLARIFICATION', 'ANALYZING', 'READY_FOR_APPROVAL'}
        reader = LocalIngestion(env, allow_degraded_read=env.health == 'degraded')
        assets = reader.assets(order_id)
        asset_id = st.selectbox('P3 registered input', [a.id for a in assets], index=None,
                               disabled=readonly, key='p3_asset_' + order_id)
        options = None
        asset = next((a for a in assets if a.id == asset_id), None)
        if asset:
            st.json({'asset_id': asset.id, 'size_bytes': asset.size_bytes, 'byte_sha256': asset.byte_sha256})
            kind = source_type(asset.original_filename)
            if kind == 'LOCAL_CSV':
                encoding = st.selectbox('P3 encoding', ['UTF-8', 'UTF-8-SIG', 'CP1251'], index=None, disabled=readonly)
                delimiter = st.selectbox('P3 delimiter', [',', ';', '\t'], index=None, disabled=readonly)
                header = st.number_input('P3 header row', min_value=0, max_value=100, value=0, disabled=readonly)
                if encoding is not None and delimiter is not None:
                    options = {'source_type': kind, 'sheet_name': None,
                               'csv_options': {'encoding': encoding, 'delimiter': delimiter, 'header_row': header}}
            else:
                sheet = st.selectbox('P3 worksheet', reader.list_xlsx_sheets(order_id, asset.id), index=None, disabled=readonly)
                if sheet is not None:
                    options = {'source_type': kind, 'sheet_name': sheet, 'csv_options': None}
            if st.button('Verify P3 input and preview', disabled=options is None or readonly):
                selected = service.choose_input(order_id, asset.id, options)
                st.session_state['p3_selection_' + order_id] = (asset.id, options, selected)
        prior = st.session_state.get('p3_selection_' + order_id)
        selected = prior[2] if prior and (asset_id, options) == (prior[0], prior[1]) else None
        if selected is not None:
            service.selections[order_id] = selected
            st.json(asdict(selected))
            for warning in selected.warnings:
                st.warning(warning['code'])
        if st.button('Begin manual review', disabled=readonly or selected is None or
                     order.status not in {'DRAFT', 'NEEDS_CLARIFICATION', 'READY_FOR_APPROVAL'}):
            service.begin_manual_review(order_id, order)
            st.rerun()
        if st.button('Request clarification', disabled=readonly or order.status != 'ANALYZING'):
            service.request_clarification(order_id, order)
            st.rerun()

        for role, review in [('brief', view.brief), ('spec', view.spec)]:
            st.write('Brief' if role == 'brief' else 'TransformationSpec')
            if review:
                st.json({'version_id': review.version_id, 'content_hash': review.content_hash,
                         'approval_id': review.approval_id})
                st.json(review.document)
                st.write('Changes from the preceding published version')
                st.json(review.diff)
            blocked = readonly or selected is None or (role == 'brief' and order.status not in {'ANALYZING', 'READY_FOR_APPROVAL'}) or (
                role == 'spec' and (order.status != 'READY_FOR_APPROVAL' or view.brief is None or view.brief.approval_id is None))
            key = 'p3_draft_' + role + '_' + order_id
            text = st.text_area('Brief JSON draft' if role == 'brief' else 'TransformationSpec JSON draft',
                                value='{}' if review is None else dumps(review.document),
                                height=250, key=key, disabled=blocked)
            if st.button('Validate Brief draft' if role == 'brief' else 'Validate TransformationSpec draft', disabled=blocked):
                document = draft(text, order_id, role)
                if role == 'brief':
                    validated = service.validate_brief(document, order, asset)
                else:
                    with service._uow() as uow:
                        context = service._brief_approval(uow, order)
                    validated = service.validate_spec(document, order, context, selected)
                st.json(validated)
                st.success('Draft is valid; calculated hash shown. Save and approval are separate actions.')
            if st.button('Save new Brief version' if role == 'brief' else 'Save new TransformationSpec version', disabled=blocked):
                command = service.publish_brief if role == 'brief' else service.publish_spec
                command(order_id, draft(text, order_id, role), order)
                st.rerun()
            eligible = review is not None and review.approval_id is None and not readonly and (
                order.approval_stage == ('BRIEF_PENDING' if role == 'brief' else 'TRANSFORMATION_PENDING'))
            intent = st.checkbox('Confirm this exact Brief ID and hash' if role == 'brief' else
                                 'Confirm this exact Spec ID, hash and approved Brief context',
                                 disabled=not eligible, key='p3_confirm_' + role + '_' +
                                 (review.version_id if review else order_id))
            if st.button('I approve this Brief version' if role == 'brief' else 'I approve TransformationSpec',
                         disabled=not eligible or not intent) and eligible and intent:
                command = service.approve_brief if role == 'brief' else service.approve_spec_and_finish
                command(order_id, review.version_id, order)
                st.rerun()
        if order.status == 'APPROVED':
            st.info('Approved versions are read-only. Immediate revision is deferred under CR-P3-001.')
            st.json(asdict(service.p4_handoff(order_id)))
        st.caption('P4 execution unavailable.')
    except (WorkflowError, IngestionError) as exc:
        st.error(exc.code)
        st.json(exc.public(order_id=order_id, source_id=asset_id))
    except StorageError as exc:
        st.error('STORAGE_ERROR')
        st.json(exc.public())
