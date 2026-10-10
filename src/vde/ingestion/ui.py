"""Upload and preview panel for P1-created Orders; actions alone can write."""
from uuid import uuid4
import streamlit as st
from vde.errors import StorageError
from .diagnostics import IngestionError
from .local import LocalIngestion, source_type
from .preview import make_preview_document
from .limits import RAW, Budget, raw_check


def register_upload(service, order_id, upload):
    """Validate uploader size before making its whole-byte copy."""
    from .diagnostics import require
    require(upload.size <= RAW and upload.size > 0, 'RAW_BYTE_LIMIT')
    source_type(upload.name)
    budget = Budget()
    raw = upload.getvalue()
    raw_check(raw)
    budget.check()
    result = service.register_local_asset(order_id, upload.name, raw, str(uuid4()))
    budget.check()
    return result


def panel(env):
    if env.health == 'blocked':
        return
    explicit_read = env.health == 'ready' or st.checkbox('Allow read-only preview of existing verified input')
    if not explicit_read:
        return
    service = LocalIngestion(env, allow_degraded_read=env.health == 'degraded')
    order_id = asset_id = None
    try:
        orders = service.orders()
        if not orders:
            st.info('No existing Orders. Prepare an Order using the P1 repository setup before uploading input.')
            return
        order_id = st.selectbox('Existing Order', [o.id for o in orders],
                                format_func=lambda identity: next(o.title for o in orders if o.id == identity))
        upload = st.file_uploader('Local CSV or XLSX', type=['csv', 'xlsx'], accept_multiple_files=False,
                                  disabled=env.health != 'ready')
        if st.button('Upload', disabled=env.health != 'ready' or upload is None):
            record = register_upload(service, order_id, upload)
            st.success(f'Input registered: {record.id}')
        assets = service.assets(order_id)
        if not assets:
            st.info('Upload one local file to preview it.')
            return
        asset_id = st.selectbox('Registered input', [a.id for a in assets], index=None,
                                format_func=lambda identity: next(a.original_filename + ' (' + a.id + ')' for a in assets if a.id == identity))
        if asset_id is None:
            return
        record = next(a for a in assets if a.id == asset_id)
        if source_type(record.original_filename) == 'LOCAL_CSV':
            encoding = st.selectbox('Encoding', ['UTF-8', 'UTF-8-SIG', 'CP1251'], index=None)
            delimiter = st.selectbox('Delimiter', [',', ';', '\t'], index=None,
                                     format_func=lambda value: {',': 'Comma', ';': 'Semicolon', '\t': 'Tab'}[value])
            header = st.number_input('Header row (zero-based logical record)', min_value=0, max_value=100, value=0)
            if st.button('Preview', disabled=encoding is None or delimiter is None):
                read = service.preview_csv(order_id, asset_id, encoding, delimiter, header)
                st.json(make_preview_document(read))
                st.caption(f'{read.data_row_count} data rows scanned; preview is not a QA verdict.')
        else:
            sheet = st.selectbox('Worksheet', service.list_xlsx_sheets(order_id, asset_id), index=None)
            if sheet is None:
                st.info('SHEET_REQUIRED: explicitly select one worksheet.')
            if st.button('Preview', disabled=sheet is None):
                read = service.preview_xlsx(order_id, asset_id, sheet)
                st.json(make_preview_document(read))
                for warning in read.warnings:
                    st.warning(warning['code'])
                    st.json(warning)
                st.caption(f'{read.data_row_count} data rows scanned; preview is not a QA verdict.')
    except IngestionError as exc:
        st.error(exc.code)
        st.json(exc.public(order_id=order_id, source_id=asset_id))
    except StorageError as exc:
        st.error('STORAGE_ERROR')
        st.json(exc.public())
