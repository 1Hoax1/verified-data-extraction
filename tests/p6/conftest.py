"""Disposable P6 runtime scenarios; never connect to an owner's workspace.

The upload substitution supplies AppTest's unsupported file-uploader input. It
does not invoke an ingestion/workflow command: the test still clicks the frozen
Upload, publish, confirmation and approval controls separately.
"""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import time
import zipfile

import pytest
from streamlit.testing.v1 import AppTest

from vde.bootstrap import bootstrap
from vde.config import Config
from vde.contracts import content_hash
from vde.persistence.uow import UnitOfWork

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'pecs/pilot_slice_v1/fixtures'
TABLES = ('orders', 'input_assets', 'brief_versions', 'transformation_spec_versions',
          'approvals', 'execution_runs', 'artifacts', 'qa_reports', 'event_log')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(document):
    return json.dumps(document, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')


def record(name, value):
    directory = Path(os.environ.get('P6_RESULTS_DIR', '/tmp/vde-p6-results')).resolve()
    assert not directory.is_relative_to(ROOT), 'Runtime observations must be outside the repository'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (name + '.json')).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')


def snapshot(directory):
    """Independent read-only SQLite observation, including deliberately corrupt DBs."""
    database = Path(directory) / 'app.sqlite3'
    with sqlite3.connect('file:' + str(database) + '?mode=ro', uri=True) as connection:
        connection.row_factory = sqlite3.Row
        return {table: [dict(row) for row in connection.execute('SELECT * FROM ' + table + ' ORDER BY 1')]
                for table in TABLES}


def payload_hashes(directory):
    directory = Path(directory)
    return {p.relative_to(directory).as_posix(): sha(p.read_bytes())
            for p in sorted(directory.rglob('*')) if p.is_file() and p.name not in
            {'app.sqlite3', 'app.sqlite3-wal', 'app.sqlite3-shm'}}


def mutate_sql(directory, statement, parameters=()):
    """Offline adversarial mutation ONLY of a disposable test copy."""
    assert Path(directory).resolve().is_relative_to(Path('/tmp'))
    with sqlite3.connect(Path(directory) / 'app.sqlite3') as connection:
        for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall():
            connection.execute('DROP TRIGGER "' + name.replace('"', '""') + '"')
        connection.execute(statement, parameters)


def widget(app, kind, label):
    matches = [element for element in getattr(app, kind) if element.label == label]
    assert len(matches) == 1, (kind, label, [e.label for e in getattr(app, kind)],
                               [e.value for e in app.error], [e.value for e in app.json])
    return matches[0]


def healthy_ui(app):
    assert not app.exception, [e.message for e in app.exception]
    return app


def new_app(directory):
    # Environment is bound inside this disposable script rather than inherited
    # from another test session. The production app itself remains unchanged.
    script = f'''\nimport os, runpy\nfrom types import SimpleNamespace\nimport streamlit as st\nos.environ['VDE_WORKSPACE'] = {str(directory)!r}\noriginal_uploader = st.file_uploader\ndef simulated_test_upload(*args, **kwargs):\n    uploaded = st.session_state.get('_p6_test_upload')\n    if uploaded is None:\n        return original_uploader(*args, **kwargs)\n    name, raw = uploaded\n    return SimpleNamespace(name=name, size=len(raw), getvalue=lambda: raw)\nst.file_uploader = simulated_test_upload\ntry:\n    runpy.run_path({str(ROOT / 'src/vde/app.py')!r}, run_name='__main__')\nfinally:\n    st.file_uploader = original_uploader\n'''
    return healthy_ui(AppTest.from_string(script, default_timeout=120).run())


