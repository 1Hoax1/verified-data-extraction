"""Executable P4 acceptance oracles; no fixture rewrites or skipped scenarios."""
import hashlib
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import io
import zipfile

import pytest
from vde.bootstrap import bootstrap
from vde.config import Config
from vde.contracts import validate
from vde.errors import StorageError
from vde.persistence.repositories import EventLogRepository
from vde.workflow.errors import WorkflowError
from vde.execution.errors import ExecutionError
from vde.execution.preflight import verify_and_plan
from vde.execution.engine import apply
from vde.execution.source_adapter import iter_verified_rows, Source, Row
from vde.execution.budget import Budget
from vde.execution.wire import encode_cell, decode_cell, row_bytes

from vde.execution.service import ExecutionService
from vde.execution.wire import iter_payload
from .support import (Approved, ROOT, load, operation, fixture_cases, assert_rejection,
                      fields_for_stress, stress_pipeline, evidence)


def test_T01_approved_csv_vertical(tmp_path):
    a = Approved(tmp_path)
    service = ExecutionService(a.env)
    active = service.start(a.order_id, a.order(), a.handoff)
    assert active.run.status == 'running'
    assert a.order().status == 'EXECUTING' and a.order().approval_stage == 'COMPLETE'
    assert a.counts() == a.before | {'execution_runs': 1, 'event_log': a.before['event_log']+1}
    result = service.finish(active)
    assert result.row_count == 3
    handle, payload = service.read_result(result.run_id)
    rows = list(iter_payload(payload, expected_columns=handle.columns, dataset_id='result'))
    assert [r[0] for r in rows] == ['Алиса Смит', 'Bob Jones', 'Carla Ruiz']
    assert handle.checksum == hashlib.sha256(payload).hexdigest()
    assert a.env.workspace.read_verified(a.asset.workspace_relpath, a.asset.byte_sha256) == a.raw
    with a.uow() as uow:
        run = uow.runs.get(result.run_id)
        assert run.status == 'succeeded' and len(run.metrics_json['operation_audit']) == 14
        assert uow.orders.get(a.order_id).status == 'EXECUTING'


def test_T02_missing_brief_approval(tmp_path, monkeypatch):
    a = Approved(tmp_path)
    assert_rejection(a, replace(a.handoff, brief_approval_id=''), 'APPROVAL_MISSING', monkeypatch)
    evidence('x-fixture', 'P4-X01', {'result': 'PASS', 'admission_no_writes_or_io': True})


def test_T03_missing_spec_approval(tmp_path, monkeypatch):
    a = Approved(tmp_path)
    assert_rejection(a, replace(a.handoff, transformation_approval_id=''), 'APPROVAL_MISSING', monkeypatch)


def test_T04_brief_hash_mismatch(tmp_path, monkeypatch):
    a = Approved(tmp_path)
    assert_rejection(a, replace(a.handoff, brief_content_hash='0'*64), 'APPROVAL_HASH_MISMATCH', monkeypatch)
    evidence('x-fixture', 'P4-X02', {'result': 'PASS', 'admission_no_writes_or_io': True})


def test_T05_spec_hash_and_brief_context(tmp_path, monkeypatch):
    a = Approved(tmp_path)
    assert_rejection(a, replace(a.handoff, transformation_content_hash='0'*64), 'APPROVAL_HASH_MISMATCH', monkeypatch)
    assert_rejection(a, replace(a.handoff, brief_version_id='foreign-brief'), 'VERSION_INCOMPATIBLE', monkeypatch)
    for identity in ('P4-X03', 'P4-X04'):
        evidence('x-fixture', identity, {'result': 'PASS', 'admission_no_writes_or_io': True})


def test_T06_wrong_order_and_selected_versions(tmp_path, monkeypatch):
    a = Approved(tmp_path)
    for patch in ({'order_id': 'foreign-order'}, {'brief_version_id': 'foreign-brief'},
                  {'transformation_spec_version_id': 'foreign-spec'}):
        assert_rejection(a, replace(a.handoff, **patch), 'VERSION_INCOMPATIBLE', monkeypatch)


def test_T07_stale_approval_and_hash(tmp_path, monkeypatch):
    a = Approved(tmp_path)
    assert_rejection(a, replace(a.handoff, brief_approval_id=a.handoff.transformation_approval_id), 'APPROVAL_MISSING', monkeypatch)
    assert_rejection(a, replace(a.handoff, transformation_content_hash='f'*64), 'APPROVAL_HASH_MISMATCH', monkeypatch)


def test_T08_incomplete_order(tmp_path, monkeypatch):
    a = Approved(tmp_path, approve_final=False)
    assert (a.order().status, a.order().approval_stage) == ('READY_FOR_APPROVAL', 'TRANSFORMATION_PENDING')
    assert_rejection(a, a.handoff, 'STATE_INVALID_TRANSITION', monkeypatch)


def test_T09_stale_order_cas(tmp_path, monkeypatch):
    a = Approved(tmp_path)
    old = a.order()
    with a.uow() as uow:
        uow.orders.update(replace(old, status='CANCELLED'), expected=old)
    assert_rejection(a, a.handoff, 'STATE_INVALID_TRANSITION', monkeypatch, expected_order=old)
    assert a.order().status == 'CANCELLED'


def test_T10_fresh_process_handoff(tmp_path):
    a = Approved(tmp_path)
    proc = subprocess.run([sys.executable, '-m', 'p4.restart_probe', str(a.env.workspace.root), 'handoff'],
                          cwd=ROOT, capture_output=True, text=True, env=child_environment())
    assert proc.returncode == 0, proc.stderr
    from dataclasses import asdict
    assert json.loads(proc.stdout) == asdict(a.handoff)
    active = ExecutionService(a.env).start(a.order_id, a.order(), a.handoff)
    assert a.counts()['execution_runs'] == 1 and a.counts()['event_log'] == a.before['event_log']+1
    active.source.close()


def test_T11_missing_column_and_unknown_operation_preflight(tmp_path, p4_pack, monkeypatch):
    a = Approved(tmp_path, pipeline=[operation('drop_missing', {'subset': ['absent'], 'how': 'any'})])
    before = a.snapshot()
    with pytest.raises(ExecutionError) as caught:
        ExecutionService(a.env).start(a.order_id, a.order(), a.handoff)
    assert caught.value.code == 'COLUMN_NOT_FOUND' and a.snapshot() == before
    fixture_cases(p4_pack, [30, 31], tmp_path)


