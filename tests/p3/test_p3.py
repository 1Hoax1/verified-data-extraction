"""P3-T01..T52 acceptance, approved fixture drivers and real regressions."""
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import unicodedata
from xml.etree import ElementTree as ET
import pytest
import rfc8785
from vde.bootstrap import bootstrap
from vde.config import Config
from vde.contracts import validate, content_hash, BRIEF_FIELDS
from vde.errors import StorageError
from vde.persistence.uow import UnitOfWork
from vde.persistence.repositories import EventLogRepository, OrderRepository
from vde.workflow.errors import WorkflowError
from vde.workflow.service import ManualWorkflow
from vde.workflow.read_model import json_diff
from p3.driver import Scenario, ROOT, load, verify_vectors


def scenario(pack, tmp, patch, number, *, run=True):
    instance = Scenario(pack, tmp / f'f{number:02}', number, patch)
    return instance.run() if run else instance


def test_T01_existing_order(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 1, run=False)
    before = s.snapshot()
    assert [o.id for o in s.service.list_existing_orders()] == ['order-pa']
    assert s.selection.asset_id == 'asset-pa-csv'
    assert before == s.snapshot() and len(before['orders']) == 1


def test_T02_foreign_asset(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 8)
    assert not s.snapshot()['brief_versions']


def test_T03_p2_csv(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 1, run=False)
    expected = load(ROOT / 'pecs/pilot_slice_v1/fixtures/P-A_dirty_csv/input_preview.json')
    assert s.selection.columns == expected['columns'] and s.selection.first_rows == expected['first_rows']
    assert s.selection.selection == {'sheet_name': None, 'csv_options': {'encoding': 'CP1251', 'delimiter': ',', 'header_row': 0}}


def test_T04_manual_transition(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 27)
    before = s.snapshot()
    s.service.begin_manual_review(s.order().id, s.order())
    assert s.order().status == 'ANALYZING' and len(s.snapshot()['event_log']) == len(before['event_log']) + 1
    s.service.request_clarification(s.order().id, s.order())
    assert s.order().status == 'NEEDS_CLARIFICATION'
    s.service.begin_manual_review(s.order().id, s.order())
    assert s.order().status == 'ANALYZING'


def test_T05_brief_golden(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 1, run=False)
    doc = s.service.validate_brief(s.docs['brief'], s.order(), s.asset)
    assert doc == s.docs['brief'] and doc['content_hash'] == s.refs['expected_brief_hash']
    validate(doc, 'brief_version')
    nullable = deepcopy(doc); nullable['data_quality_expectations']['duplicate_key'] = None
    validate(s.service.validate_brief(nullable, s.order(), s.asset), 'brief_version')


def test_T06_missing_objective(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 3)


def test_T07_forbidden_approval_property(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 4)
    from jsonschema.exceptions import ValidationError
    document = load(ROOT / 'pecs/pilot_slice_v1/fixtures/P-C_approval_safety/invalid_examples/brief_with_approved_at.schema_invalid.json')
    with pytest.raises(ValidationError): validate(document, 'brief_version')


def test_T08_nfc_and_collision(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 6)
    s = scenario(p3_pack, tmp_path, monkeypatch, 7)
    raw = s.docs['brief']['fields'][1]['output_name']
    assert unicodedata.normalize('NFC', raw) != raw and 'e\u0301' in raw
    stored = s.service.view_current_approvals(s.order().id).brief
    assert stored.document['fields'][1]['output_name'] == unicodedata.normalize('NFC', raw)
    assert stored.content_hash == 'efc2f1cb05362740737a7e1e3b70af6725065a51fa4a54d72f6a098d62aa4157'
    raw_digest = hashlib.sha256(rfc8785.dumps({k: s.docs['brief'][k] for k in BRIEF_FIELDS})).hexdigest()
    assert raw_digest == s.fixture['normalization_oracle']['expected_non_normalized_raw_semantic_sha256_test_only']
    assert len({raw_digest, stored.content_hash, s.refs['expected_brief_hash']}) == 3
    document = deepcopy(s.docs['brief']); del document['fields'][0]['output_name']
    assert s.service.validate_brief(document, s.order(), s.asset)['fields'][0]['output_name'] == document['fields'][0]['name']


def test_T09_nested_criterion(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 5)


