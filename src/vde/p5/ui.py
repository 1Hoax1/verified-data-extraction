"""One explicit P5 action; passive rerenders never initiate work."""
import streamlit as st
from vde.errors import StorageError
from vde.persistence.uow import UnitOfWork
from .errors import P5Error
from .service import P5Service


def panel(env):
    st.subheader('Export and deterministic QA')
    if not st.checkbox('Open export and QA',key='p5_open'):
        return
    if env.health != 'ready':
        st.warning('Export and QA require healthy local storage.')
        st.button('Export + deterministic QA',key='p5_complete',disabled=True)
        return
    try:
        with UnitOfWork(env.database,env.workspace) as uow:
            orders = uow.orders.list()
        if not orders:
            st.info('Choose an existing Order after transformation succeeds.')
            return
        selected = st.selectbox('P5 existing Order',[o.id for o in orders],key='p5_order')
        order = next(o for o in orders if o.id==selected)
        with UnitOfWork(env.database,env.workspace) as uow:
            runs = uow.runs.list_for_order(selected)
        eligible = [r for r in runs if r.status=='succeeded' and
                    (r.brief_version_id,r.transformation_spec_version_id)==
                    (order.selected_brief_version_id,order.selected_transformation_spec_version_id)]
        if not eligible:
            st.info('A succeeded transformation with the exact selected approvals is required.')
            return
        run_id = st.selectbox('P5 succeeded Run',[r.id for r in eligible],key='p5_run')
        service = P5Service(env)
        context = service.inspect(run_id,order)
        st.write('Approved format: '+context.projection.output['format'])
        st.caption('CSV preserves lexical cells; typed null and empty text remain distinct in QA. Unsafe formulas and numeric loss fail closed.')
        if st.button('Export + deterministic QA',key='p5_complete',disabled=order.status!='EXECUTING'):
            with st.spinner('Exporting and checking all rows'):
                service.complete(run_id,order)
        with UnitOfWork(env.database,env.workspace) as uow:
            reports = uow.reports.list_for_run(run_id)
        for report in reports:
            doc = report.report_json
            if doc['overall_status']=='FAIL':
                st.error('NEEDS_FIX — diagnostic result; NOT APPROVED FOR DELIVERY')
            else:
                st.success('READY — '+doc['overall_status'])
            st.json(doc['dataset_summary'])
            st.json(doc['deterministic_checks'])
            st.json({'blocking_issues':doc['blocking_issues'],'warnings':doc['warnings']})
    except (P5Error,StorageError) as exc:
        st.error(exc.public()['code'])