def test_T12_full_csv_scan(tmp_path, p4_pack):
    path = generate_stress(p4_pack, tmp_path)
    a = Approved(tmp_path/'approved', raw=path.read_bytes(), fields=fields_for_stress(),
                 pipeline=stress_pipeline(), csv_options={'encoding': 'UTF-8', 'delimiter': ',', 'header_row': 0})
    with a.uow() as uow:
        plan = verify_and_plan(uow, a.order_id, uow.orders.get(a.order_id), a.handoff)
    source = iter_verified_rows(a.env, plan, Budget())
    assert len(source.columns) == 200
    count, first, last = 0, None, None
    for row in source.rows:
        r = count
        assert row.values == (f'{37*r%100000:05d}', f'{r%90000:05d}') + ('0',)*198
        first, last = first or row, row
        count += 1
    assert count == 100000 and first.source == 1 and last.source == 100000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == a.asset.byte_sha256


def test_T13_full_xlsx_source_per_CR_P4_002(tmp_path):
    a = Approved(tmp_path, 'P-B_xlsx_sheet')
    with a.uow() as uow:
        plan = verify_and_plan(uow, a.order_id, uow.orders.get(a.order_id), a.handoff)
    source = iter_verified_rows(a.env, plan, Budget())
    rows = [row.values for row in source.rows]
    expected = load(ROOT/'pecs/pilot_slice_v1/fixtures/P-B_xlsx_sheet/input_preview.json')
    assert list(source.columns) == expected['columns'] and len(rows) == 4
    assert rows == [tuple(Decimal(str(v)) if type(v) is float else v for v in row) for row in expected['first_rows']]
    assert source.warnings == [{'code': 'XLSX_FORMULA_PRESENT', 'severity': 'WARNING', 'source_id': a.asset_id,
                                'affected_count': 4, 'sample_cells': ['F2', 'F3', 'F4', 'F5']}]
    assert a.env.workspace.path(a.asset.workspace_relpath).read_bytes() == a.raw


def test_T14_approved_selection_mismatch(tmp_path, monkeypatch):
    a = Approved(tmp_path)
    for changed in ({'encoding': 'UTF-8'}, {'delimiter': ';'}):
        selected = deepcopy(a.handoff.input_selection)
        selected['csv_options'].update(changed)
        assert_rejection(a, replace(a.handoff, input_selection=selected), 'VALIDATION_TRANSFORMATION_SCHEMA', monkeypatch)


def test_T15_xlsx_cache_and_bad_zip(tmp_path):
    a = Approved(tmp_path, 'P-B_xlsx_sheet')
    data = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(a.raw)) as original, zipfile.ZipFile(data, 'w', zipfile.ZIP_STORED) as changed:
        for entry in original.infolist():
            raw = original.read(entry.filename)
            if entry.filename == 'xl/worksheets/sheet1.xml':
                from xml.etree import ElementTree as ET
                tree = ET.fromstring(raw)
                ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
                cell = next(c for c in tree.iter(ns+'c') if c.find(ns+'f') is not None)
                cell.remove(cell.find(ns+'v'))
                raw = ET.tostring(tree)
            changed.writestr(entry.filename, raw)
    for number, raw, code in ((1, data.getvalue(), 'XLSX_FORMULA_CACHE_MISSING'), (2, b'not a zip', 'INPUT_UNREADABLE')):
        from vde.storage import Storage
        asset = Storage(a.env.database, a.env.workspace).register_input(id='invalid-'+str(number), order_id=a.order_id,
                                                original_filename='invalid.xlsx', data=raw)
        with pytest.raises(ExecutionError) as caught:
            stream = iter_verified_rows(a.env, SimpleNamespace(asset=asset, handoff=a.handoff), Budget())
            list(stream.rows)
        assert caught.value.code == code
    assert a.counts()['artifacts'] == 0


def test_T16_closed_parameters_and_chain(tmp_path):
    a = Approved(tmp_path)
    with a.uow() as uow:
        spec = deepcopy(uow.specs.get(a.handoff.transformation_spec_version_id).document_json)
        context = (uow.briefs.get(a.handoff.brief_version_id), uow.approvals.get(a.handoff.brief_approval_id))
    for key, value, code, xid in [('type', 'filter', 'INVALID_OPERATION', 'P4-X11'),
                                   ('params', {'unapproved': True}, 'INVALID_PARAMETER', 'P4-X12')]:
        changed = deepcopy(spec)
        changed['pipeline'][0][key] = value
        before = a.snapshot()
        with pytest.raises(WorkflowError) as caught:
            a.workflow.validate_spec(changed, a.order(), context, a.selection)
        assert caught.value.code == code and a.snapshot() == before
        evidence('x-fixture', xid, {'result': 'PASS', 'preapproval_rejection': code, 'no_p4_writes': True})


def test_T17_select(p4_pack, tmp_path):
    fixture_cases(p4_pack, [1, 2], tmp_path)


def test_T18_drop(p4_pack, tmp_path):
    fixture_cases(p4_pack, [3, 4, 5], tmp_path)


def test_T19_rename(p4_pack, tmp_path):
    fixture_cases(p4_pack, [6, 7], tmp_path)


def test_T20_trim_and_unicode(p4_pack, tmp_path):
    fixture_cases(p4_pack, [8, 9, 33], tmp_path)
    table = apply(SimpleNamespace(pipeline=[operation('trim', {'columns': ['s'], 'mode': 'both'})]),
                  Source(('s', 'untouched'), iter([Row(1, (' e\u0301 ', 'e\u0301')), Row(2, (' é ', 'é'))]), []), Budget(), tmp_path)
    assert [r.values for r in table.rows] == [('e\u0301', 'e\u0301'), ('é', 'é')]
    raw = 'c000\n e\u0301 \n é \n'.encode('utf-8')
    a = Approved(tmp_path/'unicode-csv', raw=raw, fields=fields_for_stress(1),
                 pipeline=[operation('trim', {'columns': ['c000'], 'mode': 'both'})],
                 csv_options={'encoding': 'UTF-8', 'delimiter': ',', 'header_row': 0})
    service = ExecutionService(a.env)
    result = service.execute(a.order_id, a.order(), a.handoff)
    _, payload = service.read_result(result.run_id)
    assert list(iter_payload(payload)) == [('e\u0301',), ('é',)]
    assert a.env.workspace.path(a.asset.workspace_relpath).read_bytes() == raw