def test_T10_immutable_brief(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 24, run=False)
    s.docs['brief']['version_number'] = 1  # Stale draft counter is allocated under UoW.
    s.run()
    with s.service._uow() as uow:
        records = uow.briefs.list_for_order(s.refs['order_id'])
        assert [r.version_number for r in records] == [1, 2]
        assert records[0].document_json == s.base['brief']
        assert not hasattr(uow.briefs, 'update')
        for record in records:
            assert record.content_hash == content_hash(record.document_json, 'brief_version')
            assert record.id == record.document_json['version_id']


def test_T11_selected_brief_stage(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 9, run=False)
    assert s.order().status == 'READY_FOR_APPROVAL' and s.order().approval_stage == 'BRIEF_PENDING'
    assert any(e['event_type'] == 'BRIEF_VERSION_PUBLISHED' for e in s.snapshot()['event_log'])


def test_T12_explicit_brief_approval(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 22)
    with s.service._uow() as uow:
        approval = uow.approvals.list_for_order(s.refs['order_id'])[0]
    assert approval.target_type == 'BRIEF' and approval.approved_by == 'local_user'
    assert approval.context_brief_version_id is approval.context_brief_content_hash is None
    assert s.order().approval_stage == 'TRANSFORMATION_PENDING'


def test_T13_bad_brief_hash_guard(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 10)


def test_T14_brief_duplicate(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 22)
    assert s.results[0] == s.results[1]
    assert sum(e['event_type'] == 'BRIEF_APPROVED' for e in s.snapshot()['event_log']) == 1


def test_T15_p0_context_schema(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 9)
    from jsonschema.exceptions import ValidationError
    document = load(ROOT / 'pecs/pilot_slice_v1/fixtures/P-C_approval_safety/invalid_examples/brief_approval_with_context.schema_invalid.json')
    with pytest.raises(ValidationError): validate(document, 'approval')


def test_T16_spec_golden(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 25, run=False)
    with s.service._uow() as uow:
        context = s.service._brief_approval(uow, uow.orders.get(s.refs['order_id']))
    doc = s.service.validate_spec(s.base['spec'], s.order(), context, s.selection)
    assert doc == s.base['spec'] and doc['content_hash'] == s.refs['expected_spec_hash']


def test_T17_spec_requires_brief_approval(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 11)


def test_T18_csv_options_persisted(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 1)
    assert s.service.view_current_approvals(s.order().id).spec.document['inputs'] == s.base['spec']['inputs']


def test_T19_xlsx_selection(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 2)
    source = s.service.view_current_approvals(s.order().id).spec.document['inputs'][0]
    assert source['sheet_name'] == 'Orders' and source['csv_options'] is None
    assert s.selection.warnings and s.selection.warnings[0]['code'] == 'XLSX_FORMULA_PRESENT'
    scenario(p3_pack, tmp_path, monkeypatch, 18)
    scenario(p3_pack, tmp_path, monkeypatch, 19)


def test_T20_no_auto_encoding(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 12)


def test_T21_exact_brief_context(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 13)


def test_T22_criterion_references(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 15)


def test_T23_closed_operations(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 16)
    scenario(p3_pack, tmp_path, monkeypatch, 17)
    # Full P0 P-D unknown-operation and script negatives remain schema-invalid.
    from jsonschema.exceptions import ValidationError
    directory = ROOT / 'pecs/pilot_slice_v1/fixtures/P-D_errors_and_qa_blockers'
    for case in load(directory / 'invalid_manifest.json')['items']:
        document = load(directory / case['path'])
        with pytest.raises(ValidationError):
            validate(document, case['schema'].removesuffix('.schema.json'))


def test_T24_spec_append_selected(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 25, run=False)
    assert s.order().selected_transformation_spec_version_id == 'transform-pa-v1'
    assert any(e['event_type'] == 'TRANSFORMATION_SPEC_PUBLISHED' for e in s.snapshot()['event_log'])


def test_T25_spec_revision_before_final(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 25)
    assert not any(a['target_type'] == 'TRANSFORMATION_SPEC' for a in s.snapshot()['approvals'])
    assert s.service.view_current_approvals(s.order().id).brief.approval_id


def test_T26_atomic_final(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 1)
    state = s.snapshot()
    assert s.order().status == 'APPROVED' and s.order().approval_stage == 'COMPLETE'
    assert len(state['approvals']) == 2
    assert sum(e['event_type'] == 'TRANSFORMATION_SPEC_APPROVED' for e in state['event_log']) == 1


