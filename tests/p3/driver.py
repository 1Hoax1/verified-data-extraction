"""Exact approved fixture setup/action layers; test-only SQL/fault/UI drivers."""
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unicodedata
import pytest
import rfc8785
from jsonschema.exceptions import ValidationError
from streamlit.testing.v1 import AppTest
from vde.bootstrap import bootstrap
from vde.config import Config
from vde.contracts import validate, hash_payload, BRIEF_FIELDS
from vde.errors import StorageError
from vde.models import OrderRecord, ApprovalRecord
from vde.persistence.uow import UnitOfWork
from vde.persistence.repositories import EventLogRepository
from vde.storage import Storage
from vde.workflow.errors import WorkflowError
from vde.ingestion.diagnostics import IngestionError
from vde.workflow.service import ManualWorkflow

ROOT = Path(__file__).resolve().parents[2]
TABLES = ('orders', 'input_assets', 'brief_versions', 'transformation_spec_versions',
          'approvals', 'event_log', 'execution_runs', 'artifacts', 'qa_reports')


def load(path):
    return json.loads(Path(path).read_text())


class Scenario:
    def __init__(self, pack, directory, number, monkeypatch):
        self.fixture = load(next((pack / 'fixtures/scenarios').glob(f'P3-F{number:02}_*.json')))
        self.monkeypatch = monkeypatch
        self.number = number
        self.refs = self.fixture['input_refs']
        self.docs = {key: load(ROOT / self.refs[key]) for key in ('brief', 'spec', 'brief_approval', 'spec_approval')}
        self.base = deepcopy(self.docs)
        self.env = bootstrap(Config(directory / 'workspace'))
        assert self.env.health == 'ready'
        initial = self.fixture['initial_state']
        with UnitOfWork(self.env.database, self.env.workspace) as uow:
            uow.orders.add(OrderRecord(self.refs['order_id'], 'Manual test', 'Existing local Order',
                                      '2026-07-12T08:00:00Z', '2026-07-12T08:00:00Z'))
            if 'secondary_order' in initial:
                uow.orders.add(OrderRecord(initial['secondary_order']['id'], 'Other', 'Foreign Order',
                                          '2026-07-12T08:00:00Z', '2026-07-12T08:00:00Z'))
        asset = initial['input_asset']
        raw = (ROOT / self.refs['input']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == asset['raw_bytes_sha256']
        self.asset = Storage(self.env.database, self.env.workspace).register_input(
            id=asset['id'], order_id=asset['order_id'], original_filename=asset['original_filename'],
            data=raw, created_at=asset['created_at'])
        assert asdict(self.asset) == {k: asset[k] for k in asdict(self.asset) if k != 'byte_sha256'} | {'byte_sha256': asset['raw_bytes_sha256']}
        self.service = ManualWorkflow(self.env)
        opts = initial['reading_options']
        options = {'source_type': opts['source_type'], 'sheet_name': opts['sheet_name'],
                   'csv_options': None if opts['source_type'] == 'LOCAL_XLSX' else
                   {k: opts[k] for k in ('encoding', 'delimiter', 'header_row')}}
        self.selection = self.service.choose_input(self.refs['order_id'], self.refs['asset_id'], options)
        for action in initial['setup_actions']:
            if action['layer'] == 'P1_TEST_SETUP':
                assert action['method'] == 'create_order_and_register_input'
            else:
                assert action['layer'] == 'P3_API'
                self.api(action, base=True)
        self.assert_state(initial=True)
        # Deterministic patches affect in-memory copies only, never P0 bytes.
        for patch in self.fixture['patches']:
            parts = patch['json_pointer'].strip('/').split('/')
            target = self.docs[patch['target']]
            for key in parts[:-1]:
                target = target[int(key)] if isinstance(target, list) else target[key]
            key = int(parts[-1]) if isinstance(target, list) else parts[-1]
            if patch['op'] == 'remove':
                del target[key]
            else:
                target[key] = deepcopy(patch['value'])
        if number in (24, 25):
            role = 'brief' if number == 24 else 'spec'
            self.docs[role]['version_id'] = 'brief-pa-v2' if role == 'brief' else 'transform-pa-v2'
            self.docs[role]['version_number'] = 2
        self.stale = None
        self.results = []

    def order(self):
        with UnitOfWork(self.env.database, self.env.workspace) as uow:
            return uow.orders.get(self.refs['order_id'])

    def snapshot(self):
        with UnitOfWork(self.env.database, self.env.workspace) as uow:
            return {table: [dict(row) for row in uow.connection.execute(f'SELECT * FROM {table} ORDER BY 1')]
                    for table in TABLES}

    def assert_state(self, *, initial=False):
        expected = self.fixture['initial_state'] if initial else self.fixture['expected']['final_state']
        with UnitOfWork(self.env.database, self.env.workspace) as uow:
            order = uow.orders.get(self.refs['order_id'])
            briefs = uow.briefs.list_for_order(order.id)
            specs = uow.specs.list_for_order(order.id)
            approvals = uow.approvals.list_for_order(order.id)
        if initial:
            assert {k: getattr(order, k) for k in expected['order']} == expected['order']
            for actual, key in [(briefs, 'brief_versions'), (specs, 'transformation_spec_versions')]:
                records = expected['persisted_versions'][key]
                assert len(actual) == len(records)
                for record, wanted in zip(actual, records):
                    assert all(getattr(record, k) == v for k, v in wanted.items() if k != 'source')
            assert len(approvals) == len(expected['persisted_approvals'])
            for wanted in expected['persisted_approvals']:
                record = next(a for a in approvals if (a.target_type, a.target_version_id) ==
                              (wanted['target_type'], wanted['target_version_id']))
                assert all(getattr(record, k) == v for k, v in wanted.items() if k not in {'ref', 'id_binding', 'created_by'})
            return
        assert order.status == expected['order_status'] and order.approval_stage == expected['approval_stage']
        assert order.selected_brief_version_id == expected['selected_brief_version_id']
        assert order.selected_transformation_spec_version_id == expected['selected_transformation_spec_version_id']
        assert [r.id for r in briefs] == expected['brief_version_ids']
        assert [r.id for r in specs] == expected['transformation_spec_version_ids']
        assert sum(a.target_type == 'BRIEF' for a in approvals) == expected['persisted_brief_approval_count']
        assert sum(a.target_type == 'TRANSFORMATION_SPEC' for a in approvals) == expected['persisted_transformation_spec_approval_count']
        view = self.service.view_current_approvals(order.id)
        assert bool(view.brief and view.brief.approval_id) == expected['selected_brief_approval_valid']
        assert bool(view.spec and view.spec.approval_id) == expected['selected_spec_approval_valid']

    def api(self, action, *, base=False):
        method = action['method']
        order = self.order()
        expected = self.stale or order if hasattr(self, 'stale') else order
        documents = self.base if base else self.docs
        service = self.service
        if method in {'begin_manual_review', 'request_clarification'}:
            return getattr(service, method)(order.id, expected)
        if method in {'publish_brief', 'publish_spec'}:
            return getattr(service, method)(order.id, documents['brief' if method == 'publish_brief' else 'spec'], expected)
        if method in {'approve_brief', 'approve_spec_and_finish'}:
            identity = order.selected_brief_version_id if method == 'approve_brief' else order.selected_transformation_spec_version_id
            return getattr(service, method)(order.id, identity, expected)
        if method == 'validate_spec':
            with service._uow() as uow:
                context = service._brief_approval(uow, order)
            return service.validate_spec(documents['spec'], order, context, self.selection)
        if method in {'p4_handoff', 'view_current_approvals'}:
            return getattr(service, method)(order.id)
        raise AssertionError('Unknown approved action ' + method)

    def fault(self, method):
        if method == 'inject_event_append_failure':
            def fail(*args, **kwargs):
                raise StorageError('Injected EventLog failure')
            self.monkeypatch.setattr(EventLogRepository, 'append', fail)
        elif method == 'inject_stale_expected_order':
            self.stale = replace(self.order(), notes='stale command snapshot')
        elif method in {'tamper_input_payload', 'bootstrap_blocked'}:
            self.env.workspace.path(self.asset.workspace_relpath).write_bytes(b'tampered')
            if method == 'bootstrap_blocked':
                self.env = bootstrap(Config(self.env.workspace.root))
                assert self.env.health == 'blocked'
                self.service = ManualWorkflow(self.env)
        elif method == 'bootstrap_degraded':
            self.env.workspace.path('.staging/incomplete').write_bytes(b'pending')
            self.env = bootstrap(Config(self.env.workspace.root))
            assert self.env.health == 'degraded'
            self.service = ManualWorkflow(self.env)
        elif method == 'corrupt_authoritative_brief_json':
            with UnitOfWork(self.env.database, self.env.workspace) as uow:
                brief = uow.briefs.get(self.base['brief']['version_id'])
                document = deepcopy(brief.document_json)
                document['objective'] = 'tampered authoritative content'
                uow.connection.execute('UPDATE brief_versions SET document_json=? WHERE id=?', (json.dumps(document), brief.id))
        else:
            raise AssertionError('Unknown fault ' + method)

    def ui(self):
        self.monkeypatch.setenv('VDE_WORKSPACE', str(self.env.workspace.root))
        app = AppTest.from_file(str(ROOT / 'src/vde/app.py')).run(timeout=30)
        assert not app.exception
        if self.env.health != 'blocked':
            next(e for e in app.checkbox if e.label == 'Open manual workflow').set_value(True).run(timeout=30)
            assert not app.exception
        return app

    def restart(self):
        result = subprocess.run([sys.executable, str(ROOT / 'tests/p3/restart_probe.py'),
                                 str(self.env.workspace.root), self.refs['order_id']],
                                cwd=ROOT, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        before = self.snapshot()
        assert json.loads(result.stdout)['snapshot'] == before
        return json.loads(result.stdout)

    def run(self):
        expected_code = self.fixture['expected']['code_or_reason']
        rejected = False
        for action in self.fixture['actions']:
            layer, method = action['layer'], action['method']
            if layer == 'TEST_FAULT':
                self.fault(method)
                continue
            before = self.snapshot()
            try:
                if layer == 'P3_API':
                    result = self.api(action)
                elif layer == 'P0_SCHEMA':
                    with pytest.raises(ValidationError):
                        validate(self.docs['brief_approval'], 'approval')
                    result = 'P0_SCHEMA_REJECTED'
                    rejected = True
                    assert before == self.snapshot()
                elif layer == 'P1_REPOSITORY_GUARD':
                    doc = self.docs['brief_approval' if self.number == 10 else 'spec_approval']
                    with UnitOfWork(self.env.database, self.env.workspace) as uow:
                        uow.approvals.append(ApprovalRecord.from_document(doc))
                    raise AssertionError('Guard accepted invalid Approval')
                elif layer == 'TEST_DRIVER' and method == 'process_restart':
                    result = self.restart()
                elif layer == 'TEST_DRIVER' and method == 'verify_p0_hash_vectors_and_nfc':
                    result = verify_vectors()
                elif layer == 'UI_DRIVER':
                    app = self.ui()
                    if method == 'passive_rerun':
                        app.run()
                        assert not app.exception
                    assert before == self.snapshot()
                    assert not any(not b.disabled and b.label.lower() in {'execute', 'export', 'run qa'} for b in app.button)
                    result = 'NO_WRITE'
                else:
                    raise AssertionError('Unknown fixture driver layer')
                self.results.append(result)
            except (WorkflowError, StorageError, IngestionError) as exc:
                public = exc.public()
                validate(public, 'execution_error')
                assert public['code'] == expected_code
                expected_category = 'STORAGE' if isinstance(exc, StorageError) else (
                    'STATE' if public['code'] == 'STATE_INVALID_TRANSITION' else
                    'INGESTION' if public['code'] == 'INPUT_NOT_FOUND' else
                    'VALIDATION' if public['code'].startswith('VALIDATION_') or public['code'] in {'INVALID_OPERATION', 'INVALID_PARAMETER'} else 'APPROVAL')
                assert public['category'] == expected_category
                assert public['stage'] == {'STORAGE': 'STORAGE', 'STATE': 'ORDER', 'INGESTION': 'INGESTION', 'APPROVAL': 'APPROVAL'}.get(
                    expected_category, 'BRIEF_VALIDATION' if public['code'] in {'VALIDATION_BRIEF_SCHEMA', 'VALIDATION_ACCEPTANCE_CRITERION'} else 'TRANSFORMATION_VALIDATION')
                assert before == self.snapshot(), 'Rejected command has partial business writes'
                rejected = True
                self.results.append(public)
                break
        assert rejected == (self.fixture['expected']['status'] in {'REJECT', 'ROLLBACK'})
        # Corrupt authoritative JSON and health-blocked states cannot be trusted loaded.
        if self.number not in {32, 33, 34}:
            self.assert_state()
        else:
            expected = self.fixture['expected']['final_state']
            snapshot = self.snapshot()
            order = next(o for o in snapshot['orders'] if o['id'] == self.refs['order_id'])
            assert (order['status'], order['approval_stage'], order['selected_brief_version_id'],
                    order['selected_transformation_spec_version_id']) == (
                    expected['order_status'], expected['approval_stage'], expected['selected_brief_version_id'],
                    expected['selected_transformation_spec_version_id'])
            assert [v['id'] for v in snapshot['brief_versions']] == expected['brief_version_ids']
            assert [v['id'] for v in snapshot['transformation_spec_versions']] == expected['transformation_spec_version_ids']
            assert sum(a['target_type'] == 'BRIEF' for a in snapshot['approvals']) == expected['persisted_brief_approval_count']
            assert sum(a['target_type'] == 'TRANSFORMATION_SPEC' for a in snapshot['approvals']) == expected['persisted_transformation_spec_approval_count']
        assert all(not self.snapshot()[table] for table in ('execution_runs', 'artifacts', 'qa_reports'))
        evidence = ROOT / 'docs/p3/validation/scenario-results.json'
        results = load(evidence)
        results[self.fixture['fixture_id']] = {
            'result': 'PASS', 'initial_profile': self.fixture['initial_state']['profile'],
            'initial_state_verified': True, 'driver_layers': [a['layer'] for a in self.fixture['actions']],
            'actions': [a['method'] for a in self.fixture['actions']],
            'expected': self.fixture['expected']['code_or_reason'],
            'public_errors': [r['code'] for r in self.results if isinstance(r, dict) and 'code' in r],
            'partial_business_writes_on_rejection': 0 if rejected else None,
            'no_execution_artifacts_qa': True,
        }
        evidence.write_text(json.dumps(results, indent=2, sort_keys=True) + '\n')
        return self


def verify_vectors():
    directory = ROOT / 'pecs/pilot_slice_v1/specifications/hash_vectors'
    for vector in load(directory / 'vectors_manifest.json')['vectors']:
        assert hash_payload(load(directory / vector['input'])) == vector['expected_sha256']
    assert hash_payload({'a': 'e\u0301'}) == hash_payload({'a': 'é'})
    payload = {'b': 1.0, 'a': [True, None, 'é']}
    assert rfc8785.dumps(payload) == b'{"a":[true,null,"\xc3\xa9"],"b":1}'
    with pytest.raises(ValueError):
        hash_payload({'é': 1, 'e\u0301': 2})
    return 'CONTENT_HASH_EQUAL'
