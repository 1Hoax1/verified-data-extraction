"""Executed acceptance cases P2-T01..T54; approved plan is inside the ZIP."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import zipfile
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest
from vde.bootstrap import bootstrap
from vde.config import Config
from vde.contracts import PACK, validate
from vde.errors import StorageError
from vde.persistence.uow import UnitOfWork
from vde.storage import Storage
from vde.ingestion.csv_reader import read_csv
from vde.ingestion.diagnostics import IngestionError
from vde.ingestion.local import LocalIngestion
from vde.ingestion.limits import Budget, RSS
from vde.ingestion.preview import make_preview_document, bounded
from vde.ingestion.xlsx_reader import read_xlsx, list_sheets, SafeZip
from vde.ingestion.ui import register_upload

ROOT = Path(__file__).resolve().parents[2]
PA = PACK / 'fixtures/P-A_dirty_csv'
PB = PACK / 'fixtures/P-B_xlsx_sheet'
ORDER = 'order-p2'
ASSET = 'asset-p2'


def csv(raw, **kwargs):
    return read_csv(raw, **({'asset_id': ASSET, 'encoding': 'UTF-8', 'delimiter': ',', 'header_row': 0} | kwargs))


def xlsx(pack, name, **kwargs):
    return read_xlsx((pack / 'fixtures/new_xlsx' / name).read_bytes(),
                     **({'asset_id': ASSET, 'sheet_name': 'Orders'} | kwargs))


def failure(action, code='INPUT_UNREADABLE', reason=None):
    with pytest.raises(IngestionError) as caught:
        action()
    public = caught.value.public(order_id=ORDER, source_id=ASSET)
    validate(public, 'execution_error')
    assert (public['code'], public['category'], public['stage'], public['severity']) == (code, 'INGESTION', 'INGESTION', 'BLOCKER')
    if reason:
        assert public['details']['reason'] == reason
    assert not hasattr(caught.value, 'result')
    return public


def case(pack, identity):
    record = next(c for c in json.loads((pack / 'fixtures/expected_cases.json').read_text())['cases'] if c['id'] == identity)
    result = csv((pack / 'fixtures' / record['file']).read_bytes(), encoding=record['encoding'], delimiter=record['delimiter'], header_row=record['header_row'])
    assert result.columns == record['columns'] and result.first_rows == record['rows']
    return result


def counts(env):
    with sqlite3.connect(env.database) as db:
        return {t: db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in
                ['input_assets', 'event_log', 'orders', 'brief_versions', 'transformation_spec_versions', 'execution_runs', 'approvals', 'qa_reports', 'artifacts']}


def upload(service, raw, filename='test.csv', asset_id=ASSET):
    return service.register_local_asset(ORDER, filename, raw, asset_id)


def ui(env, monkeypatch):
    monkeypatch.setenv('VDE_WORKSPACE', str(env.workspace.root))
    app = AppTest.from_file(str(ROOT / 'src/vde/app.py')).run()
    assert not app.exception
    return app


def test_T01_existing_order_ui(env, monkeypatch):
    app = ui(env, monkeypatch)
    assert app.selectbox[0].options == ['order-p2', 'order-other'] or set(app.selectbox[0].options) == {'order-p2', 'order-other'}
    assert all('create' not in b.label.lower() for b in app.button)
    assert counts(env)['orders'] == 2


def test_T02_original_storage(service, env):
    raw = (PA / 'input_dirty.csv').read_bytes()
    record = upload(service, raw)
    assert record.byte_sha256 == hashlib.sha256(raw).hexdigest() and record.size_bytes == len(raw)
    assert service.read_verified_asset(ORDER, ASSET)[0] == raw
    assert counts(env)['event_log'] == 1


def test_T03_pa_golden():
    golden = json.loads((PA / 'input_preview.json').read_text())
    assert make_preview_document(csv((PA / 'input_dirty.csv').read_bytes(), asset_id=golden['asset_id'], encoding='CP1251')) == golden


def test_T04_semicolon(pack):
    case(pack, 'SEMICOLON')


def test_T05_bom(pack):
    case(pack, 'BOM')
    raw = (pack / 'fixtures/new_csv/utf8sig.csv').read_bytes()
    assert csv(raw).columns[0] == '\ufeffcode'


def test_T06_tab(pack):
    case(pack, 'TAB')


def test_T07_logical_header(pack):
    case(pack, 'OFFSET')
    result = csv(b'"skip\nrecord"\nheader\nvalue\n', header_row=1)
    assert result.columns == ['header'] and result.first_rows == [['value']]


def test_T08_options_required(monkeypatch):
    parser = Mock(side_effect=AssertionError('decoder invoked'))
    monkeypatch.setattr('vde.ingestion.csv_reader.io.TextIOWrapper', parser)
    for options in [{'encoding': 'AUTO'}, {'encoding': None}, {'delimiter': None}]:
        failure(lambda: csv(b'a\nb\n', **options))
    parser.assert_not_called()


def test_T09_invalid_options():
    for options in [{'encoding': 'UTF-16'}, {'delimiter': '|'}, {'header_row': -1}, {'header_row': 101}, {'header_row': True}]:
        failure(lambda: csv(b'a\nb\n', **options))


def test_T10_wrong_encoding():
    failure(lambda: csv((PA / 'input_dirty.csv').read_bytes()))


def test_T11_invalid_utf8_preserved(pack, service):
    raw = (pack / 'fixtures/new_csv/invalid_utf8.csv').read_bytes()
    upload(service, raw)
    failure(lambda: service.preview_csv(ORDER, ASSET, 'UTF-8', ',', 0))
    assert service.read_verified_asset(ORDER, ASSET)[0] == raw


def test_T12_ragged(pack):
    failure(lambda: csv((pack / 'fixtures/new_csv/ragged.csv').read_bytes()))


def test_T13_quoted():
    failure(lambda: csv(b'a,b\n1,"unterminated\n'))


def test_T14_duplicate(pack):
    failure(lambda: csv((pack / 'fixtures/new_csv/duplicate_headers.csv').read_bytes()), reason='DUPLICATE_HEADER')


def test_T15_blank_header():
    for raw in [b'a,\n1,2\n', b' \nvalue\n', b'\n']:
        failure(lambda: csv(raw))


def test_T16_empty(pack, service, env):
    failure(lambda: upload(service, (pack / 'fixtures/new_csv/empty.csv').read_bytes()))
    assert counts(env)['input_assets'] == counts(env)['event_log'] == 0
    failure(lambda: csv(b''))


def test_T17_raw_size(service, env):
    spy = Mock(side_effect=AssertionError('storage registration invoked'))
    service.storage.register_input = spy
    failure(lambda: upload(service, b'X' * 100_000_001), reason='RAW_BYTE_LIMIT')
    spy.assert_not_called()
    assert counts(env)['input_assets'] == counts(env)['event_log'] == 0
    oversized = Mock(size=100_000_001, name='test.csv')
    failure(lambda: register_upload(service, ORDER, oversized))
    oversized.getvalue.assert_not_called()


def test_T18_first_five(pack):
    result = case(pack, 'MANY')
    assert result.data_row_count == 7 and len(result.first_rows) == 5


def test_T19_late_ragged(pack):
    failure(lambda: csv((pack / 'fixtures/new_csv/late_ragged.csv').read_bytes()))


def test_T20_strings(pack):
    result = case(pack, 'LITERALS')
    assert all(type(v) is str for v in result.first_rows[0])


def test_T21_literal_formula(pack):
    assert case(pack, 'LITERALS').first_rows[0][-1] == '=1+1'


def test_T22_one_column(pack):
    case(pack, 'SINGLE')
    assert csv(b'a;b\nc;d\n').columns == ['a;b']


def test_T23_sheet_order():
    sheets = list_sheets((PB / 'input_orders.xlsx').read_bytes())
    with zipfile.ZipFile(PB / 'input_orders.xlsx') as z:
        from xml.etree import ElementTree as ET
        expected = [e.get('name') for e in ET.fromstring(z.read('xl/workbook.xml')).iter() if e.tag.endswith('}sheet')]
    assert sheets == expected and 'Orders' in sheets


def test_T24_explicit_sheet(pack, env, service, monkeypatch):
    upload(service, (pack / 'fixtures/new_xlsx/multi_sheet.xlsx').read_bytes(), 'test.xlsx')
    app = ui(env, monkeypatch)
    app.selectbox[0].select(ORDER).run()
    app.selectbox[1].select(ASSET).run()
    assert app.selectbox[2].value is None
    assert any('SHEET_REQUIRED' in e.value for e in app.info)
    assert app.button[-1].disabled
    failure(lambda: xlsx(pack, 'multi_sheet.xlsx', sheet_name=None), reason='SHEET_REQUIRED')
    failure(lambda: xlsx(pack, 'multi_sheet.xlsx', sheet_name='orders'), reason='SHEET_NOT_FOUND')


def pb():
    return read_xlsx((PB / 'input_orders.xlsx').read_bytes(), asset_id='asset-pb-xlsx', sheet_name='Orders')


def test_T25_pb_golden():
    assert make_preview_document(pb()) == json.loads((PB / 'input_preview.json').read_text())


def test_T26_warning():
    result = pb()
    assert result.formula_cell_count == 4 and result.formula_sample_addresses == ['F2', 'F3', 'F4', 'F5']
    assert len(result.warnings) == 1
    validate(result.warnings[0], 'execution_error')
    assert (result.warnings[0]['code'], result.warnings[0]['severity']) == ('XLSX_FORMULA_PRESENT', 'WARNING')


def test_T27_missing_cache(pack):
    failure(lambda: xlsx(pack, 'cache_missing.xlsx'), 'XLSX_FORMULA_CACHE_MISSING', 'SELECTED_FORMULA_CACHE_ABSENT')

    # Cache checks must reach beyond the retained first five data rows.
    raw = (pack / 'fixtures/new_xlsx/cache_numeric.xlsx').read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        sheet = z.read('xl/worksheets/sheet1.xml')
    late = b''.join(f'<row r="{n}"><c r="A{n}" t="str"><v>A</v></c><c r="B{n}" t="n"><f>1+1</f>'.encode() +
                    (b'' if n == 8 else b'<v>2</v>') + b'</c></row>' for n in range(3, 9))
    raw = rewrite(raw, 'xl/worksheets/sheet1.xml', sheet.replace(b'</sheetData>', late + b'</sheetData>'))
    failure(lambda: read_xlsx(raw, asset_id=ASSET, sheet_name='Orders'), 'XLSX_FORMULA_CACHE_MISSING')


def test_T28_unselected_cache(pack):
    result = xlsx(pack, 'unselected_cache_missing.xlsx', sheet_name='Clean')
    assert result.first_rows == [['A', 1]] and result.warnings == []

    # The unselected payload is never opened, even for openpyxl dimensions.
    raw = (pack / 'fixtures/new_xlsx/unselected_cache_missing.xlsx').read_bytes()
    raw = rewrite(raw, 'xl/worksheets/sheet2.xml', b'<!DOCTYPE bad><invalid')
    assert read_xlsx(raw, asset_id=ASSET, sheet_name='Clean').first_rows == [['A', 1]]


def rewrite(raw, name, data):
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info.filename, data if info.filename == name else source.read(info))
    return out.getvalue()


def test_T29_corrupt(pack):
    for name in ['not_a_zip.xlsx', 'invalid_workbook_xml.xlsx', 'invalid_selected_sheet_xml.xlsx']:
        failure(lambda: xlsx(pack, name))
    raw = (pack / 'fixtures/new_xlsx/cache_numeric.xlsx').read_bytes()
    bad = bytearray(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        info = z.getinfo('xl/worksheets/sheet1.xml')
        offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
    bad[offset + 5] ^= 0xFF
    failure(lambda: read_xlsx(bytes(bad), asset_id=ASSET, sheet_name='Orders'))

    # Unsafe paths/types, encrypted metadata, DTD/entities and forged sizes.
    import struct
    import zlib
    import stat
    raw = (pack / 'fixtures/new_xlsx/cache_numeric.xlsx').read_bytes()
    for unsafe in ['../escape.xml', '/absolute.xml', 'xl/./workbook.xml']:
        out = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(out, 'w') as target:
            for info in source.infolist():
                target.writestr(info, source.read(info))
            target.writestr(unsafe, b'unsafe')
        failure(lambda: read_xlsx(out.getvalue(), asset_id=ASSET, sheet_name='Orders'), reason='ZIP_UNSAFE_PATH')
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(out, 'w') as target:
        for info in source.infolist():
            target.writestr(info, source.read(info))
        link = zipfile.ZipInfo('xl/link.xml')
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        target.writestr(link, b'/tmp/target')
    failure(lambda: read_xlsx(out.getvalue(), asset_id=ASSET, sheet_name='Orders'), reason='ZIP_SPECIAL_FILE')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        sheet = z.read('xl/worksheets/sheet1.xml')
    for encoding in ['utf-8', 'utf-16']:
        declaration = '<!DOCTYPE worksheet [<!ENTITY x "unsafe">]>'
        text = sheet.decode().replace('?><worksheet', '?>' + declaration + '<worksheet')
        if text == sheet.decode():
            text = declaration + sheet.decode()
        protected = rewrite(raw, 'xl/worksheets/sheet1.xml', text.encode(encoding))
        failure(lambda: read_xlsx(protected, asset_id=ASSET, sheet_name='Orders'), reason='UNSAFE_XML_DECLARATION')
    # Encrypted central-directory flag is rejected without expansion.
    encrypted = bytearray(raw)
    directory = encrypted.index(b'PK\x01\x02')
    flags = struct.unpack_from('<H', encrypted, directory + 8)[0]
    struct.pack_into('<H', encrypted, directory + 8, flags | 1)
    failure(lambda: read_xlsx(bytes(encrypted), asset_id=ASSET, sheet_name='Orders'), reason='ZIP_ENCRYPTED')
    # Forge both local/central size and CRC to match a truncated prefix.
    # Inflated byte counting must reject BEFORE ZipExtFile trims the output.
    forged = bytearray(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        info = z.getinfo('xl/worksheets/sheet1.xml')
        directory = z.start_dir
    offset = directory
    while offset < len(forged) and forged[offset:offset+4] == b'PK\x01\x02':
        name_length, extra_length, comment_length = struct.unpack_from('<HHH', forged, offset + 28)
        name = forged[offset+46:offset+46+name_length].decode()
        if name == info.filename:
            size = len(sheet) - 1
            crc = zlib.crc32(sheet[:size])
            struct.pack_into('<I', forged, offset+16, crc)
            struct.pack_into('<I', forged, offset+24, size)
            struct.pack_into('<I', forged, info.header_offset+14, crc)
            struct.pack_into('<I', forged, info.header_offset+22, size)
            break
        offset += 46 + name_length + extra_length + comment_length
    failure(lambda: read_xlsx(bytes(forged), asset_id=ASSET, sheet_name='Orders'), reason='ZIP_ACTUAL_MEMBER_LIMIT')


def guard(pack, name, reason, monkeypatch):
    inflater = Mock(side_effect=AssertionError('ZIP expansion before preflight'))
    monkeypatch.setattr(zipfile.ZipFile, 'open', inflater)
    failure(lambda: xlsx(pack, name), reason=reason)
    inflater.assert_not_called()


def test_T30_preflight(pack, monkeypatch):
    for name, reason in [('entries_over_10000.xlsx', 'ZIP_ENTRY_COUNT_LIMIT'), ('member_over_100m.xlsx', 'ZIP_MEMBER_LIMIT'),
                         ('total_over_250m.xlsx', 'ZIP_TOTAL_EXPANDED_LIMIT'), ('ratio_over_100.xlsx', 'ZIP_RATIO_LIMIT')]:
        guard(pack, name, reason, monkeypatch)


def test_T31_unsupported(service, env):
    for suffix in ['json', 'xls', 'xlsm', 'pdf']:
        failure(lambda: upload(service, b'not supported', 'input.' + suffix), 'UNSUPPORTED_FORMAT')
    assert counts(env)['input_assets'] == 0


def test_T32_single_sheet(pack):
    assert xlsx(pack, 'multi_sheet.xlsx', sheet_name='Second').first_rows == [['s2']]
    assert xlsx(pack, 'multi_sheet.xlsx', sheet_name='First').first_rows == [['s1']]


def test_T33_cross_order(service):
    upload(service, b'a\nb\n')
    service.storage.read_input = Mock(side_effect=AssertionError('foreign bytes read'))
    failure(lambda: service.read_verified_asset('order-other', ASSET), 'INPUT_NOT_FOUND')
    failure(lambda: service.read_verified_asset(ORDER, 'missing-asset'), 'INPUT_NOT_FOUND')
    service.storage.read_input.assert_not_called()


def test_T34_restart(service, env):
    upload(service, (PA / 'input_dirty.csv').read_bytes())
    before = service.preview_csv(ORDER, ASSET, 'CP1251', ',', 0)
    restarted = LocalIngestion(bootstrap(Config(env.workspace.root)))
    after = restarted.preview_csv(ORDER, ASSET, 'CP1251', ',', 0)
    assert before == after
    failure(lambda: restarted.preview_csv(ORDER, ASSET, None, None, 0))
    assert restarted.assets(ORDER)[0].byte_sha256 == before.byte_sha256


def test_T35_rerun_upload(service, env, monkeypatch):
    raw = b'a\nb\n'
    from streamlit.runtime.uploaded_file_manager import UploadedFile, UploadedFileRec
    from streamlit.proto.Common_pb2 import FileURLs
    mock_upload = UploadedFile(UploadedFileRec('upload-test', 'local.csv', 'text/csv', raw), FileURLs())
    first = register_upload(service, ORDER, mock_upload)
    app = ui(env, monkeypatch)
    app.selectbox[0].select(ORDER).run()
    app.selectbox[1].select(first.id).run()
    app.selectbox[2].select('UTF-8').run()
    app.selectbox[3].select(',').run()
    app.button[-1].click().run()
    assert not app.exception
    assert json.loads(app.json[-1].value)['first_rows'] == [['b']]
    snapshot = counts(env)
    app.run().run()
    assert counts(env) == snapshot
    second = register_upload(service, ORDER, mock_upload)
    assert first.id != second.id
    assert counts(env)['input_assets'] == counts(env)['event_log'] == 2
    assert service.read_verified_asset(ORDER, first.id)[0] == service.read_verified_asset(ORDER, second.id)[0] == raw


def test_T36_parse_retry(service, env):
    upload(service, (PA / 'input_dirty.csv').read_bytes())
    snapshot = counts(env)
    failure(lambda: service.preview_csv(ORDER, ASSET, 'UTF-8', ',', 0))
    assert service.preview_csv(ORDER, ASSET, 'CP1251', ',', 0).first_rows
    assert counts(env) == snapshot
    with UnitOfWork(env.database, env.workspace) as uow:
        assert uow.orders.get(ORDER).status == 'DRAFT'


def test_T37_public_diagnostics(pack):
    # Execute every approved CSV/XLSX case and schema-validate EVERY diagnostic.
    for record in json.loads((pack / 'fixtures/expected_cases.json').read_text())['cases']:
        if 'expected_error' in record:
            failure(lambda: csv((pack / 'fixtures' / record['file']).read_bytes()), record['expected_error'])
        else:
            case(pack, record['id'])
    for record in json.loads((pack / 'fixtures/xlsx_expected_cases.json').read_text())['cases']:
        if record['outcome'] == 'ERROR':
            failure(lambda: xlsx(pack, Path(record['file']).name, sheet_name=record['sheet']), record['code'], record['guard'] if record['guard'] in ['ZIP_ENTRY_COUNT_LIMIT', 'ZIP_MEMBER_LIMIT', 'ZIP_TOTAL_EXPANDED_LIMIT', 'ZIP_RATIO_LIMIT', 'DATA_ROW_LIMIT', 'COLUMN_LIMIT', 'PREVIEW_CELL_LIMIT'] else None)
        else:
            result = xlsx(pack, Path(record['file']).name, sheet_name=record['sheet'])
            assert result.columns == record['columns'] and result.first_rows == record['first_rows']
            for warning in result.warnings:
                validate(warning, 'execution_error')
                assert (warning['category'], warning['stage'], warning['severity']) == ('INGESTION', 'INGESTION', 'WARNING')


def test_T38_p1_faults(service, env):
    def stop(stage):
        if stage == 'metadata':
            raise StorageError('Injected metadata failure')
    failing = LocalIngestion(env, storage=Storage(env.database, env.workspace, stop))
    with pytest.raises(StorageError) as error:
        upload(failing, b'a\nb\n', asset_id='asset-fault')
    validate(error.value.public(), 'execution_error')
    assert counts(env)['input_assets'] == counts(env)['event_log'] == 0
    assert bootstrap(Config(env.workspace.root)).health == 'degraded'
    # No repair of orphan; register a separate asset in original ready test context.
    record = upload(service, b'a\nb\n')
    env.workspace.path(record.workspace_relpath).write_bytes(b'corrupt')
    with pytest.raises(StorageError) as error:
        service.preview_csv(ORDER, ASSET, 'UTF-8', ',', 0)
    public = error.value.public()
    assert (public['code'], public['category'], public['stage']) == ('STORAGE_ERROR', 'STORAGE', 'STORAGE')
    validate(public, 'execution_error')


def test_T39_p1_regression(tmp_path):
    junit = ROOT / 'docs/p2/validation/p1-results.xml'
    result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/p1', '-q', '--junitxml=' + str(junit)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    from xml.etree import ElementTree as ET
    suite = ET.parse(junit).getroot()[0]
    assert (suite.get('tests'), suite.get('failures'), suite.get('errors'), suite.get('skipped')) == ('42', '0', '0', '0')
    assert {p.get('value') for p in suite.findall('.//property') if p.get('name') == 'p1_id'} == {f'P1-T{i:02}' for i in range(1, 43)}
    result = subprocess.run(['git', 'diff', 'origin/main', '--', 'pecs/pilot_slice_v1', 'docs/p1/v1.0'], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout == ''


def test_T40_scope_dependencies(env, tmp_path):
    from scope_policy import audit_application, audit_repository_paths
    baseline_project = subprocess.check_output(['git', 'show', '129300728c446b82eaeafe1068e27339eb7176dd:pyproject.toml'], cwd=ROOT, text=True)
    baseline_lock = subprocess.check_output(['git', 'show', '129300728c446b82eaeafe1068e27339eb7176dd:uv.lock'], cwd=ROOT, text=True)
    audit_application(ROOT, baseline_project, baseline_lock)
    # CR-P3-002: owner-approved P3 start baseline; upstream governance changes
    # are not implementation changes in this branch. Original negative probes remain.
    changed = subprocess.check_output(['git', 'diff', '--name-only', 'ba73d05d2294dfb7e51b9c3c758e63c6065286d6'], cwd=ROOT, text=True).splitlines()
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=ROOT, text=True).splitlines()
    audit_repository_paths(changed + untracked)
    for path in ['worker.py', 'scripts/network_ingestion.py', 'docs/p1/v1.0/P1_TEST_PLAN.md', 'DECISIONS.md', 'tests/p1/conftest.py']:
        with pytest.raises(AssertionError, match='Unapproved repository change'):
            audit_repository_paths([path])
    old_p1_test = subprocess.check_output(['git', 'show', '129300728c446b82eaeafe1068e27339eb7176dd:tests/p1/test_p1.py'], cwd=ROOT, text=True)
    new_p1_test = (ROOT / 'tests/p1/test_p1.py').read_text()
    assert old_p1_test.split('def test_T30_p1_scope_audit')[0] == new_p1_test.split('def test_T30_p1_scope_audit')[0]
    assert old_p1_test.split('def test_T31_brief_approval_raw_guard')[1] == new_p1_test.split('def test_T31_brief_approval_raw_guard')[1]
    # Negative probes exercise the same auditor on a copied application tree;
    # the real source, deps and migrations are never modified by these probes.
    scratch = tmp_path / 'scope-negative'
    shutil.copytree(ROOT / 'src', scratch / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.egg-info'))
    for name in ['pyproject.toml', 'uv.lock']:
        shutil.copy(ROOT / name, scratch / name)
    app_path = scratch / 'src/vde/app.py'
    real_app = app_path.read_text()
    forbidden_examples = [
        'import requests', 'import httpx', 'import socket', 'import sqlalchemy',
        'import openai', 'import telegram', 'import playwright', 'import celery',
        'import fastapi', 'import pandas', 'from urllib.request import urlopen',
        'import importlib; importlib.import_module("requests")',
        '__import__("requests")', 'exec("pass")', 'eval("1+1")',
        'import subprocess; subprocess.run(["echo", "code"])',
        'def ingest_json(raw): return raw', 'def approve_order(): return None',
        'uow.orders.add(record)', 'uow.specs.append(record)', 'uow.approvals.append(record)',
        'uow.runs.append(record)', 'uow.qa.append(record)', 'workbook.save("output.xlsx")',
    ]
    for snippet in forbidden_examples:
        app_path.write_text(real_app + '\n' + snippet + '\n')
        with pytest.raises(AssertionError, match='Unapproved'):
            audit_application(scratch, baseline_project, baseline_lock)
    app_path.write_text(real_app)
    for path in ['src/vde/engine.py', 'src/vde/ingestion/url_reader.py', 'src/vde/order_create.py',
                 'src/vde/persistence/migrations/002_p2.sql']:
        target = scratch / path
        target.write_text('# unapproved source' if path.endswith('.py') else 'CREATE TABLE dataset_rows (id INTEGER);')
        with pytest.raises(AssertionError, match='Unapproved'):
            audit_application(scratch, baseline_project, baseline_lock)
        target.unlink()
    migration = scratch / 'src/vde/persistence/migrations/001_p1_baseline.sql'
    original = migration.read_text()
    migration.write_text(original + '\nCREATE TABLE dataset_rows (id INTEGER);\n')
    with pytest.raises(AssertionError, match='drift'):
        audit_application(scratch, baseline_project, baseline_lock)
    migration.write_text(original)
    project_path = scratch / 'pyproject.toml'
    original = project_path.read_text()
    for modified in [original.replace('"openpyxl==3.1.5"', '"openpyxl==3.1.5", "requests==2.32.3"'),
                     original.replace('"pytest==8.4.2"', '"pytest==8.4.2", "telegram==0.0.1"'),
                     original.replace('"setuptools>=77"', '"setuptools>=77", "sqlalchemy==2.0.0"')]:
        project_path.write_text(modified)
        with pytest.raises(AssertionError, match='Unapproved'):
            audit_application(scratch, baseline_project, baseline_lock)
    project_path.write_text(original)
    lock_path = scratch / 'uv.lock'
    original = lock_path.read_text()
    lock_path.write_text(original.replace('name = "openpyxl"\nversion = "3.1.5"', 'name = "openpyxl"\nversion = "3.1.4"'))
    with pytest.raises(AssertionError, match='Unapproved'):
        audit_application(scratch, baseline_project, baseline_lock)
    lock_path.write_text(original)
    audit_application(scratch, baseline_project, baseline_lock)
    assert all(counts(env)[t] == 0 for t in ['brief_versions', 'transformation_spec_versions', 'execution_runs', 'approvals', 'qa_reports', 'artifacts'])


def test_T41_header_rules(pack):
    for name in ['row1_blank.xlsx', 'header_merged.xlsx', 'header_duplicate.xlsx']:
        failure(lambda: xlsx(pack, name))


def test_T42_empty_cache(pack):
    result = xlsx(pack, 'cache_explicit_empty.xlsx')
    assert result.first_rows == [['A', '']] and len(result.warnings) == 1
    assert result.warnings[0]['code'] == 'XLSX_FORMULA_PRESENT'


def test_T43_cache_presence(pack):
    from xml.etree import ElementTree as ET
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    for name, present in [('cache_explicit_empty.xlsx', True), ('cache_missing.xlsx', False)]:
        with zipfile.ZipFile(pack / 'fixtures/new_xlsx' / name) as z:
            cell = next(c for c in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).iter(ns + 'c') if c.get('r') == 'B2')
            assert (cell.find(ns + 'v') is not None) is present
    test_T42_empty_cache(pack)
    test_T27_missing_cache(pack)


def test_T44_entries(pack, monkeypatch):
    guard(pack, 'entries_over_10000.xlsx', 'ZIP_ENTRY_COUNT_LIMIT', monkeypatch)


def test_T45_member(pack, monkeypatch):
    guard(pack, 'member_over_100m.xlsx', 'ZIP_MEMBER_LIMIT', monkeypatch)


def test_T46_total(pack, monkeypatch):
    guard(pack, 'total_over_250m.xlsx', 'ZIP_TOTAL_EXPANDED_LIMIT', monkeypatch)


def test_T47_ratio(pack, monkeypatch):
    guard(pack, 'ratio_over_100.xlsx', 'ZIP_RATIO_LIMIT', monkeypatch)


def test_T48_header_only(pack):
    for result in [xlsx(pack, 'header_only.xlsx'), csv(b'id,name\n')]:
        assert result.data_row_count == 0 and result.first_rows == []
        assert 'qa' not in make_preview_document(result)


def test_T49_typed(pack):
    record = next(c for c in json.loads((pack / 'fixtures/xlsx_expected_cases.json').read_text())['cases'] if c['file'].endswith('typed_cells.xlsx'))
    assert xlsx(pack, 'typed_cells.xlsx').first_rows == record['first_rows']
    raw = (pack / 'fixtures/new_xlsx/typed_cells.xlsx').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == record['sha256']


def test_T50_error_cache(pack):
    result = xlsx(pack, 'error_formula_cache.xlsx')
    assert result.first_rows == [['A', {'kind': 'excel_error', 'value': '#DIV/0!'}]]
    assert len(result.warnings) == result.formula_cell_count == 1


def test_T51_health(service, env):
    record = upload(service, b'a\nb\n')
    env.workspace.path('.staging/incomplete').write_bytes(b'incomplete')
    degraded = bootstrap(Config(env.workspace.root))
    assert degraded.health == 'degraded'
    before = counts(env)
    for permit in [False, True]:
        reader = LocalIngestion(degraded, allow_degraded_read=permit)
        with pytest.raises(StorageError):
            upload(reader, b'a\nb\n', asset_id='asset-other')
        if permit:
            assert reader.preview_csv(ORDER, ASSET, 'UTF-8', ',', 0).first_rows == [['b']]
        else:
            with pytest.raises(StorageError):
                reader.preview_csv(ORDER, ASSET, 'UTF-8', ',', 0)
    assert counts(env) == before and env.workspace.path('.staging/incomplete').exists()
    env.workspace.path(record.workspace_relpath).write_bytes(b'damaged')
    blocked = bootstrap(Config(env.workspace.root))
    assert blocked.health == 'blocked'
    for action in [lambda: LocalIngestion(blocked, allow_degraded_read=True).preview_csv(ORDER, ASSET, 'UTF-8', ',', 0),
                   lambda: upload(LocalIngestion(blocked), b'a\nb\n')]:
        with pytest.raises(StorageError) as error:
            action()
        validate(error.value.public(), 'execution_error')


def test_T52_scan_caps(pack):
    for name, reason in [('rows_over_100000.xlsx', 'DATA_ROW_LIMIT'), ('columns_over_200.xlsx', 'COLUMN_LIMIT')]:
        raw = (pack / 'fixtures/new_xlsx' / name).read_bytes()
        with SafeZip(raw, Budget()):
            pass
        failure(lambda: xlsx(pack, name), reason=reason)
    failure(lambda: csv(b'a\n' + b'x\n' * 100001), reason='DATA_ROW_LIMIT')
    failure(lambda: csv((','.join('H' + str(i) for i in range(201)) + '\n').encode()), reason='COLUMN_LIMIT')


def test_T53_preview_limits(pack):
    from xml.etree import ElementTree as ET
    raw = (pack / 'fixtures/new_xlsx/preview_cell_over_65536.xlsx').read_bytes()
    with SafeZip(raw, Budget()):
        pass
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        cell = next(c for c in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).iter() if c.tag.endswith('}c') and c.get('r') == 'B2')
        assert len(''.join(cell.itertext())) == 65537
    failure(lambda: xlsx(pack, 'preview_cell_over_65536.xlsx'), reason='PREVIEW_CELL_LIMIT')
    failure(lambda: bounded(['a'], [['x' * 65537]], []), reason='PREVIEW_CELL_LIMIT')
    failure(lambda: bounded(['a'] * 200, [['x' * 60000] * 200] * 5, []), reason='PREVIEW_JSON_LIMIT')
    assert len(json.dumps(make_preview_document(pb())).encode()) < 1_048_576


def test_T54_rss_and_fixtures(pack, tmp_path, monkeypatch):
    # Actual sampled-guard rejection, without a dangerous giant allocation.
    with monkeypatch.context() as patch:
        samples = iter([1000, 1000 + RSS + 1])
        patch.setattr('vde.ingestion.limits.current_rss', lambda: next(samples))
        failure(lambda: csv(b'a\nb\n'), reason='RUNTIME_RSS_LIMIT')
    # Generator must reproduce binary bytes in a NEW temp directory.
    regenerated = tmp_path / 'regenerated'
    regenerated.mkdir()
    shutil.copy(pack / 'fixtures/build_xlsx_fixtures.py', regenerated)
    proc = subprocess.run([sys.executable, str(regenerated / 'build_xlsx_fixtures.py')], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert len(list((regenerated / 'new_xlsx').glob('*.xlsx'))) == 21
    for original in (pack / 'fixtures/new_xlsx').glob('*.xlsx'):
        assert original.read_bytes() == (regenerated / 'new_xlsx' / original.name).read_bytes()
    evidence = {
        'tested_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'archive_sha256': hashlib.sha256((ROOT / 'docs/p2/v1.0/P2_Implementation_Pack_v1.0_APPROVED.zip').read_bytes()).hexdigest(),
        'manifest_entries_verified': 57, 'csv_fixtures_verified': 12, 'xlsx_regenerated_byte_identical': 21,
        'generator_command_argv': [sys.executable, str(regenerated / 'build_xlsx_fixtures.py')],
        'generator_stdout': proc.stdout.strip(),
        'csv_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((pack / 'fixtures/new_csv').glob('*.csv'))},
        'xlsx_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((regenerated / 'new_xlsx').glob('*.xlsx'))},
    }
    (ROOT / 'docs/p2/validation/fixture-verification.json').write_text(json.dumps(evidence, indent=2) + '\n')
    for kind in ['csv', 'xlsx']:
        output = ROOT / f'docs/p2/validation/rss-{kind}.json'
        proc = subprocess.run([sys.executable, str(ROOT / 'tests/p2/rss_probe.py'), str(pack), str(tmp_path / kind), kind], capture_output=True, text=True, cwd=ROOT)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        output.write_text(proc.stdout)
        measurements = json.loads(proc.stdout)
        assert measurements['incremental_peak_bytes'] <= RSS
        assert measurements['data_row_count'] == 100000 and measurements['first_rows_count'] == 5
        assert measurements['upload_buffer_included'] and not measurements['dataset_handle']