def test_T27_spec_approval_guards(p3_pack, tmp_path, monkeypatch):
    for number in (20, 21, 38):
        scenario(p3_pack, tmp_path, monkeypatch, number)


def test_T28_final_duplicate(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 23)
    assert s.results[0] == s.results[1]
    assert sum(e['event_type'] == 'TRANSFORMATION_SPEC_APPROVED' for e in s.snapshot()['event_log']) == 1
    before = s.snapshot(); s.ui().run(); assert s.snapshot() == before


def test_T29_final_commit_rollback(p3_pack, tmp_path, monkeypatch):
    with monkeypatch.context() as patch:
        scenario(p3_pack, tmp_path, patch, 29)
    # Separate actual connection.commit failure after all repository mutations.
    with monkeypatch.context() as patch:
        s = scenario(p3_pack, tmp_path / 'commit', patch, 29, run=False)
        before = s.snapshot(); order = s.order()
        from vde.persistence import uow as module
        connect = module.connect
        class CommitFailure:
            def __init__(self, connection): self.connection = connection
            def __getattr__(self, key): return getattr(self.connection, key)
            def commit(self): raise sqlite3.OperationalError('injected commit failure')
        patch.setattr(module, 'connect', lambda path: CommitFailure(connect(path)))
        with pytest.raises(StorageError) as error:
            s.service.approve_spec_and_finish(order.id, order.selected_transformation_spec_version_id, order)
        validate(error.value.public(), 'execution_error')
        patch.undo()
        assert s.snapshot() == before


def test_T30_read_only_handoff(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 1)
    before = s.snapshot(); dto = s.service.p4_handoff(s.order().id)
    assert dto.asset_id == s.asset.id and dto.byte_sha256 == s.asset.byte_sha256
    assert dto.brief_content_hash == s.refs['expected_brief_hash']
    assert dto.transformation_content_hash == s.refs['expected_spec_hash']
    assert dto.brief_approval_id != dto.transformation_approval_id
    assert s.snapshot() == before


def test_T31_source_integrity(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 14)
    scenario(p3_pack, tmp_path, monkeypatch, 31)


def test_T32_brief_revision_invalidates_selection(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 24, run=False)
    before = s.snapshot(); s.run()
    assert before['approvals'] == s.snapshot()['approvals']
    assert s.order().selected_transformation_spec_version_id is None


def test_T33_handoff_missing_before_io(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 37, run=False)
    monkeypatch.setattr(s.env.workspace, 'read_verified', lambda *a: pytest.fail('Input I/O before missing Approval check'))
    s.run()


def test_T34_p0_transition_graph(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 26)
    scenario(p3_pack, tmp_path, monkeypatch, 27)


def test_T35_event_cas_rollback(p3_pack, tmp_path, monkeypatch):
    for number in (28, 29, 30):
        with monkeypatch.context() as patch:
            scenario(p3_pack, tmp_path, patch, number)
    # Every publishing/approval command rolls back its writes on EventLog failure.
    for number, method in [(27, 'begin_manual_review'), (9, 'publish_brief'),
                           (22, 'approve_brief'), (25, 'publish_spec'), (29, 'approve_spec_and_finish'),
                           (27, 'request_clarification')]:
        with monkeypatch.context() as patch:
            s = scenario(p3_pack, tmp_path / method, patch, number, run=False)
            if method == 'publish_brief':
                s.docs['brief']['version_id'] = 'brief-pa-v2'
            if method == 'request_clarification':
                s.service.begin_manual_review(s.order().id, s.order())
            before = s.snapshot()
            s.fault('inject_event_append_failure')
            with pytest.raises(StorageError):
                s.api({'method': method})
            assert s.snapshot() == before
    with monkeypatch.context() as patch:
        s = scenario(p3_pack, tmp_path / 'late-cas', patch, 29, run=False)
        before = s.snapshot(); order = s.order()
        def fail_cas(*args, **kwargs): raise StorageError('Injected late CAS failure')
        patch.setattr(OrderRepository, 'update', fail_cas)
        with pytest.raises(StorageError):
            s.service.approve_spec_and_finish(order.id, order.selected_transformation_spec_version_id, order)
        assert s.snapshot() == before


