"""One explicit local Execute action; rendering never starts or resumes work."""
import streamlit as st

from vde.errors import StorageError
from vde.persistence.uow import UnitOfWork
from .errors import ExecutionError
from .service import ExecutionService


def panel(env):
    st.subheader('Deterministic transformation')
    if not st.checkbox('Open deterministic transformation', key='p4_open'):
        return
    if env.health != 'ready':
        st.warning('Execution is disabled while local storage is blocked or has incomplete work. No automatic recovery is performed.')
        st.button('Execute', key='p4_execute', disabled=True)
        return
    service = ExecutionService(env)
    try:
        with UnitOfWork(env.database, env.workspace) as uow:
            orders = uow.orders.list()
        if not orders:
            st.info('Select a pre-existing Order with two approved versions.')
            return
        order_id = st.selectbox('P4 existing Order', [o.id for o in orders], key='p4_order')
        order = next(o for o in orders if o.id == order_id)
        eligible = order.status in {'APPROVED', 'FAILED'} and order.approval_stage == 'COMPLETE'
        handoff = None
        if eligible:
            handoff = service.fresh_handoff(order_id)
            with service._uow() as uow:
                asset = uow.inputs.get(handoff.asset_id)
                spec = uow.specs.get(handoff.transformation_spec_version_id)
            st.write(f'Source: {asset.original_filename}; SHA-256: {asset.byte_sha256}')
            st.json(handoff.input_selection)
            st.write('Pipeline: ' + ' → '.join(op['type'] for op in spec.document_json['pipeline']))
            st.caption('Limits: 100,000 rows, 200 columns, 512 MiB additional RSS and a 120-second soft time budget.')
        confirmed = st.checkbox('I confirm the selected source and pipeline', key='p4_confirm', disabled=not eligible)
        if st.button('Execute', key='p4_execute', disabled=not eligible or not confirmed or handoff is None):
            result = service.execute(order_id, order, handoff)
            st.session_state['p4_last_run_'+order_id] = result.run_id
            st.success('Transformation stored. Export and QA are pending.')
        with service._uow() as uow:
            runs = uow.runs.list_for_order(order_id)
        for run in runs:
            st.write(f'Run {run.id}: {run.status}')
            if run.metrics_json:
                st.json(run.metrics_json)
            if run.error_json:
                st.error(run.error_json['code'])
                st.json(run.error_json)
    except (ExecutionError, StorageError) as exc:
        public = exc.public()
        st.error(public['code'])
        st.json(public)