def test_T21_case(p4_pack, tmp_path):
    fixture_cases(p4_pack, [10, 11], tmp_path)


def test_T22_literal_replace(p4_pack, tmp_path):
    fixture_cases(p4_pack, [12, 13], tmp_path)


def test_T23_date(p4_pack, tmp_path):
    fixture_cases(p4_pack, [14], tmp_path)


def test_T24_date_fail_and_null(p4_pack, tmp_path):
    fixture_cases(p4_pack, [15, 16], tmp_path)


def test_T25_exact_number_and_signed64(p4_pack, tmp_path):
    fixture_cases(p4_pack, [17, 18], tmp_path)
    catalog = load(p4_pack/'fixtures/internal_scalar_precision_cases.json')['cases']
    for case in catalog[:13]:
        p = operation('parse_number', {'column': 'value', 'decimal_separator': '.', 'thousands_separator': None,
                                      'target_type': 'integer', 'errors': 'FAIL'})
        table = apply(SimpleNamespace(pipeline=[p]), Source(('value',), iter([Row(1, (case['source_text'],))]), []), Budget(), tmp_path)
        actual = next(table.rows).values[0]
        assert type(actual) is int and actual == int(case['source_text'])
        assert encode_cell(actual) == case['wire_payload']['rows'][0][0]
        assert decode_cell(encode_cell(actual), expected_type='integer') == actual
        evidence('w-fixture', case['id'], {'result': 'PASS', 'runtime_type': 'int', 'exact_wire_tag': encode_cell(actual)})
    for case in load(ROOT/'tests/p4/fixtures/decimal_fraction_cases.json')['valid']:
        op = operation('parse_number', {'column': 'value', 'decimal_separator': '.', 'thousands_separator': None,
                                       'target_type': 'decimal', 'errors': 'FAIL'})
        table = apply(SimpleNamespace(pipeline=[op]), Source(('value',), iter([Row(1, (case['source_text'],))]), []), Budget(), tmp_path)
        actual = next(table.rows).values[0]
        assert type(actual) is Decimal and actual == Decimal(case['source_text'])
        assert encode_cell(actual) == {'type': 'decimal', 'value': case['wire']}
        assert decode_cell(encode_cell(actual)) == actual


def test_T26_number_failure_overflow(p4_pack, tmp_path):
    fixture_cases(p4_pack, [19, 20], tmp_path)
    for case in load(p4_pack/'fixtures/internal_scalar_precision_cases.json')['cases'][41:]:
        op = operation('parse_number', {'column': 'value', 'decimal_separator': '.', 'thousands_separator': None,
                                       'target_type': 'integer', 'errors': case['errors']})
        table = apply(SimpleNamespace(pipeline=[op]), Source(('value',), iter([Row(1, (case['source_text'],))]), []), Budget(), tmp_path)
        if case['errors'] == 'FAIL':
            with pytest.raises(ExecutionError) as caught:
                list(table.rows)
            assert caught.value.code == 'PARSE_FAILED' and caught.value.row_id == 1
        else:
            assert [r.values for r in table.rows] == [(None,)] and table.audit[0]['parse_failed_count'] == 1
        evidence('w-fixture', case['id'], {'result': 'PASS', 'actual_errors_policy': case['errors']})
    runtime_failure(tmp_path/'X10', 'P4-X10', 'PARSE_FAILED')


def test_T27_fill(p4_pack, tmp_path):
    fixture_cases(p4_pack, [21, 34], tmp_path)


def test_T28_drop_missing(p4_pack, tmp_path):
    fixture_cases(p4_pack, [22, 23, 29], tmp_path)


def test_T29_sort(p4_pack, tmp_path):
    fixture_cases(p4_pack, [24, 25], tmp_path)


def test_T30_deduplicate(p4_pack, tmp_path):
    fixture_cases(p4_pack, [26, 27, 28], tmp_path)


def test_T31_zero_columns(p4_pack, tmp_path):
    fixture_cases(p4_pack, [35], tmp_path)


def test_T32_mixed_sort(p4_pack, tmp_path):
    fixture_cases(p4_pack, [36], tmp_path)


def test_T33_null_dedup(p4_pack, tmp_path):
    fixture_cases(p4_pack, [37], tmp_path)


def test_T34_non_string_trim(p4_pack, tmp_path):
    fixture_cases(p4_pack, [38], tmp_path)


def test_T35_pipeline_order(tmp_path):
    sort = operation('sort', {'by': ['priority'], 'ascending': [True], 'nulls': 'LAST'})
    dedup = operation('deduplicate', {'subset': ['key'], 'keep': 'FIRST'})
    outputs = []
    for ops in ([sort, dedup], [dedup, sort]):
        source = Source(('key', 'priority'), iter([Row(1, ('A', 2)), Row(2, ('A', 1)), Row(3, ('B', 3))]), [])
        outputs.append([r.values for r in apply(SimpleNamespace(pipeline=ops), source, Budget(), tmp_path).rows])
    assert outputs == [[('A', 1), ('B', 3)], [('A', 2), ('B', 3)]]


def test_T36_branch_cycle_reuse_rejected(tmp_path):
    a = Approved(tmp_path)
    with a.uow() as uow:
        spec = deepcopy(uow.specs.get(a.handoff.transformation_spec_version_id).document_json)
        context = (uow.briefs.get(a.handoff.brief_version_id), uow.approvals.get(a.handoff.brief_approval_id))
    for index, key, value in [(1, 'input_dataset', 'raw'), (1, 'output_dataset', 's01'), (2, 'output_dataset', 'raw')]:
        changed = deepcopy(spec)
        changed['pipeline'][index][key] = value
        with pytest.raises(WorkflowError) as caught:
            a.workflow.validate_spec(changed, a.order(), context, a.selection)
        assert caught.value.code == 'VALIDATION_TRANSFORMATION_SCHEMA'
    assert a.counts() == a.before


def test_T37_missing_columns_and_failed_state(p4_pack, tmp_path):
    fixture_cases(p4_pack, [2, 5, 30], tmp_path)
    runtime_failure(tmp_path/'X07', 'P4-X07', 'COLUMN_NOT_FOUND')
    runtime_failure(tmp_path/'X08', 'P4-X08', 'COLUMN_COLLISION')


def test_T38_sort_semantic_invariant(p4_pack, tmp_path):
    case = load(p4_pack/'fixtures/operation_cases.json')['cases'][31]
    validate(case['pipeline'][0], 'sort')
    fixture_cases(p4_pack, [32], tmp_path)