def test_T36_crash_boundaries(p3_pack, tmp_path, monkeypatch):
    results = []
    for number, role in [(28, 'brief'), (29, 'spec')]:
        for phase in ['before_commit', 'after_commit']:
            s = scenario(p3_pack, tmp_path / (role + phase), monkeypatch, number, run=False)
            before = s.snapshot()
            proc = subprocess.run([sys.executable, str(ROOT / 'tests/p3/restart_probe.py'),
                                   str(s.env.workspace.root), s.order().id, role, phase], cwd=ROOT, capture_output=True, text=True)
            assert proc.returncode == (76 if phase == 'before_commit' else 77), proc.stderr
            env = bootstrap(Config(s.env.workspace.root)); assert env.health == 'ready'
            after = s.restart()['snapshot']
            if phase == 'before_commit':
                assert after == before
            else:
                assert len(after['approvals']) == len(before['approvals']) + 1
                assert len(after['event_log']) == len(before['event_log']) + 1
                order = s.order()
                assert order.approval_stage == ('TRANSFORMATION_PENDING' if role == 'brief' else 'COMPLETE')
                assert order.status == ('READY_FOR_APPROVAL' if role == 'brief' else 'APPROVED')
            results.append({'command': role, 'phase': phase, 'exit_code': proc.returncode, 'result': 'PASS'})
    (ROOT / 'docs/p3/validation/crash-restart-results.json').write_text(json.dumps(results, indent=2) + '\n')


def test_T37_process_restart(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 35)


def test_T38_corrupt_authoritative_json(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 34)
    assert bootstrap(Config(s.env.workspace.root)).health == 'blocked'


def element(app, kind, label):
    return next(e for e in getattr(app, kind) if e.label == label)


def test_T39_streamlit_workflow(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 1, run=False)
    app = s.ui()
    def act(kind, label, value=None):
        widget = element(app, kind, label)
        if kind == 'button': widget.click()
        else: widget.set_value(value)
        app.run(timeout=30); assert not app.exception
    act('selectbox', 'P3 registered input', s.asset.id)
    act('selectbox', 'P3 encoding', 'CP1251')
    act('selectbox', 'P3 delimiter', ',')
    act('button', 'Verify P3 input and preview')
    act('button', 'Begin manual review')
    act('text_area', 'Brief JSON draft', json.dumps(s.base['brief']))
    act('button', 'Validate Brief draft')
    assert not app.error
    act('button', 'Save new Brief version')
    assert s.order().approval_stage == 'BRIEF_PENDING' and not s.snapshot()['approvals']
    act('checkbox', 'Confirm this exact Brief ID and hash', True)
    act('button', 'I approve this Brief version')
    brief = s.service.view_current_approvals(s.order().id).brief
    doc = deepcopy(s.base['spec']); doc['brief_version_id'] = brief.version_id; doc['brief_content_hash'] = brief.content_hash
    act('text_area', 'TransformationSpec JSON draft', json.dumps(doc))
    act('button', 'Validate TransformationSpec draft')
    assert not app.error
    act('button', 'Save new TransformationSpec version')
    assert s.order().status == 'READY_FOR_APPROVAL' and len(s.snapshot()['approvals']) == 1
    act('checkbox', 'Confirm this exact Spec ID, hash and approved Brief context', True)
    act('button', 'I approve TransformationSpec')
    assert s.order().status == 'APPROVED' and s.order().approval_stage == 'COMPLETE'
    assert len(s.snapshot()['approvals']) == 2 and not app.error
    before = s.snapshot(); app.run(); assert not app.exception and before == s.snapshot()


def test_T40_passive_reruns(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 36)
    app = s.ui(); before = s.snapshot()
    element(app, 'selectbox', 'P3 registered input').set_value(s.asset.id).run()
    for _ in range(3): app.run(); assert not app.exception
    assert before == s.snapshot()


def test_T41_health(p3_pack, tmp_path, monkeypatch):
    for number in (32, 33):
        s = scenario(p3_pack, tmp_path, monkeypatch, number)
        before = s.snapshot()
        with pytest.raises(StorageError): s.service.list_existing_orders()
        opted = ManualWorkflow(s.env, allow_degraded_read=True)
        if number == 32:
            assert opted.view_current_approvals(s.refs['order_id']).brief
        else:
            with pytest.raises(StorageError): opted.view_current_approvals(s.refs['order_id'])
        with pytest.raises(StorageError): opted.begin_manual_review(s.refs['order_id'], s.order())
        assert before == s.snapshot()


