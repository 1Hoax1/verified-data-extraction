"""Twenty P6 runtime oracles. A blocked platform check remains a real FAIL."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.request import urlopen
from uuid import uuid4
from types import SimpleNamespace

from openpyxl import load_workbook
import pytest

from vde.bootstrap import bootstrap
from vde.config import Config
from vde.contracts import content_hash, validate
from vde.errors import StorageError
from vde.p6.orders import CreateOrderService, P6Error
from vde.p6.delivery import DeliveryService
from .conftest import (ROOT, FIXTURES, TABLES, UIScenario, canonical, healthy_ui,
                       mutate_sql, new_app, payload_hashes, record, sha, snapshot, widget)


def refused(env, order_id, run_id, codes=None):
    before = snapshot(env.workspace.root)
    files = payload_hashes(env.workspace.root)
    with pytest.raises((P6Error, StorageError)) as caught:
        DeliveryService(env).prepare(order_id, run_id)
    code = getattr(caught.value, 'code', 'STORAGE_ERROR')
    if codes:
        assert code in codes
    assert snapshot(env.workspace.root) == before
    assert payload_hashes(env.workspace.root) == files
    return code


def transfer(app, fetch, expected):
    """Read the actual HTTP response body; never substitute snapshot bytes."""
    outputs = {}
    controls = app.get('download_button')
    assert len(controls) == 2
    for control in controls:
        response = fetch(control.proto.url)
        assert response.code == 200
        assert int(response.headers['Content-Length']) == len(response.body)
        name = ('report' if control.label == 'Download QAReport' else 'result')
        raw, filename, mime = expected[name]
        assert response.body == raw
        assert sha(response.body) == sha(raw)
        assert response.headers['Content-Type'] == mime
        assert filename in response.headers['Content-Disposition']
        outputs[name] = {'bytes': len(response.body), 'sha256': sha(response.body),
                         'url': control.proto.url, 'status': response.code,
                         'content_type': response.headers['Content-Type'],
                         'content_disposition': response.headers['Content-Disposition']}
    return outputs


def snapshot_expectation(prepared):
    return {'result': (prepared.result_bytes, prepared.result_name, prepared.result_mime),
            'report': (prepared.report_bytes, prepared.report_name, prepared.report_mime)}


def verified_report(case, prepared):
    report = json.loads(prepared.report_bytes.decode('utf-8'))
    validate(report, 'qa_report')
    assert prepared.report_bytes == canonical(case.decision.report)
    assert report['run_id'] == case.run_id
    assert report['brief_version_id'] == case.brief.id
    assert report['transformation_spec_version_id'] == case.spec.id
    assert report['report_id'] == prepared.view.report_record.report_id
    assert report['dataset_summary']['checksum'] == sha(prepared.result_bytes)
    assert report['dataset_summary']['file_size_bytes'] == len(prepared.result_bytes)
    assert report['artifacts'] == case.decision.report['artifacts']
    assert len(report['artifacts']) == 1
    return report


def test_T01_fresh_linux_bootstrap_and_passive_ui(tmp_path):
    directory = tmp_path / 'fresh'
    env = bootstrap(Config(directory))
    assert platform.system() == 'Linux' and env.health == 'ready'
    before = snapshot(directory)
    app = new_app(directory)
    for _ in range(3):
        healthy_ui(app.run())
    assert all(not before[t] for t in TABLES)
    assert snapshot(directory) == before
    assert not widget(app, 'button', 'Create DRAFT Order').disabled
    assert len(app.get('download_button')) == 0
    record('T01', {'health': env.health, 'platform': platform.platform(), 'before': before,
                   'after': snapshot(directory), 'passive_rerenders': 3})


def test_T02_create_order_form_exact_fields_and_p2_visibility(tmp_path):
    directory = tmp_path / 'create'
    bootstrap(Config(directory))
    app = new_app(directory)
    token = app.session_state['p6_order_request_token']
    values = {'Order title': '  Isolated order  ', 'Listing text': '  Exact listing\ntext  ',
              'Listing URL (optional)': 'https://example.invalid/no-fetch',
              'Budget (canonical decimal, optional)': '123.45',
              'Deadline (UTC YYYY-MM-DDTHH:MM:SSZ, optional)': '2026-12-01T12:00:00Z',
              'Notes (optional)': '  verbatim notes  '}
    for label, value in values.items():
        kind = 'text_area' if label in {'Listing text', 'Notes (optional)'} else 'text_input'
        widget(app, kind, label).set_value(value)
    healthy_ui(widget(app, 'button', 'Create DRAFT Order').click().run())
    observed = snapshot(directory)
    assert len(observed['orders']) == 1
    order = observed['orders'][0]
    assert order['id'] == token and order['status'] == 'DRAFT'
    assert order['title'] == 'Isolated order' and order['listing_text'] == values['Listing text']
    for key, label in [('listing_url', 'Listing URL (optional)'), ('budget', 'Budget (canonical decimal, optional)'),
                       ('deadline', 'Deadline (UTC YYYY-MM-DDTHH:MM:SSZ, optional)'), ('notes', 'Notes (optional)')]:
        assert order[key] == values[label]
    assert order['created_at'] == order['updated_at']
    assert all(order[k] is None for k in ('approval_stage', 'selected_brief_version_id',
                                         'selected_transformation_spec_version_id'))
    assert all(not observed[t] for t in TABLES if t != 'orders')
    assert token in widget(app, 'selectbox', 'Existing Order').value
    record('T02', {'request_token': token, 'submitted': values, 'persisted': order,
                   'associated_counts': {t: len(observed[t]) for t in TABLES if t != 'orders'}})


def test_T03_invalid_form_retry_idempotency_and_concurrent_conflict(tmp_path):
    directory = tmp_path / 'retry'
    env = bootstrap(Config(directory))
    app = new_app(directory)
    token = app.session_state['p6_order_request_token']
    for title, budget, deadline in [('', '', ''), ('Valid', '1.00', ''),
                                    ('Valid', 'NaN', ''), ('Valid', '1e3', ''),
                                    ('Valid', '', '2026-12-01T12:00:00+00:00')]:
        widget(app, 'text_input', 'Order title').set_value(title)
        widget(app, 'text_area', 'Listing text').set_value('Explicit test input')
        widget(app, 'text_input', 'Budget (canonical decimal, optional)').set_value(budget)
        widget(app, 'text_input', 'Deadline (UTC YYYY-MM-DDTHH:MM:SSZ, optional)').set_value(deadline)
        healthy_ui(widget(app, 'button', 'Create DRAFT Order').click().run())
        assert not snapshot(directory)['orders']
        assert app.session_state['p6_order_request_token'] == token
    before = snapshot(directory)
    app.run(); app.run(); app.run()
    assert snapshot(directory) == before
    fields = dict(title='Valid', listing_text='Exact listing', budget='1.5')
    def create(_):
        return CreateOrderService(bootstrap(Config(directory))).create(token, **fields)
    with ThreadPoolExecutor(max_workers=2) as executor:
        orders = list(executor.map(create, range(2)))
    assert orders[0].id == orders[1].id == token
    before = snapshot(directory)
    assert CreateOrderService(env).create(token, **fields).id == token
    with pytest.raises(P6Error) as caught:
        CreateOrderService(env).create(token, title='Conflicting', listing_text='Exact listing', budget='1.5')
    assert caught.value.code == 'P6_ORDER_TOKEN_CONFLICT'
    assert snapshot(directory) == before and len(before['orders']) == 1
    record('T03', {'retained_token': token, 'invalid_submissions': 5, 'concurrent_results': [o.id for o in orders],
                   'conflict': caught.value.code, 'counts': {k: len(v) for k, v in before.items()}})


def test_T04_pa_explicit_two_ui_approvals_and_exact_hashes(pa):
    assert len(pa.before_brief_approval['approvals']) == 0
    assert len(pa.after_brief_approval['approvals']) == len(pa.before_spec_approval['approvals']) == 1
    approvals = pa.approved_snapshot['approvals']
    assert len(approvals) == 2
    for approval, version, target in [(next(a for a in approvals if a['target_type'] == 'BRIEF'), pa.brief, 'BRIEF'),
                                      (next(a for a in approvals if a['target_type'] == 'TRANSFORMATION_SPEC'), pa.spec, 'TRANSFORMATION_SPEC')]:
        kind = 'brief_version' if target == 'BRIEF' else 'transformation_spec_version'
        assert approval['target_version_id'] == version.id
        assert approval['target_content_hash'] == version.content_hash == content_hash(version.document_json, kind)
        assert approval['approved_by'] == 'local_user'
    spec_approval = next(a for a in approvals if a['target_type'] == 'TRANSFORMATION_SPEC')
    assert (spec_approval['context_brief_version_id'], spec_approval['context_brief_content_hash']) == (pa.brief.id, pa.brief.content_hash)
    labels = [a['label'] for a in pa.actions]
    assert labels.index('I approve this Brief version') < labels.index('Save new TransformationSpec version')
    assert labels.index('Confirm this exact Spec ID, hash and approved Brief context') < labels.index('I approve TransformationSpec') < labels.index('Execute')
    record('T04', {'approvals': approvals, 'explicit_actions': pa.actions, 'adaptations': pa.adaptations})


def test_T05_pa_csv_result_and_qa_actual_http_transfer(pa, download_http):
    assert pa.order().status == 'READY' and pa.decision.report['overall_status'] == 'PASS'
    before = pa.snapshot()
    prepared = pa.prepare_ui()
    golden = (pa.source / 'expected_result.csv').read_bytes()
    assert len(golden) == 277 and prepared.result_bytes == golden
    assert sha(golden) == pa.decision.artifact.checksum
    verified_report(pa, prepared)
    observations = transfer(pa.app, download_http, snapshot_expectation(prepared))
    assert pa.snapshot() == before
    record('T05', {'http_transfers': observations, 'golden_sha256': sha(golden), 'snapshot_key': prepared.key})


def _cr_p6_002_guard_cases(pb):
    """Recognition-only mutations never grant or persist Approval authority."""
    from vde.p5.service import P5Service
    from vde.p5.qa import _certified_pb_columns, criterion_result, predicate
    context = P5Service(pb.env).inspect(pb.run_id, pb.order())
    before, files = pb.snapshot(), payload_hashes(pb.directory)
    original = deepcopy(context.brief.document_json)
    criterion = next(c for c in original['acceptance_criteria'] if c['criterion_id'] == 'PB-AC-002')
    projection = context.projection
    assert _certified_pb_columns(criterion, projection, context)
    assert criterion_result(criterion, SimpleNamespace(projection=projection), {}, context)['status'] == 'PASS'
    assert not predicate('sequence_equals', list(projection.columns), criterion['expected'])
    matrix = []

    def reject(label, *, changes=(), asset_changes=None, output_changes=None, columns=None, spec_inputs=None):
        doc = deepcopy(original)
        for path, value in changes:
            parent = doc
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = deepcopy(value)
        # An altered contract cannot acquire the exception even if it has its
        # own correct semantic hash. These are pure unit copies, not live or
        # admitted replacement versions and never substitute for Approvals.
        doc['content_hash'] = content_hash(doc, 'brief_version')
        brief = replace(context.brief, document_json=doc, content_hash=doc['content_hash'])
        asset = replace(context.asset, **(asset_changes or {}))
        output = {**projection.output, **(output_changes or {})}
        spec_doc = deepcopy(context.spec.document_json); spec_doc['output'] = output
        if spec_inputs is not None:
            spec_doc['inputs'] = deepcopy(spec_inputs)
        copied = replace(context, brief=brief, asset=asset,
                         spec=replace(context.spec, document_json=spec_doc))
        projected = replace(projection, output=output, columns=tuple(columns or projection.columns))
        c = doc['acceptance_criteria'][1]
        assert not _certified_pb_columns(c, projected, copied), label
        result = criterion_result(c, SimpleNamespace(projection=projected), {}, copied)
        assert result['status'] == 'FAIL', (label, result)
        matrix.append(dict(case=label, outcome='REJECTED', qa_status=result['status'],
                           semantic_hash=doc['content_hash'], recognition_only=True))

    edits = [
        ('objective', ('objective',), original['objective'] + ' Different contract.'),
        ('record_definition', ('record_definition',), 'A different record.'),
        ('scope', ('scope', 'included'), ['Different scope']),
        ('field_description', ('fields', 0, 'description'), 'Changed field meaning'),
        ('field_type', ('fields', 0, 'data_type'), 'integer'),
        ('field_required', ('fields', 0, 'required'), False),
        ('volume', ('volume_expectation', 'exact_count'), 4),
        ('quality', ('data_quality_expectations', 'unexpected_columns_allowed'), True),
        ('risk', ('risks', 0, 'description'), 'Different risk'),
        ('assumption', ('assumptions', 0, 'text'), 'Different assumption'),
        ('criterion_severity', ('acceptance_criteria', 1, 'severity'), 'INFO'),
        ('criterion_id', ('acceptance_criteria', 1, 'criterion_id'), 'OTHER-AC-002'),
        ('operator', ('acceptance_criteria', 1, 'operator'), 'set_equals'),
        ('target_scope', ('acceptance_criteria', 1, 'target', 'scope'), 'METRIC'),
        ('expected_order', ('acceptance_criteria', 1, 'expected'), list(reversed(criterion['expected']))),
        ('target_order', ('acceptance_criteria', 1, 'target', 'columns'), list(reversed(criterion['expected']))),
        ('input_type', ('inputs_expected', 0, 'input_type'), 'LOCAL_CSV'),
        ('sheet', ('inputs_expected', 0, 'sheet_name'), 'Notes'),
        ('input_binding', ('inputs_expected', 0, 'asset_id'), 'wrong-asset'),
        ('no_input', ('inputs_expected',), []),
        ('multiple_inputs', ('inputs_expected',), original['inputs_expected'] * 2),
    ]
    for label, path, value in edits:
        reject(label, changes=[(path, value)])
    reject('source_checksum', asset_changes={'byte_sha256': '0' * 64})
    reject('actual_asset_id', asset_changes={'id': 'different-asset'})
    for key, value in [('format', 'CSV'), ('file_name', 'different.xlsx'), ('sheet_name', 'Different'),
                       ('dataset_id', 'different'), ('column_order', list(reversed(projection.columns)))]:
        reject('output_' + key, output_changes={key: value})
    reject('projected_column_order', columns=list(reversed(projection.columns)))
    source = context.spec.document_json['inputs'][0]
    for key, value in [('asset_id', 'wrong-source'), ('sheet_name', 'Notes'), ('source_type', 'LOCAL_CSV')]:
        reject('selected_source_' + key, spec_inputs=[{**source, key: value}])
    reject('no_selected_source', spec_inputs=[])
    reject('multiple_selected_sources', spec_inputs=[source, source])
    generic = deepcopy(criterion); generic['criterion_id'] = 'GENERIC-AC-002'
    assert criterion_result(generic, SimpleNamespace(projection=projection), {}, context)['status'] == 'FAIL'
    assert pb.snapshot() == before and payload_hashes(pb.directory) == files
    assert context.brief.document_json == original
    return dict(fresh_uuid_brief_id=context.brief.id, real_semantic_hash=context.brief.content_hash,
                positive_status='PASS', generic_five_vs_six='FAIL', negatives=matrix,
                immutable_context_and_payloads=True, approval_authority='Unchanged actual P5 admission; unit copies are not authority')


def _canonical_pb_oracle(directory):
    # Reuse the approved historical isolated P1/P3/P4 procedure. Its two
    # explicit simulated API actions create real test-local Approvals; no
    # imported fixture Approval, direct approval INSERT or owner claim exists.
    from p5.support import Scenario, pb_v2
    case = Scenario(directory, 'P-B_xlsx_sheet', change=pb_v2)
    with case.uow() as u:
        brief = u.briefs.get(case.handoff.brief_version_id)
        spec = u.specs.get(case.handoff.transformation_spec_version_id)
        approvals = u.approvals.list_for_order(case.order_id)
    internal_hashes = payload_hashes(case.env.workspace.root)
    decision = case.complete()
    assert brief.id == 'brief-pb-v1' and brief.content_hash == '9b7c2b0111360714dfbc9cbdbc755b693b11e067f32771cb226126fdcd1ffb49'
    assert spec.id == 'transform-pb-v2-cr-p5-001' and spec.version_number == 2
    assert case.order().status == decision.order_status == 'READY'
    assert decision.report['overall_status'] == 'PASS_WITH_WARNINGS'
    assert decision.artifact.artifact_type == 'RESULT_XLSX' and len(approvals) == 2
    checks = decision.report['deterministic_checks']
    assert len(checks) == 24 and not any(c['status'] == 'FAIL' for c in checks)
    assert {c['criterion_id']: c['status'] for c in checks if c['check_id'] == 'DQ-017'} == {'PB-AC-006': 'PASS', 'PB-AC-007': 'PASS'}
    assert 'XLSX_FORMULA_PRESENT' in decision.report['warnings']
    path = case.env.workspace.path(decision.artifact.workspace_relpath)
    actual = load_workbook(path.open('rb'), read_only=True, data_only=False)
    golden = load_workbook(case.source / 'expected_result.xlsx', read_only=True, data_only=False)
    try:
        cells = list(actual['Data'].rows)
        values = [[c.value for c in row] for row in cells]
        assert values == [[c.value for c in row] for row in golden.active.rows]
        assert len(cells) == 4 and all(len(row) == 6 for row in cells)
        assert all(c.data_type != 'f' for row in cells for c in row)
    finally:
        actual.close(); golden.close()
    after = payload_hashes(case.env.workspace.root)
    assert all(after[name] == digest for name, digest in internal_hashes.items())
    assert sha(path.read_bytes()) == decision.artifact.checksum
    from vde.p5.service import P5Service
    from vde.p5.qa import _certified_pb_columns, criterion_result
    context = P5Service(case.env).inspect(case.run_id, case.order())
    criterion = next(c for c in brief.document_json['acceptance_criteria'] if c['criterion_id'] == 'PB-AC-002')
    wrong_source = replace(context, asset=replace(context.asset, byte_sha256='0' * 64))
    assert not _certified_pb_columns(criterion, context.projection, wrong_source)
    assert criterion_result(criterion, SimpleNamespace(projection=context.projection), {}, wrong_source)['status'] == 'FAIL'
    return dict(brief=asdict(brief), spec=asdict(spec), approvals=[asdict(a) for a in approvals],
                report=decision.report, data_cells=18, decoded_cells=values, result_sha256=decision.artifact.checksum,
                isolated_simulated_API_actions_only=True, original_source_and_P4_unchanged=True,
                original_id_with_wrong_source='FAIL in recognition-only negative; no original-ID bypass')


def test_T06_pb_explicit_v2_approval_and_typed_warning_oracle(pb, tmp_path):
    assert pb.spec.version_number == 2
    with pb.uow() as u:
        versions = u.specs.list_for_order(pb.order_id)
        approvals = u.approvals.list_for_order(pb.order_id)
        artifacts = u.artifacts.list_for_run(pb.run_id)
    assert len(versions) == 2 and len(approvals) == 2
    assert next(a for a in approvals if a.target_type == 'TRANSFORMATION_SPEC').target_version_id == pb.spec.id
    assert all(a.approved_by == 'local_user' for a in approvals)
    checks = pb.decision.report['deterministic_checks']
    assert len(checks) == 24
    dq17 = {c['criterion_id']: c['status'] for c in checks if c['check_id'] == 'DQ-017'}
    assert dq17 == {'PB-AC-006': 'PASS', 'PB-AC-007': 'PASS'}
    assert pb.decision.report['warnings']
    assert any('FORMULA' in json.dumps(w).upper() for w in pb.decision.report['warnings'])
    assert [a.artifact_type for a in artifacts if a.artifact_type.startswith('RESULT_')] == ['RESULT_XLSX']
    guards = _cr_p6_002_guard_cases(pb)
    canonical_pb = _canonical_pb_oracle(tmp_path / 'canonical-pb')
    record('T06', {'versions': [asdict(v) for v in versions], 'approvals': [asdict(a) for a in approvals],
                   'CR_P6_002_guards': guards, 'canonical_pb': canonical_pb,
                   'DQ017': dq17, 'checks': len(checks), 'warnings': pb.decision.report['warnings'],
                   'adaptations': pb.adaptations, 'observed_order_status': pb.order().status,
                   'observed_qa_status': pb.decision.report['overall_status'],
                   'actual_report': pb.decision.report,
                   'blocking_issues': pb.decision.report['blocking_issues'],
                   'failed_checks': [c for c in checks if c['status'] == 'FAIL']})
    assert pb.order().status == 'READY' and pb.decision.report['overall_status'] == 'PASS_WITH_WARNINGS', (
        'Certified P-B must pass with its actual approved UUID Brief and unchanged acceptance contract.',
        pb.decision.report['blocking_issues'])


def test_T07_pb_xlsx_and_qa_independent_http_and_18_cells(pb, download_http):
    before = pb.snapshot()
    prepared = pb.prepare_ui()
    verified_report(pb, prepared)
    assert prepared.result_name.endswith('.xlsx')
    assert prepared.result_mime == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    book = load_workbook(io.BytesIO(prepared.result_bytes), read_only=True, data_only=False, keep_links=False)
    try:
        sheet = book[pb.spec.document_json['output']['sheet_name']]
        rows = list(sheet.iter_rows())
        assert len(rows) == 4 and all(len(row) == 6 for row in rows)
        assert all(cell.data_type != 'f' for row in rows for cell in row)
        values = [[cell.value for cell in row] for row in rows]
    finally:
        book.close()
    # Frozen P-B expected cells are independent of the exported workbook.
    golden = load_workbook(pb.source / 'expected_result.xlsx', read_only=True, data_only=False, keep_links=False)
    try:
        expected = [[cell.value for cell in row] for row in golden.active.iter_rows()]
    finally:
        golden.close()
    assert values == expected
    assert sum(len(row) for row in values[1:]) == 18
    observations = transfer(pb.app, download_http, snapshot_expectation(prepared))
    assert pb.snapshot() == before
    record('T07', {'http_transfers': observations, 'decoded_cells': values, 'data_cells': 18,
                   'observed_qa_status': pb.decision.report['overall_status'], 'result_name': prepared.result_name})
    assert pb.order().status == 'READY' and pb.decision.report['overall_status'] == 'PASS_WITH_WARNINGS'
    assert '_DIAGNOSTIC_NOT_FOR_DELIVERY' not in prepared.result_name


def test_T08_pd_diagnostic_never_client_ready(pd, download_http):
    assert pd.order().status == 'NEEDS_FIX' and pd.decision.report['overall_status'] == 'FAIL'
    before = pd.snapshot()
    prepared = pd.prepare_ui()
    assert '_DIAGNOSTIC_NOT_FOR_DELIVERY.' in prepared.result_name
    assert prepared.view.diagnostic
    report = verified_report(pd, prepared)
    assert report['blocking_issues']
    controls = pd.app.get('download_button')
    assert any(c.label == 'Download diagnostic — NOT FOR DELIVERY' for c in controls)
    assert not any(c.label == 'Download verified result' for c in controls)
    warnings = [e.value for e in pd.app.warning] + [e.value for e in pd.app.error]
    assert any('NOT FOR DELIVERY' in w for w in warnings)
    observations = transfer(pd.app, download_http, snapshot_expectation(prepared))
    assert pd.snapshot() == before
    record('T08', {'order_status': pd.order().status, 'QA': report['overall_status'],
                   'warnings': warnings, 'http_transfers': observations})


def test_T09_ineligible_states_and_missing_approvals(pa, tmp_path, copy_workspace):
    env = bootstrap(Config(tmp_path / 'draft'))
    order = CreateOrderService(env).create(str(uuid4()), title='Draft', listing_text='No run')
    observations = {'DRAFT/no_run': refused(env, order.id, str(uuid4()))}
    for status in ('DRAFT', 'FAILED', 'EXECUTING', 'APPROVED'):
        directory, copied = copy_workspace(pa)
        mutate_sql(directory, 'UPDATE orders SET status=? WHERE id=?', (status, pa.order_id))
        observations[status] = refused(copied, pa.order_id, pa.run_id)
    directory, copied = copy_workspace(pa)
    mutate_sql(directory, 'DELETE FROM approvals WHERE target_type=?', ('TRANSFORMATION_SPEC',))
    observations['missing_approval'] = refused(copied, pa.order_id, pa.run_id)
    record('T09', observations)


def test_T10_restart_intermediate_and_terminal_no_cached_authorization(tmp_path, pa, copy_workspace):
    intermediate = UIScenario(tmp_path / 'intermediate', execute=False, pause_after_brief=True)
    before = intermediate.snapshot()
    restarted = new_app(intermediate.directory)
    assert intermediate.snapshot() == before and not before['execution_runs']
    assert len(before['approvals']) == 1 and not before['transformation_spec_versions']
    assert len(restarted.get('download_button')) == 0
    directory, env = copy_workspace(pa)
    first = new_app(directory)
    widget(first, 'selectbox', 'Download Order').set_value(pa.order_id).run()
    widget(first, 'selectbox', 'Download Run').set_value(pa.run_id).run()
    widget(first, 'button', 'Prepare verified download').click().run()
    assert len(first.get('download_button')) == 2
    before = snapshot(directory)
    restarted = new_app(directory)
    assert snapshot(directory) == before
    assert 'p6_delivery_snapshot' not in restarted.session_state or restarted.session_state['p6_delivery_snapshot'] is None
    assert len(restarted.get('download_button')) == 0
    assert DeliveryService(bootstrap(Config(directory))).view(pa.order_id, pa.run_id).key
    record('T10', {'intermediate_counts': {k: len(v) for k, v in intermediate.snapshot().items()},
                   'terminal_counts': {k: len(v) for k, v in before.items()}, 'old_snapshot_reused': False})


def test_T11_corrupt_source_csv_and_xlsx_on_disposable_copies(pa, pb, copy_workspace):
    observations = {}
    for case in (pa, pb):
        directory, env = copy_workspace(case)
        path = directory / case.asset.workspace_relpath
        original = path.read_bytes()
        path.write_bytes(original + b'CORRUPTION')
        before = snapshot(directory)
        recovered = bootstrap(Config(directory))
        assert recovered.health == 'blocked'
        code = refused(env, case.order_id, case.run_id)
        assert snapshot(directory) == before and path.read_bytes() == original + b'CORRUPTION'
        app = new_app(directory)
        assert len(app.get('download_button')) == 0
        assert widget(app, 'button', 'Create DRAFT Order').disabled
        observations[case.family] = {'health': recovered.health, 'error': code,
                                     'original_sha256': sha(original), 'mutated_sha256': sha(path.read_bytes())}
    record('T11', observations)


def test_T12_corrupt_internal_final_and_snapshot_boundary(pa, copy_workspace):
    observations = []
    for kind in ('P4_INTERNAL', 'RESULT_CSV'):
        directory, env = copy_workspace(pa)
        artifact = next(a for a in snapshot(directory)['artifacts'] if a['artifact_type'] == kind)
        prepared = DeliveryService(env).prepare(pa.order_id, pa.run_id)
        verified_bytes = prepared.result_bytes
        path = directory / artifact['workspace_relpath']
        path.write_bytes(path.read_bytes() + b'CORRUPT')
        code = refused(env, pa.order_id, pa.run_id)
        assert prepared.result_bytes == verified_bytes
        assert sha(prepared.result_bytes) == pa.decision.artifact.checksum
        observations.append({'kind': kind, 'new_prepare_error': code, 'old_verified_snapshot_sha256': sha(verified_bytes),
                             'snapshot_boundary': 'Existing immutable bytes remain the previously verified copy.'})
    record('T12', observations)


def test_T13_cross_order_and_context_guards_before_artifact_access(pa, pb, copy_workspace, monkeypatch):
    directory, env = copy_workspace(pa)
    other = CreateOrderService(env).create(str(uuid4()), title='Other', listing_text='Other isolated Order')
    from vde.p5.service import P5Service
    calls = []
    original = P5Service.read_decision
    def spy(service, run_id):
        calls.append(run_id)
        return original(service, run_id)
    monkeypatch.setattr(P5Service, 'read_decision', spy)
    code = refused(env, other.id, pa.run_id, {'P6_CROSS_ORDER'})
    assert calls == []
    observations = {'cross_order': {'code': code, 'p5_artifact_reads': 0}}
    mutations = [('approval_hash', 'UPDATE approvals SET target_content_hash=? WHERE target_type=?', ('0'*64, 'TRANSFORMATION_SPEC')),
                 ('spec_context', 'UPDATE transformation_spec_versions SET brief_content_hash=?', ('1'*64,)),
                 ('run_context', 'UPDATE execution_runs SET transformation_approval_id=?', (str(uuid4()),))]
    for label, sql, args in mutations:
        directory, copied = copy_workspace(pa)
        mutate_sql(directory, sql, args)
        observations[label] = refused(copied, pa.order_id, pa.run_id)
    pb_mutations = [
        ('brief_approval_hash', 'UPDATE approvals SET target_content_hash=? WHERE target_type=?', ('0'*64, 'BRIEF')),
        ('spec_approval_hash', 'UPDATE approvals SET target_content_hash=? WHERE target_type=?', ('0'*64, 'TRANSFORMATION_SPEC')),
        ('spec_approval_context', 'UPDATE approvals SET context_brief_content_hash=? WHERE target_type=?', ('0'*64, 'TRANSFORMATION_SPEC')),
        ('missing_brief_approval', 'DELETE FROM approvals WHERE target_type=?', ('BRIEF',)),
        ('fake_approver', 'UPDATE approvals SET approved_by=?', ('TEST_ONLY',)),
        ('future_approval', 'UPDATE approvals SET approved_at=?', ('2099-01-01T00:00:00Z',)),
        ('run_approval', 'UPDATE execution_runs SET transformation_approval_id=?', (str(uuid4()),)),
        ('failed_run', 'UPDATE execution_runs SET status=?', ('failed',)),
        ('selected_spec', 'UPDATE orders SET selected_transformation_spec_version_id=?', (str(uuid4()),)),
        ('asset_checksum', 'UPDATE input_assets SET byte_sha256=?', ('0'*64,)),
    ]
    pb_denials = {}
    for label, sql, args in pb_mutations:
        directory, copied = copy_workspace(pb)
        if label == 'fake_approver':
            before = snapshot(directory); files = payload_hashes(directory)
            with pytest.raises(sqlite3.IntegrityError, match="approved_by='local_user'"):
                mutate_sql(directory, sql, args)
            assert snapshot(directory) == before and payload_hashes(directory) == files
            pb_denials[label] = 'REJECTED by existing SQLite CHECK before forged authority can persist'
            continue
        mutate_sql(directory, sql, args)
        pb_denials[label] = refused(copied, pb.order_id, pb.run_id)
    for label, key, value in [('spec_output', 'output', {**pb.spec.document_json['output'], 'format': 'CSV'}),
                              ('spec_source_sheet', 'inputs', [{**pb.spec.document_json['inputs'][0], 'sheet_name': 'Notes'}])]:
        directory, copied = copy_workspace(pb)
        document = deepcopy(pb.spec.document_json); document[key] = value
        mutate_sql(directory, 'UPDATE transformation_spec_versions SET document_json=?', (json.dumps(document),))
        pb_denials[label] = refused(copied, pb.order_id, pb.run_id)
    observations['CR_P6_002_PB_real_context_denials'] = pb_denials
    record('T13', observations)


def test_T14_missing_report_artifact_metadata_and_health_fail_closed(pa, copy_workspace):
    observations = {}
    for label, sql, args in [('missing_report', 'DELETE FROM qa_reports', ()),
                             ('artifact_metadata', 'UPDATE artifacts SET checksum=? WHERE artifact_type=?', ('0'*64, 'RESULT_CSV'))]:
        directory, env = copy_workspace(pa)
        mutate_sql(directory, sql, args)
        observations[label] = refused(env, pa.order_id, pa.run_id)
    for area, filename, expected in [('.staging', 'unfinished', 'degraded'), ('orders', 'orphan.bin', 'degraded')]:
        directory, env = copy_workspace(pa)
        (directory / area / filename).write_bytes(b'disposable incomplete work')
        recovered = bootstrap(Config(directory))
        assert recovered.health == expected
        before = snapshot(directory)
        observations[area] = refused(env, pa.order_id, pa.run_id)
        with pytest.raises((P6Error, StorageError)):
            CreateOrderService(env).create(str(uuid4()), title='Blocked', listing_text='Must not persist')
        app = new_app(directory)
        assert widget(app, 'button', 'Create DRAFT Order').disabled
        assert len(app.get('download_button')) == 0 and snapshot(directory) == before
    directory, env = copy_workspace(pa)
    mutate_sql(directory, 'UPDATE qa_reports SET overall_status=?', ('FAIL',))
    assert bootstrap(Config(directory)).health == 'blocked'
    observations['blocked'] = refused(env, pa.order_id, pa.run_id)
    record('T14', observations)


def test_T15_passive_rerenders_reprepare_transfer_and_single_snapshot(pa, download_http):
    prepared = pa.prepare_ui()
    before, files = pa.snapshot(), payload_hashes(pa.directory)
    transfers = []
    for _ in range(3):
        healthy_ui(pa.app.run())
        transfers.append(transfer(pa.app, download_http, snapshot_expectation(prepared)))
    previous = prepared
    prepared = pa.prepare_ui()
    assert prepared is not previous and prepared.key == previous.key
    assert isinstance(prepared.result_bytes, bytes) and isinstance(prepared.report_bytes, bytes)
    state = pa.app.session_state.filtered_state
    assert sum(v is prepared for v in state.values()) == 1
    transfers.append(transfer(pa.app, download_http, snapshot_expectation(prepared)))
    widget(pa.app, 'selectbox', 'Download Run').set_value(None).run()
    assert pa.app.session_state.filtered_state.get('p6_delivery_snapshot') is None
    assert len(pa.app.get('download_button')) == 0
    assert pa.snapshot() == before and payload_hashes(pa.directory) == files
    record('T15', {'rerenders': 3, 'http_transfers': transfers, 'counts_unchanged': True,
                   'stored_payload_hashes': files, 'selection_change_clears_snapshot': True})


def test_T16_mime_names_deterministic_json_and_unsafe_name_denial(pa, pb, pd, copy_workspace):
    observations = {}
    for case in (pa, pb, pd):
        prepared = DeliveryService(case.env).prepare(case.order_id, case.run_id)
        report = verified_report(case, prepared)
        assert prepared.report_name == 'qa_report_' + report['report_id'] + '.json'
        assert prepared.report_mime == 'application/json; charset=utf-8'
        assert '/' not in prepared.result_name and '\\' not in prepared.result_name
        assert not any(ord(c) < 32 for c in prepared.result_name)
        assert prepared.result_name.endswith('.xlsx' if case is pb else '.csv')
        if case is not pb:
            assert prepared.result_mime == 'text/csv'
        again = DeliveryService(case.env).prepare(case.order_id, case.run_id)
        assert again.report_bytes == prepared.report_bytes and again.result_bytes == prepared.result_bytes
        observations[case.family] = {'result_name': prepared.result_name, 'mime': prepared.result_mime,
                                     'report_name': prepared.report_name, 'report_sha256': sha(prepared.report_bytes)}
    for name in ('../escape.csv', 'bad\\name.csv', 'bad\nname.csv', 'wrong.xlsx'):
        directory, env = copy_workspace(pa)
        with sqlite3.connect(directory / 'app.sqlite3') as connection:
            raw = connection.execute('SELECT document_json FROM transformation_spec_versions WHERE id=?', (pa.spec.id,)).fetchone()[0]
        doc = json.loads(raw); doc['output']['file_name'] = name
        mutate_sql(directory, 'UPDATE transformation_spec_versions SET document_json=? WHERE id=?', (json.dumps(doc), pa.spec.id))
        observations['unsafe:' + repr(name)] = refused(env, pa.order_id, pa.run_id)
    record('T16', observations)


def test_T17_actual_large_p5_artifact_p6_rss_http_and_resource_denial(tmp_path, download_http, monkeypatch):
    from vde.p6.delivery import Budget
    source = Path(os.environ.get('P6_STRESS_WORKSPACE', '/workspace/p6-work/stress-source'))
    assert source.is_dir(), 'NOT_RUN: actual accepted P5 100000×200 workspace required via P6_STRESS_WORKSPACE'
    original_files = payload_hashes(source)
    original_db_sha = sha((source / 'app.sqlite3').read_bytes())
    directory = tmp_path / 'real-stress-copy'
    shutil.copytree(source, directory)
    env = bootstrap(Config(directory))
    assert env.health == 'ready'
    persisted = snapshot(directory)
    finals = [a for a in persisted['artifacts'] if a['artifact_type'] == 'RESULT_CSV']
    assert len(finals) == 1
    artifact = finals[0]; run_id = artifact['run_id']
    order_id = next(r['order_id'] for r in persisted['execution_runs'] if r['id'] == run_id)
    path = directory / artifact['workspace_relpath']
    assert path.stat().st_size == 40500998
    assert sha(path.read_bytes()) == artifact['checksum'] == '353698a4bab0ffc54633cb3fabad7eb404821b5f97dfeb7eb9676dafec4d9239'
    app = new_app(directory)
    widget(app, 'selectbox', 'Download Order').set_value(order_id).run()
    widget(app, 'selectbox', 'Download Run').set_value(run_id).run()
    healthy_ui(widget(app, 'button', 'Prepare verified download').click().run())
    prepared = app.session_state['p6_delivery_snapshot']
    report = json.loads(prepared.report_bytes)
    assert report['dataset_summary']['row_count'] == 100000
    assert report['dataset_summary']['column_count'] == 200
    resources = prepared.resources
    assert resources['estimated_allocation_bytes'] >= 3 * len(prepared.result_bytes) + len(prepared.report_bytes) + 64 * 1024 * 1024
    assert resources['incremental_peak_rss'] <= 536870912 and resources['rss_samples'] > 0
    with prepared.guard.binding():
        http = transfer(app, download_http, snapshot_expectation(prepared))
    assert prepared.resources['incremental_peak_rss'] <= 536870912
    with pytest.raises(P6Error) as caught:
        DeliveryService(env, budget_factory=lambda: Budget(limit=1)).prepare(order_id, run_id)
    assert caught.value.code == 'P6_DOWNLOAD_RESOURCE_LIMIT'
    # Exercise a failure after Streamlit has really registered its first media
    # object. Clearing only session_state would leave an HTTP-readable payload.
    import streamlit as st
    storage = download_http.reset_storage()
    captured_urls = []
    original_button = st.download_button
    def fail_after_registration(*args, **kwargs):
        result = original_button(*args, **kwargs)
        if not captured_urls:
            captured_urls.extend(storage.get_url(file_id) for file_id in storage._files_by_id)
            raise MemoryError('Deliberate isolated test fault after first real media registration')
        return result
    monkeypatch.setattr(st, 'download_button', fail_after_registration)
    fault_app = new_app(directory)
    widget(fault_app, 'selectbox', 'Download Order').set_value(order_id).run()
    widget(fault_app, 'selectbox', 'Download Run').set_value(run_id).run()
    healthy_ui(widget(fault_app, 'button', 'Prepare verified download').click().run())
    assert captured_urls
    assert fault_app.session_state.filtered_state.get('p6_delivery_snapshot') is None
    assert len(fault_app.get('download_button')) == 0
    failed_transfers = [{'url': url, 'http_status': download_http(url).code} for url in captured_urls]
    assert all(t['http_status'] == 404 for t in failed_transfers)
    monkeypatch.setattr(st, 'download_button', original_button)
    assert snapshot(directory) == persisted and payload_hashes(source) == original_files
    assert sha((source / 'app.sqlite3').read_bytes()) == original_db_sha
    record('T17', {'source_workspace': str(source), 'source_db_sha256': original_db_sha,
                   'source_payload_hashes': original_files, 'provenance': 'Copied existing P5 generated test workspace; no new Approvals issued.',
                   'actual_rows': 100000, 'actual_columns': 200, 'actual_result_bytes': path.stat().st_size,
                   'P6_resources': resources, 'http_transfers': http, 'tightened_budget_denial': caught.value.code,
                   'post_first_registration_allocation_failure_transfers': failed_transfers})


def test_T18_successor_scope_audit_and_negative_mutation_classes(tmp_path):
    from .scope_audit import audit, negative_probes
    result = audit(ROOT)
    probes = negative_probes(ROOT, tmp_path / 'scope-probes')
    record('T18', {'audit': result, 'negative_probes': probes})
    assert result.get('result') == 'PASS', result
    assert probes, 'Negative mutation probes must actually execute'
    rows = probes if isinstance(probes, list) else probes.get('probes', probes.get('results', []))
    assert len(rows) >= 6
    assert all(p.get('result') == 'REJECTED' for p in rows)


def test_T19_documented_linux_launch_restart_and_actual_mac_docker(pa, copy_workspace):
    directory, env = copy_workspace(pa)
    before = snapshot(directory); files = payload_hashes(directory)
    readme = (ROOT / 'docs/p6/README_PILOT.md').read_text()
    assert 'streamlit' in readme and 'docker' in readme.lower() and 'VDE_WORKSPACE' in readme
    observations = {'observed_host': platform.platform(), 'linux_launches': []}
    for _ in range(2):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); port = listener.getsockname()[1]
        command = [sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'src/vde/app.py'),
                   '--server.address=127.0.0.1', '--server.port=' + str(port), '--server.headless=true',
                   '--browser.gatherUsageStats=false']
        child_env = os.environ.copy(); child_env['VDE_WORKSPACE'] = str(directory)
        process = subprocess.Popen(command, cwd=ROOT, env=child_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        status = None
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    with urlopen(f'http://127.0.0.1:{port}/_stcore/health', timeout=1) as response:
                        status = response.status
                        assert response.read() == b'ok'
                    break
                except OSError:
                    if process.poll() is not None:
                        break
                    time.sleep(0.1)
            assert status == 200
        finally:
            process.terminate()
            stdout, stderr = process.communicate(timeout=15)
        observations['linux_launches'].append({'command': command, 'health_http': status,
                                                'stdout': stdout, 'stderr': stderr})
    assert snapshot(directory) == before and payload_hashes(directory) == files
    observations['persisted_order_run_result_qa_after_restart'] = True
    mac_path = os.environ.get('P6_MAC_DOCKER_EVIDENCE')
    if mac_path:
        mac = json.loads(Path(mac_path).read_text())
        observations['mac_docker'] = mac
        assert mac['host_system'] == 'Darwin' and mac['container_system'] == 'Linux'
        assert mac['launch_http_status'] == 200 and mac['restart_http_status'] == 200
        assert mac['workspace_persisted'] is True and mac['explicit_ui_workflow_completed'] is True
        assert mac['commands'] and mac['stdout'] and mac['docker_info']
    else:
        observations['mac_docker'] = {'outcome': 'NOT_RUN', 'reason': 'This execution host is Linux; no actual macOS Docker host evidence is available.'}
    record('T19', observations)
    assert mac_path, 'NOT_RUN — Mac Docker launch/restart and explicit workflow require actual macOS host evidence; Linux smoke passed. Gate B remains blocked.'


def test_T20_exact_twenty_id_inventory_and_pending_release_gate(request):
    items = [i for i in request.session.items if str(i.path) == str(Path(__file__))]
    ids = [dict(i.user_properties).get('p6_id') for i in items]
    assert sorted(ids) == [f'P6-T{i:02}' for i in range(1, 21)]
    assert len(ids) == len(set(ids)) == 20
    checklist = (ROOT / 'docs/p6/RELEASE_CHECKLIST.md').read_text()
    readme = (ROOT / 'docs/p6/README_PILOT.md').read_text()
    combined = (checklist + readme).lower()
    assert 'gate b' in combined and 'pending' in combined
    for limitation in ('13', 'snapshot', 'mac', '512', 'p5-t76', '212', '76'):
        assert limitation in combined, limitation
    assert 'tests/p6' in combined and 'junit' in combined and 'sha' in combined
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    tree = subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip()
    manifest = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in
                sorted((ROOT / 'src/vde/p6').glob('*.py')) + sorted((ROOT / 'tests/p6').glob('*.py'))}
    # This is the executable inventory checkpoint. The validation runner adds
    # completed JUnit/full-regression outcomes and its final evidence manifest
    # after pytest exits; this test cannot assert its own future report exists.
    record('T20', {'collected_ids': ids, 'tested_commit': commit, 'tested_tree': tree,
                   'working_runtime_test_sha256': manifest, 'Gate_B': 'PENDING',
                   'final_junit_and_regression_manifest': 'Generated by run_validation after this invocation; no recursive test run.'})