def test_T39_schema_parameters(p4_pack, tmp_path):
    fixture_cases(p4_pack, [13], tmp_path)
    from vde.execution.operations import plan_columns
    with pytest.raises(ExecutionError) as caught:
        plan_columns(('n',), operation('parse_number', {'column': 'n', 'decimal_separator': '.',
                        'thousands_separator': '.', 'target_type': 'integer', 'errors': 'FAIL'}))
    assert caught.value.code == 'INVALID_PARAMETER'


def test_T40_full_shape_limits(tmp_path, p4_pack):
    for rows, cols, code in ((100000, 200, None), (100001, 200, 'SCHEMA_MISMATCH'), (100000, 201, 'SCHEMA_MISMATCH')):
        raw = generate_stress(p4_pack, tmp_path, rows, cols).read_bytes()
        if code is None:
            source, env, asset = raw_source(tmp_path/f'case-{rows}-{cols}', raw)
            assert sum(1 for _ in source.rows) == rows
            assert len(source.columns) == cols
            assert env.workspace.inspect(asset.workspace_relpath)[1] == hashlib.sha256(raw).hexdigest()
        else:
            with pytest.raises(ExecutionError) as caught:
                source, _, _ = raw_source(tmp_path/f'case-{rows}-{cols}', raw)
                list(source.rows)
            assert caught.value.code == code


def test_T41_p0_csv_golden(tmp_path, p4_pack):
    check_golden(tmp_path, p4_pack, 'P-A_dirty_csv', 'P-A')


def test_T42_p0_xlsx_golden(tmp_path, p4_pack):
    check_golden(tmp_path, p4_pack, 'P-B_xlsx_sheet', 'P-B')


def test_T43_p0_semantic_errors(tmp_path):
    root = ROOT/'pecs/pilot_slice_v1/fixtures/P-D_errors_and_qa_blockers'
    cases = load(root/'semantic_error_cases.json')['cases']
    assert len(cases) == 3
    for index, case in enumerate(cases):
        document = load(root/case['path'])
        validate(document, 'transformation_spec_version')
        a = Approved(tmp_path/f'p0-case-{index}', 'P-D_errors_and_qa_blockers', pipeline=document['pipeline'])
        with pytest.raises(ExecutionError) as caught:
            ExecutionService(a.env).execute(a.order_id, a.order(), a.handoff)
        assert caught.value.code == case['expected_error'] and a.counts()['artifacts'] == 0
        if 'row_id' in case:
            assert str(caught.value.row_id) == case['row_id'] and caught.value.value == case['value']
            assert a.order().status == 'FAILED'
        else:
            assert a.counts() == a.before and a.order().status == 'APPROVED'
        evidence('p0-semantic', case['path'], {'result':'PASS', 'actual_error':caught.value.code})
    runtime_failure(tmp_path/'missing', 'P4-X07', 'COLUMN_NOT_FOUND')
    runtime_failure(tmp_path/'collision', 'P4-X08', 'COLUMN_COLLISION')
    error = runtime_failure(tmp_path/'date', 'P4-X09', 'PARSE_FAILED')
    assert error.row_id == 2 and error.value == 'bad-date'


def test_T44_start_atomicity(tmp_path, monkeypatch):
    a = Approved(tmp_path)
    before = a.snapshot()
    with monkeypatch.context() as patch:
        def failure(*args, **kwargs):
            raise StorageError('Injected start EventLog failure')
        patch.setattr(EventLogRepository, 'append', failure)
        with pytest.raises(StorageError):
            ExecutionService(a.env).start(a.order_id, a.order(), a.handoff)
    assert a.snapshot() == before
    active = ExecutionService(a.env).start(a.order_id, a.order(), a.handoff)
    with a.uow() as uow:
        assert uow.runs.get(active.id).status == 'running'
        assert uow.orders.get(a.order_id).status == 'EXECUTING'
        assert len(uow.events.list_for_run(active.id)) == 1
    active.source.close()


def test_T45_kill_before_start_commit(tmp_path, p4_pack):
    crash_case(tmp_path, p4_pack, 'P4-X13', 'before_run_commit')


def test_T46_kill_after_start_commit(tmp_path, p4_pack):
    crash_case(tmp_path, p4_pack, 'P4-X14', 'after_run_commit')


def test_T47_kill_mid_pipeline(tmp_path, p4_pack):
    crash_case(tmp_path, p4_pack, 'P4-X15', 'mid_pipeline')


def test_T48_kill_after_promotion(tmp_path, p4_pack):
    crash_case(tmp_path, p4_pack, 'P4-X16', 'after_promotion_before_metadata')


def test_T49_artifact_event_rollback(tmp_path, p4_pack):
    crash_case(tmp_path, p4_pack, 'P4-X18', 'event_insert_failure')


def test_T50_committed_restart_and_bad_integer_wires(tmp_path, p4_pack):
    crash_case(tmp_path/'committed', p4_pack, 'P4-X17', 'after_success_commit')
    for c in load(p4_pack/'fixtures/internal_scalar_precision_cases.json')['cases'][13:39]:
        with pytest.raises(ExecutionError) as caught:
            decode_cell(c['wire_cell'], expected_type='integer')
        assert caught.value.code == 'SCHEMA_MISMATCH'
        evidence('w-fixture', c['id'], {'result': 'PASS', 'runtime_decoder': 'REJECTED_WITHOUT_COERCION'})
    # The separate P1 Artifact commit must not be mistaken for Run completion.
    a = Approved(tmp_path/'artifact-only')
    proc = child(a, 'after_artifact_commit')
    assert proc.returncode == -9
    reopened = bootstrap(Config(a.env.workspace.root))
    assert reopened.health == 'degraded' and len(reopened.recovery.stale_runs) == 1
    with a.uow() as uow:
        run = uow.runs.list_for_order(a.order_id)[0]
        assert run.status == 'running' and len(uow.artifacts.list_for_run(run.id)) == 1
        assert len(uow.events.list_for_run(run.id)) == 2
    with pytest.raises(StorageError):
        ExecutionService(reopened).read_result(run.id)