@pytest.fixture(scope='session', autouse=True)
def download_http():
    """Real loopback GET of Streamlit's prepared media, independent of snapshots."""
    from streamlit.runtime.memory_media_file_storage import MemoryMediaFileStorage
    from streamlit.web.server.media_file_handler import MediaFileHandler
    from tornado.testing import AsyncHTTPTestCase
    from tornado.web import Application
    storage = [MemoryMediaFileStorage('/mock/media')]
    patch = pytest.MonkeyPatch()
    patch.setattr('streamlit.testing.v1.app_test.MemoryMediaFileStorage', lambda endpoint: storage[0])
    class DownloadHandler(MediaFileHandler):
        pass
    DownloadHandler.initialize_storage(storage[0])
    class Server(AsyncHTTPTestCase):
        def get_app(self):
            return Application([(r'/mock/media/(.*)', DownloadHandler, {'path': ''})])
    server = Server()
    server.setUp()
    def fetch(path):
        return server.fetch(path)
    def reset_storage():
        # A new browser-test transport isolates the allocation-fault probe from
        # URLs deliberately published by previous successful test sessions.
        storage[0] = MemoryMediaFileStorage('/mock/media')
        DownloadHandler.initialize_storage(storage[0])
        return storage[0]
    fetch.reset_storage = reset_storage
    try:
        yield fetch
    finally:
        server.tearDown()
        patch.undo()