def test_T42_review_diff(p3_pack, tmp_path, monkeypatch):
    for number, role, pointer in [(24, 'brief', '/objective'), (25, 'spec', '/output/file_name')]:
        s = scenario(p3_pack, tmp_path, monkeypatch, number)
        view = getattr(s.service.view_current_approvals(s.order().id), role)
        assert any(d['path'] == pointer for d in view.diff)
        app = s.ui(); rendered = '\n'.join(e.value for e in app.json)
        assert view.version_id in rendered and view.content_hash in rendered and pointer in rendered
    assert json_diff({'z': None}, {'a': 1}) == [
        {'path': '/a', 'change': 'add', 'after': 1}, {'path': '/z', 'change': 'remove', 'before': None}]


def test_T43_approved_ui_readonly(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 26)
    before = s.snapshot(); app = s.ui()
    for label in ['Save new Brief version', 'Save new TransformationSpec version', 'Begin manual review']:
        assert element(app, 'button', label).disabled
    assert element(app, 'selectbox', 'P3 registered input').disabled
    assert before == s.snapshot()


def test_T44_brief_revision_setup(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 24, run=False)
    assert s.order().status == 'READY_FOR_APPROVAL'
    assert not any(a['target_type'] == 'TRANSFORMATION_SPEC' for a in s.snapshot()['approvals'])
    s.run(); assert s.order().approval_stage == 'BRIEF_PENDING'


def test_T45_spec_revision_setup(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 25, run=False)
    before = s.snapshot(); s.run()
    assert before['approvals'] == s.snapshot()['approvals']
    assert len(s.snapshot()['transformation_spec_versions']) == 2


def test_T46_p0_pa(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 1)
    view = s.service.view_current_approvals(s.order().id)
    assert view.brief.document == s.base['brief'] and view.spec.document == s.base['spec']


def test_T47_p0_pb(p3_pack, tmp_path, monkeypatch):
    s = scenario(p3_pack, tmp_path, monkeypatch, 2)
    expected = load(ROOT / 'pecs/pilot_slice_v1/fixtures/P-B_xlsx_sheet/input_preview.json')
    assert s.selection.columns == expected['columns'] and s.selection.first_rows == expected['first_rows']
    view = s.service.view_current_approvals(s.order().id)
    assert view.brief.document == s.base['brief'] and view.spec.document == s.base['spec']


def test_T48_hash_vectors(p3_pack, tmp_path, monkeypatch):
    scenario(p3_pack, tmp_path, monkeypatch, 39)
    verify_vectors()


def regression(phase, count):
    output = ROOT / 'docs/p3/validation'
    historical = ROOT / 'docs/p2/validation'
    originals = {p: p.read_bytes() for p in historical.iterdir() if p.is_file()}
    command = [sys.executable, '-m', 'pytest', 'tests/' + phase, '-q', '--junitxml=' + str(output / (phase + '-results.xml'))]
    try:
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        (output / (phase + '-run.log')).write_text('COMMAND ' + json.dumps(command) + '\n' + proc.stdout + proc.stderr)
        if phase == 'p2':
            for name in ['fixture-verification.json', 'rss-csv.json', 'rss-xlsx.json']:
                shutil.copy(historical / name, output / name)
    finally:
        for path, data in originals.items(): path.write_bytes(data)
        for path in historical.iterdir():
            if path.is_file() and path not in originals: path.unlink()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    suite = ET.parse(output / (phase + '-results.xml')).getroot()[0]
    assert (suite.get('tests'), suite.get('failures'), suite.get('errors'), suite.get('skipped')) == (str(count), '0', '0', '0')
    assert {p.get('value') for p in suite.findall('.//property') if p.get('name') == phase + '_id'} == {phase.upper() + f'-T{i:02}' for i in range(1, count + 1)}


def test_T49_p1_regression():
    regression('p1', 42)


def test_T50_p2_regression():
    regression('p2', 54)