def test_T51_explicit_retry_and_no_stale_adoption(tmp_path):
    a = Approved(tmp_path/'ready')
    service = ExecutionService(a.env)
    active = service.start(a.order_id, a.order(), a.handoff)
    active.source.columns = active.source.columns + ('customer_name',)
    with pytest.raises(ExecutionError):
        service.finish(active)
    old = active.id
    assert a.order().status == 'FAILED'
    fresh = service.fresh_handoff(a.order_id)
    result = service.execute(a.order_id, a.order(), fresh)
    assert result.run_id != old
    with a.uow() as uow:
        assert uow.runs.get(old).status == 'failed'
        assert uow.runs.get(result.run_id).status == 'succeeded'
        assert len(uow.artifacts.list_for_run(old)) == 0
    for stage in ('after_run_commit', 'after_promotion_before_metadata'):
        b = Approved(tmp_path/stage)
        assert child(b, stage).returncode == -9
        reopened = bootstrap(Config(b.env.workspace.root))
        before = b.snapshot()
        with pytest.raises(StorageError):
            ExecutionService(reopened).fresh_handoff(b.order_id)
        assert b.snapshot() == before


def test_T52_failed_run_order_event_atomic(tmp_path):
    runtime_failure(tmp_path/'missing', 'P4-X07', 'COLUMN_NOT_FOUND')
    runtime_failure(tmp_path/'parse', 'P4-X10', 'PARSE_FAILED')


def test_T53_no_p5_output_or_qa(tmp_path):
    a = Approved(tmp_path)
    result = ExecutionService(a.env).execute(a.order_id, a.order(), a.handoff)
    assert a.order().status == 'EXECUTING'
    assert a.counts()['qa_reports'] == 0
    with a.uow() as uow:
        artifacts = uow.artifacts.list_for_run(result.run_id)
        assert len(artifacts) == 1 and artifacts[0].artifact_type == 'P4_INTERNAL' and artifacts[0].format == 'P4_INTERNAL_V2'
    assert not any(p.suffix.lower() in {'.csv', '.xlsx'} for p in a.env.workspace.root.rglob('*'))