class UIScenario:
    """One isolated UI-created Order and a recorded sequence of user events."""

    def __init__(self, directory, family='P-A_dirty_csv', *, pb_spec=None, execute=True, pause_after_brief=False):
        self.directory = Path(directory)
        self.env = bootstrap(Config(self.directory))
        assert self.env.health == 'ready'
        self.family = family
        self.source = FIXTURES / family
        self.actions = []
        self.adaptations = []
        self.app = new_app(self.directory)
        self.create(title='P6 isolated simulated test user — ' + family,
                    listing='Fixture exercise only. No live customer approval or delivery.')
        filename = ('input_orders.xlsx' if family.startswith('P-B') else
                    'input_problematic.csv' if family.startswith('P-D') else 'input_dirty.csv')
        self.app.session_state['_p6_test_upload'] = (filename, (self.source / filename).read_bytes())
        self.app.run()
        self.click('Upload')
        del self.app.session_state['_p6_test_upload']
        with self.uow() as u:
            assets = u.inputs.list_for_order(self.order_id)
        assert len(assets) == 1
        self.asset = assets[0]
        self.check('Open manual workflow')
        self.select('P3 registered input', self.asset.id)
        original_brief = json.loads((self.source / 'brief_version.json').read_text())
        original_spec = json.loads((self.source / 'transformation_spec_version.json').read_text())
        selection = original_spec['inputs'][0]
        if selection['source_type'] == 'LOCAL_CSV':
            self.select('P3 encoding', selection['csv_options']['encoding'])
            self.select('P3 delimiter', selection['csv_options']['delimiter'])
            widget(self.app, 'number_input', 'P3 header row').set_value(selection['csv_options']['header_row']).run()
        else:
            self.select('P3 worksheet', selection['sheet_name'])
        self.click('Verify P3 input and preview')
        self.click('Begin manual review')
        self.check('Open deterministic transformation')
        assert widget(self.app, 'button', 'Execute').disabled
        brief = self.adapt(original_brief, 'brief_version', self.source / 'brief_version.json')
        self.set_text('Brief JSON draft', json.dumps(brief))
        self.click('Validate Brief draft')
        self.click('Save new Brief version')
        self.before_brief_approval = self.snapshot()
        assert len(self.before_brief_approval['approvals']) == 0
        assert widget(self.app, 'button', 'I approve this Brief version').disabled
        self.check('Confirm this exact Brief ID and hash')
        self.click('I approve this Brief version')
        self.after_brief_approval = self.snapshot()
        assert len(self.after_brief_approval['approvals']) == 1
        self.check('Open deterministic transformation')
        assert widget(self.app, 'button', 'Execute').disabled
        with self.uow() as u:
            self.brief = u.briefs.get(u.orders.get(self.order_id).selected_brief_version_id)
        if pause_after_brief:
            record('checkpoint-P3', {'actions': self.actions, 'adaptations': self.adaptations,
                   'persisted_brief': asdict(self.brief), 'snapshot': self.snapshot()})
            return
        documents = [(original_spec, self.source / 'transformation_spec_version.json')]
        if pb_spec is not None:
            documents.append((pb_spec[0], pb_spec[1]))
        for document, origin in documents:
            spec = self.adapt(document, 'transformation_spec_version', origin)
            self.set_text('TransformationSpec JSON draft', json.dumps(spec))
            self.click('Validate TransformationSpec draft')
            self.click('Save new TransformationSpec version')
        self.before_spec_approval = self.snapshot()
        assert len(self.before_spec_approval['approvals']) == 1
        assert widget(self.app, 'button', 'I approve TransformationSpec').disabled
        self.check('Confirm this exact Spec ID, hash and approved Brief context')
        self.click('I approve TransformationSpec')
        self.approved_snapshot = self.snapshot()
        assert len(self.approved_snapshot['approvals']) == 2
        with self.uow() as u:
            self.spec = u.specs.get(u.orders.get(self.order_id).selected_transformation_spec_version_id)
        self.check('Open deterministic transformation')
        self.check('I confirm the selected source and pipeline')
        assert not widget(self.app, 'button', 'Execute').disabled
        if execute:
            self.click('Execute')
            with self.uow() as u:
                runs = u.runs.list_for_order(self.order_id)
            assert len(runs) == 1 and runs[0].status == 'succeeded'
            self.run_id = runs[0].id
            self.p4_snapshot = self.snapshot()
            self.check('Open export and QA')
            self.click('Export + deterministic QA')
            self.app.run()
            from vde.p5.service import P5Service
            self.decision = P5Service(self.env).read_decision(self.run_id)
        record('fixture-' + family, {'isolated_workspace': str(self.directory),
               'simulated_test_user_only': True, 'actions': self.actions,
               'identity_adaptations': self.adaptations, 'order': asdict(self.order()),
               'actual_persisted_brief': asdict(self.brief), 'actual_persisted_spec': asdict(self.spec),
               'approvals': self.snapshot()['approvals']})

    def create(self, title, listing, **optional):
        self.token = self.app.session_state['p6_order_request_token']
        self.set_text('Order title', title, run=False)
        self.set_text('Listing text', listing, run=False)
        labels = {'listing_url': 'Listing URL (optional)', 'budget': 'Budget (canonical decimal, optional)',
                  'deadline': 'Deadline (UTC YYYY-MM-DDTHH:MM:SSZ, optional)', 'notes': 'Notes (optional)'}
        for key, value in optional.items():
            self.set_text(labels[key], value, run=False)
        self.click('Create DRAFT Order')
        self.order_id = self.app.session_state['p6_last_order_id']
        assert self.order_id == self.token

    def adapt(self, original, kind, origin):
        doc = deepcopy(original)
        substitutions = []
        def replace_at(mapping, key, value, path):
            old = mapping[key]
            mapping[key] = value
            substitutions.append({'path': path, 'original': old, 'adapted': value})
        replace_at(doc, 'order_id', self.order_id, 'order_id')
        if kind == 'brief_version':
            replace_at(doc['inputs_expected'][0], 'asset_id', self.asset.id, 'inputs_expected[0].asset_id')
            replace_at(doc, 'source_refs', [self.asset.id], 'source_refs')
        else:
            replace_at(doc['inputs'][0], 'asset_id', self.asset.id, 'inputs[0].asset_id')
            replace_at(doc, 'brief_version_id', self.brief.id, 'brief_version_id')
            replace_at(doc, 'brief_content_hash', self.brief.content_hash, 'brief_content_hash')
        doc['content_hash'] = content_hash(doc, kind)
        self.adaptations.append({'source': str(origin.relative_to(ROOT)) if origin.is_relative_to(ROOT) else str(origin),
            'original_file_sha256': sha(origin.read_bytes()), 'original_content_hash': original['content_hash'],
            'substitutions': substitutions, 'derived_content_hash': doc['content_hash'],
            'derived_json_sha256': sha(canonical(doc)),
            'ui_allocates_version_id_created_at_and_monotonic_version_number': True})
        return doc

    def set_text(self, label, value, run=True):
        kind = 'text_area' if label in {'Listing text', 'Notes (optional)', 'Brief JSON draft',
                                      'TransformationSpec JSON draft'} else 'text_input'
        control = widget(self.app, kind, label).set_value(value)
        if run:
            healthy_ui(control.run())

    def click(self, label):
        control = widget(self.app, 'button', label)
        assert not control.disabled, label
        self.actions.append({'action': 'button', 'label': label, 'before_counts': self.counts()})
        healthy_ui(control.click().run())

    def check(self, label):
        control = widget(self.app, 'checkbox', label)
        assert not control.disabled, label
        self.actions.append({'action': 'checkbox', 'label': label})
        healthy_ui(control.check().run())

    def select(self, label, value):
        healthy_ui(widget(self.app, 'selectbox', label).set_value(value).run())

    def uow(self):
        return UnitOfWork(self.env.database, self.env.workspace)

    def order(self):
        with self.uow() as u:
            return u.orders.get(self.order_id)

    def snapshot(self):
        return snapshot(self.directory)

    def counts(self):
        return {table: len(rows) for table, rows in self.snapshot().items()}

    def prepare_ui(self):
        # Delivery selectors are explicit and cannot inherit another session's IDs.
        self.select('Download Order', self.order_id)
        self.select('Download Run', self.run_id)
        self.click('Prepare verified download')
        return self.app.session_state['p6_delivery_snapshot']