def test_T51_whole_application_scope(p3_pack, tmp_path, monkeypatch):
    from scope_policy import audit_application, audit_repository_paths
    base_project = subprocess.check_output(['git', 'show', '129300728c446b82eaeafe1068e27339eb7176dd:pyproject.toml'], cwd=ROOT, text=True)
    base_lock = subprocess.check_output(['git', 'show', '129300728c446b82eaeafe1068e27339eb7176dd:uv.lock'], cwd=ROOT, text=True)
    audit_application(ROOT, base_project, base_lock, phase='p3')
    changed = subprocess.check_output(['git', 'diff', '--name-only', 'ba73d05'], cwd=ROOT, text=True).splitlines()
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=ROOT, text=True).splitlines()
    audit_repository_paths(changed + untracked)
    scratch = tmp_path / 'audit'
    shutil.copytree(ROOT / 'src', scratch / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.egg-info'))
    for name in ['pyproject.toml', 'uv.lock']: shutil.copy(ROOT / name, scratch / name)
    target = scratch / 'src/vde/workflow/service.py'; original = target.read_text()
    snippets = ['import requests', 'import httpx', 'import socket', 'import sqlalchemy', 'import openai',
                'import telegram', 'import playwright', 'import celery', 'import fastapi', 'import pandas',
                'from urllib.request import urlopen', '__import__("requests")', 'exec("pass")', 'eval("1")',
                'import subprocess; subprocess.run(["echo", "code"])', 'def ingest_json(raw): return raw',
                'uow.orders.add(record)', 'uow.runs.append(record)', 'uow.artifacts._append_promoted(record)',
                'uow.reports.append(record)', 'workbook.save("output.xlsx")', 'def execute_pipeline(): pass',
                'import importlib; importlib.import_module("openai")']
    for snippet in snippets:
        target.write_text(original + '\n' + snippet + '\n')
        with pytest.raises(AssertionError, match='Unapproved'): audit_application(scratch, base_project, base_lock, phase='p3')
    target.write_text(original)
    for path in ['src/vde/engine.py', 'src/vde/workflow/worker.py', 'src/vde/ingestion/url_reader.py', 'src/vde/persistence/migrations/002_p3.sql']:
        file = scratch / path; file.write_text('# forbidden' if path.endswith('.py') else 'CREATE TABLE drafts(id);')
        with pytest.raises(AssertionError): audit_application(scratch, base_project, base_lock, phase='p3')
        file.unlink()
    for path in ['src/vde/ingestion/local.py', 'src/vde/storage.py', 'src/vde/persistence/migrations/001_p1_baseline.sql']:
        file = scratch / path; data = file.read_text(); file.write_text(data + '\n# forbidden drift\n')
        with pytest.raises(AssertionError, match='drift'): audit_application(scratch, base_project, base_lock, phase='p3')
        file.write_text(data)
    project = scratch / 'pyproject.toml'; data = project.read_text()
    project.write_text(data.replace('"openpyxl==3.1.5"', '"openpyxl==3.1.5", "sqlalchemy==2.0.0"'))
    with pytest.raises(AssertionError, match='Unapproved'): audit_application(scratch, base_project, base_lock, phase='p3')
    project.write_text(data)
    for path in ['worker.py', 'DECISIONS.md', 'pecs/pilot_slice_v1/contracts/approval.schema.json', 'src/vde/storage.py']:
        with pytest.raises(AssertionError): audit_repository_paths([path])
    s = scenario(p3_pack, tmp_path / 'fixture', monkeypatch, 40)
    with s.service._uow() as uow:
        tables = {r[0] for r in uow.connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        assert tables == {'schema_migrations', 'orders', 'input_assets', 'brief_versions', 'transformation_spec_versions',
                          'approvals', 'execution_runs', 'artifacts', 'qa_reports', 'event_log'}
    audit_application(scratch, base_project, base_lock, phase='p3')


def test_T52_pack_fixture_integrity(p3_pack):
    command = [sys.executable, str(p3_pack / 'tools/verify_p3_fixture_reachability.py'), '--repo', str(ROOT)]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (ROOT / 'docs/p3/validation/fixture-verifier.log').write_text('COMMAND ' + json.dumps(command) + '\n' + proc.stdout + proc.stderr)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result['fixture_count'] == 40 and result['p0_checkout_hash_verification'] == 'PASS'
    assert result['approval_wrong_context_order_hash_checks'] == 'PASS_5_OF_5'
    assert len(result['corrected_approval_mutants_rejected']) == 5
    assert len(list((p3_pack / 'fixtures/scenarios').glob('*.json'))) == 40
    for directory in ['pecs/pilot_slice_v1', 'docs/p1/v1.0', 'docs/p2/v1.0', 'docs/p3/v1.0']:
        assert not subprocess.check_output(['git', 'diff', 'ba73d05', '--', directory], cwd=ROOT)