def test_T54_ui_manual_click_only(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    a = Approved(tmp_path)
    monkeypatch.setenv('VDE_WORKSPACE', str(a.env.workspace.root))
    app = AppTest.from_file(str(ROOT/'src/vde/app.py')).run(timeout=30)
    assert not app.exception and a.counts() == a.before
    app.checkbox(key='p4_open').check().run(timeout=30)
    app.run(timeout=30)
    assert not app.exception and a.counts() == a.before
    evidence('x-fixture', 'P4-X19', {'result': 'PASS', 'passive_render_writes': 0})
    app.checkbox(key='p4_confirm').check().run(timeout=30)
    started = []
    from vde.execution.service import ExecutionService as Service
    original = Service.start
    def witness(self, *args, **kwargs):
        active = original(self, *args, **kwargs)
        started.append(a.counts())
        return active
    monkeypatch.setattr(Service, 'start', witness)
    app.button(key='p4_execute').click().run(timeout=30)
    assert not app.exception and len(started) == 1
    assert started[0]['execution_runs'] == 1 and started[0]['event_log'] == a.before['event_log']+1
    assert a.counts()['execution_runs'] == 1 and a.order().status == 'EXECUTING'
    before = a.counts()
    app.run(timeout=30)
    assert not app.exception and a.counts() == before


def test_T55_ui_health_blocked_and_degraded(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    for health in ('blocked', 'degraded'):
        a = Approved(tmp_path/health)
        if health == 'blocked':
            a.env.workspace.path(a.asset.workspace_relpath).write_bytes(b'tampered')
        else:
            a.env.workspace.path('.staging/pending').write_bytes(b'pending')
        monkeypatch.setenv('VDE_WORKSPACE', str(a.env.workspace.root))
        before = a.counts()
        app = AppTest.from_file(str(ROOT/'src/vde/app.py')).run(timeout=30)
        app.checkbox(key='p4_open').check().run(timeout=30)
        assert not app.exception and app.button(key='p4_execute').disabled
        assert any('disabled' in w.value for w in app.warning)
        assert a.counts() == before


def test_T56_ui_audit_and_failure_context(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    for failed in (False, True):
        a = Approved(tmp_path/str(failed))
        if failed:
            active = ExecutionService(a.env).start(a.order_id, a.order(), a.handoff)
            inject_runtime_source(active, 'P4-X09')
            with pytest.raises(ExecutionError):
                ExecutionService(a.env).finish(active)
        else:
            ExecutionService(a.env).execute(a.order_id, a.order(), a.handoff)
        before = a.counts()
        monkeypatch.setenv('VDE_WORKSPACE', str(a.env.workspace.root))
        app = AppTest.from_file(str(ROOT/'src/vde/app.py')).run(timeout=30)
        app.checkbox(key='p4_open').check().run(timeout=30)
        assert not app.exception
        visible = '\n'.join(j.value for j in app.json)
        if failed:
            assert 'PARSE_FAILED' in visible and 'bad-date' in visible and 'row_ids' in visible
        else:
            assert 'operation_audit' in visible and 'parse_failed_count' in visible and 'input_rows' in visible
        assert a.counts() == before


def test_T57_repeatability_and_wire_catalog(tmp_path, p4_pack):
    for fixture in ('P-A_dirty_csv', 'P-B_xlsx_sheet'):
        outputs = []
        for index in range(2):
            a = Approved(tmp_path/fixture/str(index), fixture)
            service = ExecutionService(a.env)
            result = service.execute(a.order_id, a.order(), a.handoff)
            outputs.append(service.read_result(result.run_id)[1])
        assert outputs[0] == outputs[1]
    from vde.execution.wire import serialize
    catalog = load(p4_pack/'fixtures/internal_scalar_precision_cases.json')['cases']
    for c in catalog[:13]+catalog[39:41]:
        raw = c['expected_jcs_utf8'].encode('utf-8')
        values = list(iter_payload(raw, expected_columns=['value'], dataset_id='result'))
        encoded, count = serialize(['value'], iter(Row(1, v) for v in values), 'result', Budget())
        assert count == 1 and encoded == raw and hashlib.sha256(encoded).hexdigest() == c['expected_sha256']
        evidence('w-fixture', c['id'], {'result': 'PASS', 'canonical_payload_sha256': c['expected_sha256'], 'actual_runtime_round_trip': True})
    assert catalog[39]['expected_sha256'] != catalog[40]['expected_sha256']
    for c in catalog[13:39]:
        with pytest.raises(ExecutionError):
            decode_cell(c['wire_cell'], expected_type='integer')
    for text in load(ROOT/'tests/p4/fixtures/decimal_fraction_cases.json')['invalid_wire_texts']:
        with pytest.raises(ExecutionError):
            decode_cell({'type': 'decimal', 'value': text})
    # Duplicate keys, invalid Unicode, noncanonical bytes, stale revision and
    # invalid constants are decoder rejections, not repaired successes.
    positive = catalog[0]['expected_jcs_utf8'].encode()
    for raw in (positive.replace(b'P4_INTERNAL_V2', b'P4_INTERNAL_V1'),
                positive+b' ', positive.replace(b'"rows":', b'"rows":[],"rows":'),
                positive.replace(b'"9007199254740991"', b'NaN'),
                positive.replace(b'"9007199254740991"', b'"\\ud800"')):
        with pytest.raises(ExecutionError):
            list(iter_payload(raw))


def test_T58_seeded_typed_sort_dedup_reference(tmp_path):
    import random
    values = [9007199254740993, 2, 9007199254740992, 10, 2, 9223372036854775807]
    for seed in range(32):
        rows = [Row(i+1, (v, 'e\u0301' if i % 2 else 'é')) for i, v in enumerate(values)]
        random.Random(seed).shuffle(rows)
        sort = operation('sort', {'by': ['n'], 'ascending': [True], 'nulls': 'LAST'})
        actual = list(apply(SimpleNamespace(pipeline=[sort]), Source(('n', 's'), iter(rows), []), Budget(), tmp_path).rows)
        assert actual == sorted(rows, key=lambda row: row.values[0])
        for keep in ('FIRST', 'LAST', 'NONE'):
            dedup = operation('deduplicate', {'subset': ['n'], 'keep': keep})
            expected = [row for i, row in enumerate(rows) if
                (keep == 'FIRST' and not any(p.values[0] == row.values[0] for p in rows[:i])) or
                (keep == 'LAST' and not any(p.values[0] == row.values[0] for p in rows[i+1:])) or
                (keep == 'NONE' and sum(p.values[0] == row.values[0] for p in rows) == 1)]
            assert list(apply(SimpleNamespace(pipeline=[dedup]), Source(('n', 's'), iter(rows), []), Budget(), tmp_path).rows) == expected
    unicode_rows = [Row(1, ('e\u0301',)), Row(2, ('é',))]
    op = operation('deduplicate', {'subset': ['s'], 'keep': 'FIRST'})
    assert list(apply(SimpleNamespace(pipeline=[op]), Source(('s',), iter(unicode_rows), []), Budget(), tmp_path).rows) == unicode_rows


def test_T59_positive_dense_workload_and_injected_limits(tmp_path, p4_pack, monkeypatch):
    command = [sys.executable, '-m', 'p4.stress_probe', str(p4_pack), str(tmp_path/'dense')]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, env=child_environment(), timeout=360)
    record_process('stress', proc, command)
    assert proc.returncode == 0, proc.stdout+proc.stderr
    measured = json.loads(proc.stdout)
    assert measured['result'] == 'PASS' and measured['result_rows'] == 90000
    assert measured['incremental_peak_rss_bytes'] <= 536870912 and measured['elapsed_seconds'] <= 120
    for fault, code in (('rss', 'STORAGE_ERROR'), ('time', 'STORAGE_ERROR'), ('scratch', 'STORAGE_ERROR'),
                        ('rows', 'SCHEMA_MISMATCH'), ('cols', 'SCHEMA_MISMATCH'), ('parse', 'PARSE_FAILED')):
        a = Approved(tmp_path/fault)
        service = ExecutionService(a.env)
        active = service.start(a.order_id, a.order(), a.handoff)
        if fault == 'rss':
            active.budget.rss_reader = lambda: active.budget.baseline+536870913
        elif fault == 'time':
            active.budget.clock = lambda: active.budget.started+121
        elif fault == 'scratch':
            active.budget.scratch_limit = 1
        elif fault == 'rows':
            active.source.rows.close()
            active.source.rows = (Row(i+1, ('Alice', 'US', '2026-01-01', '1', 'active', 'a@b')) for i in range(100001))
            # Check the ingress envelope even when downstream dedup could shrink it.
            original = active.source.rows
            def checked():
                for row in original:
                    active.budget.shape(6, row.source)
                    yield row
            active.source.rows = checked()
        elif fault == 'cols':
            active.source.rows.close()
            active.source.rows = iter([Row(1, ('Alice', 'US', '2026-01-01', '1', 'active', 'a@b')+('0',)*195)])
        else:
            inject_runtime_source(active, 'P4-X10')
        with pytest.raises(ExecutionError) as caught:
            service.finish(active)
        assert caught.value.code == code
        assert a.order().status == 'FAILED' and a.counts()['artifacts'] == 0
    from vde.execution import spill
    original_record = spill._record
    modified = []
    def corrupt(position, row):
        raw = original_record(position, row)
        if not modified:
            modified.append(True)
            return raw.replace(b'"0"', b'"1"', 1)
        return raw
    directory = tmp_path/'spill-corrupt'
    directory.mkdir()
    with monkeypatch.context() as patch:
        patch.setattr(spill, '_record', corrupt)
        rows = (Row(i+1, (f'{i:05d}',)+('0',)*199) for i in range(10000))
        with pytest.raises(ExecutionError) as caught:
            list(spill.external_sort(rows, lambda row: row.values[0], directory, Budget()))
        assert caught.value.code == 'STORAGE_ERROR' and caught.value.reason == 'P4_SPILL_CORRUPT'
    assert not list(directory.iterdir())


def test_T60_asset_integrity_and_health(tmp_path, monkeypatch):
    a = Approved(tmp_path/'foreign')
    from vde.models import OrderRecord
    from vde.storage import Storage
    with a.uow() as uow:
        uow.orders.add(OrderRecord('foreign-order', 'Foreign', 'Other Order', '2026-10-30T00:00:00Z', '2026-10-30T00:00:00Z'))
    Storage(a.env.database, a.env.workspace).register_input(id='foreign-asset', order_id='foreign-order', original_filename='input.csv', data=a.raw)
    assert_rejection(a, replace(a.handoff, asset_id='foreign-asset'), 'INPUT_NOT_FOUND', monkeypatch)
    evidence('x-fixture', 'P4-X05', {'result': 'PASS', 'foreign_asset_no_writes_or_io': True})
    b = Approved(tmp_path/'blocked')
    b.env.workspace.path(b.asset.workspace_relpath).write_bytes(b'tampered-before-p4')
    b.raw = b'tampered-before-p4'
    b.env = bootstrap(Config(b.env.workspace.root))
    before = b.snapshot()
    with pytest.raises(StorageError):
        ExecutionService(b.env).start(b.order_id, b.order(), b.handoff)
    assert b.snapshot() == before and b.env.health == 'blocked'
    evidence('x-fixture', 'P4-X06', {'result': 'PASS', 'health': 'blocked', 'writes': 'FORBIDDEN'})
    c = Approved(tmp_path/'missing')
    c.env.workspace.path(c.asset.workspace_relpath).unlink()
    before = c.snapshot()
    with pytest.raises(StorageError):
        ExecutionService(c.env).start(c.order_id, c.order(), c.handoff)
    assert c.snapshot() == before


def test_T61_forbidden_scope(tmp_path):
    from .scope_audit import audit_p4, audit_snippet
    audit_p4(ROOT)
    for snippet in ('eval("1")', 'exec("pass")', 'import requests', 'import socket', 'import openai',
                    'import telegram', 'import celery', 'import sqlalchemy', 'import subprocess',
                    'from urllib.request import urlopen', '__import__("requests")',
                    'import importlib; importlib.import_module("openai")', 'workbook.save("x.xlsx")'):
        with pytest.raises(AssertionError):
            audit_snippet(snippet)


def test_T62_whole_application_scope_CR_P4_001(tmp_path):
    from .scope_audit import audit_p4, negative_repository_probes
    from scope_policy import audit_application
    base_project = subprocess.check_output(['git','show','129300728c446b82eaeafe1068e27339eb7176dd:pyproject.toml'],cwd=ROOT,text=True)
    base_lock = subprocess.check_output(['git','show','129300728c446b82eaeafe1068e27339eb7176dd:uv.lock'],cwd=ROOT,text=True)
    audit_application(ROOT, base_project, base_lock, phase='p3')
    audit_p4(ROOT)
    negative_repository_probes(ROOT, tmp_path)


def test_T63_frozen_regression_evidence_and_p0(p4_pack, tmp_path):
    from .scope_audit import frozen_baseline
    frozen_baseline(ROOT)
    from p3.driver import verify_vectors
    assert verify_vectors() == 'CONTENT_HASH_EQUAL'
    # Execute the specified regressions here as well as in the final combined
    # run. This is the approved T63 action, not merely test-definition counting.
    xml = tmp_path/'p0-p3-regression.xml'
    command = [sys.executable, '-m', 'pytest', 'tests/p1', 'tests/p2', 'tests/p3', '-q', '--junitxml='+str(xml)]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, env=child_environment())
    record_process('T63-p0-p3-regression', proc, command)
    assert proc.returncode == 0, proc.stdout+proc.stderr
    import xml.etree.ElementTree as ET
    collected = {'p1': set(), 'p2': set(), 'p3': set()}
    for case in ET.parse(xml).getroot().iter('testcase'):
        phase = next(p for p in collected if 'test_'+p in case.get('classname'))
        collected[phase].add(case.get('name').split('_')[1][1:])
        assert all(case.find(key) is None for key in ('failure','error','skipped'))
    (ROOT/'docs/p4/validation/T63-p0-p3-regression.xml').write_bytes(xml.read_bytes())
    definitions = {'p1': 42, 'p2': 54, 'p3': 52}
    import ast
    for phase, count in definitions.items():
        tree = ast.parse((ROOT/'tests'/phase/f'test_{phase}.py').read_text())
        ids = [n.name.split('_')[1][1:] for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_T')]
        assert sorted(ids) == [f'{i:02}' for i in range(1, count+1)]
        assert collected[phase] == {f'{i:02}' for i in range(1,count+1)}


def test_T64_approved_archive_strict_verifier(p4_pack):
    command = [sys.executable, str(p4_pack/'tools/verify_p4_fixture_consistency.py'),
               '--p0-root', str(ROOT/'pecs/pilot_slice_v1'), '--require-p0', '--mutation-probes']
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    record_process('fixture-verifier', proc, command)
    assert proc.returncode == 0 and proc.stderr == ''
    summary = json.loads(proc.stdout.splitlines()[0])
    assert summary['result'] == 'STATIC_PINS_REFS_AND_P0_CONTRACTS_PASS'
    assert (summary['p0_valid_operation_schemas'], summary['p0_schema_invalid_operation_cases'],
            summary['p0_semantic_invalid_operation_cases'], summary['golden'], summary['precision_cases']) == (36, 2, 1, 2, 45)
    assert '9/9 isolated mutations rejected' in proc.stdout


def child_environment():
    import os
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT/'src')+os.pathsep+str(ROOT/'tests')
    return env


def child(a, stage):
    command = [sys.executable, '-m', 'p4.restart_probe', str(a.env.workspace.root), stage]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, env=child_environment(), timeout=40)
    record_process('restart-'+stage, proc, command)
    return proc