@pytest.fixture(scope='session')
def pb_spec(tmp_path_factory):
    archive = ROOT / 'docs/p5/handoff/P5_Codex_Implementation_Handoff_2026-11-05.zip'
    assert sha(archive.read_bytes()) == '3e3a2f6a8e65f500fe5bd281ef805d9229d50b96c50433cdda52cbb4fd6d63e4'
    with zipfile.ZipFile(archive) as outer:
        names = [n for n in outer.namelist() if n.endswith('/P5_Gate_A_PB_Supplement_v0.2b_candidate.zip')]
        assert len(names) == 1
        nested = outer.read(names[0])
    assert sha(nested) == '4e08285b00344f2d00a7af89a723a835f931f4bceb768b11ec1aaf637fd0ae18'
    with zipfile.ZipFile(io.BytesIO(nested)) as inner:
        names = [n for n in inner.namelist() if n.endswith('/fixtures/P-B_versioned/transformation_spec_version_v2_CANDIDATE.json')]
        assert len(names) == 1
        raw = inner.read(names[0])
    path = tmp_path_factory.mktemp('p6-pb-provenance') / 'transformation_spec_version_v2_CANDIDATE.json'
    path.write_bytes(raw)
    return json.loads(raw), path


@pytest.fixture(scope='session')
def pa(tmp_path_factory):
    return UIScenario(tmp_path_factory.mktemp('p6-pa') / 'workspace')


@pytest.fixture(scope='session')
def pb(tmp_path_factory, pb_spec):
    return UIScenario(tmp_path_factory.mktemp('p6-pb') / 'workspace', 'P-B_xlsx_sheet', pb_spec=pb_spec)


@pytest.fixture(scope='session')
def pd(tmp_path_factory):
    return UIScenario(tmp_path_factory.mktemp('p6-pd') / 'workspace', 'P-D_errors_and_qa_blockers')


@pytest.fixture
def copy_workspace(tmp_path):
    counter = [0]
    def make(case):
        counter[0] += 1
        target = tmp_path / ('disposable-' + str(counter[0]))
        shutil.copytree(case.directory if hasattr(case, 'directory') else Path(case), target)
        return target, bootstrap(Config(target))
    return make


def pytest_collection_modifyitems(items):
    for item in items:
        if '/p6/' in str(item.path):
            match = re.match(r'test_T(\d{2})_', item.name)
            if match:
                item.user_properties.append(('p6_id', 'P6-T' + match[1]))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if '/p6/' in str(item.path) and report.when == 'call':
        record('outcome-' + item.name.split('_')[1], {'nodeid': item.nodeid,
               'outcome': report.outcome, 'duration_seconds': report.duration,
               'properties': item.user_properties,
               'failure': str(report.longrepr) if report.failed else None})