def record_process(name, process, command):
    directory = ROOT/'docs/p4/validation'
    directory.mkdir(parents=True, exist_ok=True)
    (directory/(name+'.stdout.txt')).write_text(process.stdout)
    (directory/(name+'.stderr.txt')).write_text(process.stderr)
    (directory/(name+'.command.json')).write_text(json.dumps({'argv': command, 'cwd': str(ROOT), 'exit_code': process.returncode}, indent=2)+'\n')


def generate_stress(pack, directory, rows=100000, cols=200):
    import importlib.util
    spec = importlib.util.spec_from_file_location('test_stress_generator', pack/'tools/generate_p4_stress_fixture.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = directory/f'dense-{rows}-{cols}.csv'
    result = module.generate(path, rows, cols, 37, 90000)
    if rows == 100000 and cols == 200:
        assert result['byte_size'] == 40801000 and result['sha256'] == '5c5d2dbf69c0b8f4d27be5ec8a258677eb883d5ad267a4ec644b0205978aa97d'
    evidence('generator', f'{rows}x{cols}', result)
    return path


def raw_source(directory, raw):
    from vde.models import OrderRecord
    from vde.persistence.uow import UnitOfWork
    from vde.storage import Storage
    env = bootstrap(Config(directory/'workspace'))
    with UnitOfWork(env.database, env.workspace) as uow:
        uow.orders.add(OrderRecord('raw-order','Reader','P4 source limit probe','2026-10-30T00:00:00Z','2026-10-30T00:00:00Z'))
    asset = Storage(env.database, env.workspace).register_input(id='raw-asset', order_id='raw-order', original_filename='input.csv', data=raw)
    handoff = SimpleNamespace(input_selection={'source_type': 'LOCAL_CSV', 'sheet_name': None,
                       'csv_options': {'encoding': 'UTF-8', 'delimiter': ',', 'header_row': 0}})
    return iter_verified_rows(env, SimpleNamespace(asset=asset, handoff=handoff), Budget()), env, asset


def inject_runtime_source(active, identity):
    if identity == 'P4-X07':
        active.source.columns = active.source.columns[1:]
    elif identity == 'P4-X08':
        active.source.columns += ('customer_name',)
    else:
        original = active.source.rows
        def changed():
            try:
                for row in original:
                    values = list(row.values)
                    if row.source == 2:
                        values[2 if identity == 'P4-X09' else 3] = 'bad-date' if identity == 'P4-X09' else 'not-a-number'
                    yield Row(row.source, tuple(values))
            finally:
                original.close()
        active.source.rows = changed()


def runtime_failure(directory, identity, code):
    a = Approved(directory)
    service = ExecutionService(a.env)
    active = service.start(a.order_id, a.order(), a.handoff)
    inject_runtime_source(active, identity)
    with pytest.raises(ExecutionError) as caught:
        service.finish(active)
    assert caught.value.code == code
    public = caught.value.public(order_id=a.order_id, run_id=active.id, source_id=a.asset_id)
    validate(public, 'execution_error')
    assert a.order().status == 'FAILED' and a.order().approval_stage == 'COMPLETE'
    assert a.counts() == a.before | {'execution_runs': 1, 'event_log': a.before['event_log']+2}
    reopened = bootstrap(Config(a.env.workspace.root))
    assert reopened.health == 'ready' and not reopened.recovery.stale_runs
    with a.uow() as uow:
        run = uow.runs.get(active.id)
        assert run.status == 'failed' and run.error_json['code'] == code
        assert len(uow.events.list_for_run(run.id)) == 2
    assert a.env.workspace.path(a.asset.workspace_relpath).read_bytes() == a.raw
    evidence('x-fixture', identity, {'result': 'PASS', 'run_status': 'failed', 'order_status': 'FAILED',
             'p4_eventlog_delta': 2, 'new_artifact_rows': 0, 'health_after_restart': 'ready', 'public_error': public})
    return caught.value


def crash_case(directory, pack, identity, stage):
    a = Approved(directory)
    expected = next(c for c in load(pack/'fixtures/failure_cases.json')['cases'] if c['id'] == identity)['expected_state']
    proc = child(a, stage)
    assert proc.returncode == (0 if stage == 'event_insert_failure' else -9), proc.stdout+proc.stderr
    reopened = bootstrap(Config(a.env.workspace.root))
    actual = {'order_status': a.order().status, 'approval_stage': a.order().approval_stage,
              'new_run_rows': a.counts()['execution_runs']-a.before['execution_runs'],
              'new_artifact_rows': a.counts()['artifacts']-a.before['artifacts'],
              'p4_eventlog_delta': a.counts()['event_log']-a.before['event_log'],
              'new_orphan_files': len(reopened.recovery.orphans), 'health_after_restart': reopened.health,
              'recovery_stale_run_count': len(reopened.recovery.stale_runs),
              'source_unchanged': a.env.workspace.path(a.asset.workspace_relpath).read_bytes() == a.raw}
    with a.uow() as uow:
        runs = uow.runs.list_for_order(a.order_id)
        approvals = uow.approvals.list_for_order(a.order_id)
    actual['run_status'] = None if not runs else runs[0].status
    actual['approval_ids_unchanged'] = {v.id for v in approvals} == {a.handoff.brief_approval_id, a.handoff.transformation_approval_id}
    eligible = False
    before = a.snapshot()
    if runs:
        try:
            handle, raw = ExecutionService(reopened).read_result(runs[0].id)
            eligible = True
            assert handle.checksum == hashlib.sha256(raw).hexdigest() and handle.row_count == 3
        except (ExecutionError, StorageError):
            assert expected['p5_handoff_eligible'] is False
    actual['p5_handoff_eligible'] = eligible
    assert a.snapshot() == before  # No bootstrap/read auto-resume or repair.
    for key, value in actual.items():
        assert value == expected[key], (identity, key, value, expected[key])
    if expected['explicit_retry_allowed']:
        assert ExecutionService(reopened).fresh_handoff(a.order_id) == a.handoff
    evidence('x-fixture', identity, {'result': 'PASS', **actual, 'automatic_retry_observed': False,
              'child_exit_code': proc.returncode, 'checkpoint': stage})


def check_golden(directory, pack, fixture, identity):
    import csv
    a = Approved(directory, fixture)
    service = ExecutionService(a.env)
    result = service.execute(a.order_id, a.order(), a.handoff)
    handle, raw = service.read_result(result.run_id)
    rows = list(iter_payload(raw))
    with a.uow() as uow:
        fields = uow.specs.get(a.handoff.transformation_spec_version_id).document_json['expected_schema']
    projection = []
    for row in rows:
        projected = []
        for field, value in zip(fields, row):
            if value is None:
                text = ''
            elif field['data_type'] == 'date':
                assert type(value) is date
                text = value.isoformat()
            elif field['data_type'] == 'decimal':
                assert type(value) in (int, Decimal)
                text = format(Decimal(value), 'f')
                if '.' not in text:
                    text += '.0'
            elif field['data_type'] == 'integer':
                assert type(value) is int
                text = str(value)
            else:
                assert type(value) is str
                text = value
            projected.append(text)
        projection.append(projected)
    g = load(pack/'fixtures/golden_oracles.json')['oracles'][identity]
    expected = list(csv.reader(io.StringIO((ROOT/g['expected_csv_path']).read_text(), newline='')))
    actual = [[f['output_name'] for f in fields]] + projection
    assert actual == expected and len(rows) == 3
    output = io.StringIO(newline='')
    csv.writer(output, lineterminator='\n').writerows(actual)
    assert hashlib.sha256(output.getvalue().encode()).hexdigest() == g['expected_csv_sha256']
    assert a.env.workspace.path(a.asset.workspace_relpath).read_bytes() == a.raw
    evidence('golden', identity, {'result': 'PASS', 'logical_sha256': handle.checksum,
                                  'golden_csv_sha256': g['expected_csv_sha256'], 'rows': 3, 'columns': 6})
