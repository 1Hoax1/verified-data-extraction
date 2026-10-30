"""Test-only real P3 workflow setup, immutable P0 inputs and state witnesses."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from datetime import date
from types import SimpleNamespace

import pytest

from vde.bootstrap import bootstrap
from vde.config import Config
from vde.models import OrderRecord
from vde.persistence.uow import UnitOfWork
from vde.storage import Storage
from vde.workflow.service import ManualWorkflow
from vde.execution.errors import ExecutionError
from vde.execution.engine import apply
from vde.execution.source_adapter import Source, Row
from vde.execution.budget import Budget
from vde.execution.wire import encode_cell

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads(Path(path).read_text())


class Approved:
    def __init__(self, directory, fixture='P-A_dirty_csv', *, raw=None, pipeline=None, fields=None,
                 approve_final=True, csv_options=None):
        self.env = bootstrap(Config(Path(directory) / 'workspace'))
        assert self.env.health == 'ready'
        source = ROOT / 'pecs/pilot_slice_v1/fixtures' / fixture
        brief, spec = deepcopy(load(source/'brief_version.json')), deepcopy(load(source/'transformation_spec_version.json'))
        self.order_id = brief['order_id']
        self.asset_id = spec['inputs'][0]['asset_id']
        name = 'input_orders.xlsx' if spec['inputs'][0]['source_type'] == 'LOCAL_XLSX' else (
            'input_problematic.csv' if fixture == 'P-D_errors_and_qa_blockers' else 'input_dirty.csv')
        if fields is not None:
            brief['fields'] = deepcopy(fields)
            spec['expected_schema'] = deepcopy(fields)
            brief['output_contract']['column_order'] = spec['output']['column_order'] = [f['name'] for f in fields]
            brief['acceptance_criteria'] = []
            # P0 requires at least one acceptance criterion; retain a known
            # structural criterion with its target mapped to the first field.
            criterion = deepcopy(load(source/'brief_version.json')['acceptance_criteria'][0])
            criterion['target']['column'] = None
            criterion['target']['columns'] = None
            brief['acceptance_criteria'] = [criterion]
            spec['acceptance_criteria_ref'] = [criterion['criterion_id']]
            brief['data_quality_expectations']['duplicate_key'] = None
        if pipeline is not None:
            spec['pipeline'] = deepcopy(pipeline)
        if csv_options is not None:
            spec['inputs'][0]['csv_options'] = deepcopy(csv_options)
        with self.uow() as uow:
            uow.orders.add(OrderRecord(self.order_id, 'P4 test', 'Existing approved local Order',
                                      '2026-07-12T08:00:00Z', '2026-07-12T08:00:00Z'))
        self.raw = (source/name).read_bytes() if raw is None else raw
        self.asset = Storage(self.env.database, self.env.workspace).register_input(
            id=self.asset_id, order_id=self.order_id, original_filename=name, data=self.raw)
        self.workflow = ManualWorkflow(self.env)
        selected = spec['inputs'][0]
        self.selection = self.workflow.choose_input(self.order_id, self.asset_id,
            {k: deepcopy(selected[k]) for k in ('source_type', 'sheet_name', 'csv_options')})
        self.workflow.begin_manual_review(self.order_id, self.order())
        published_brief = self.workflow.publish_brief(self.order_id, brief, self.order())
        spec['brief_content_hash'] = published_brief.content_hash
        self.workflow.approve_brief(self.order_id, brief['version_id'], self.order())
        self.workflow.publish_spec(self.order_id, spec, self.order())
        if approve_final:
            self.workflow.approve_spec_and_finish(self.order_id, spec['version_id'], self.order())
            self.handoff = self.workflow.p4_handoff(self.order_id)
        else:
            from vde.workflow.read_model import P4Handoff
            with self.uow() as uow:
                b = uow.briefs.get(brief['version_id'])
                s = uow.specs.get(spec['version_id'])
                ba = uow.approvals.find_valid('BRIEF', b.id, b.content_hash)
            self.handoff = P4Handoff(self.order_id, b.id, b.content_hash, ba.id, s.id, s.content_hash,
                                     '', self.asset.id, self.asset.byte_sha256,
                                     {k: selected[k] for k in ('source_type', 'sheet_name', 'csv_options')})
        self.before = self.counts()

    def uow(self):
        return UnitOfWork(self.env.database, self.env.workspace)

    def order(self):
        with self.uow() as uow:
            return uow.orders.get(self.order_id)

    def counts(self):
        with self.uow() as uow:
            return {t: uow.connection.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in
                    ('execution_runs', 'artifacts', 'event_log', 'qa_reports', 'approvals')}

    def snapshot(self):
        with self.uow() as uow:
            return {t: [dict(r) for r in uow.connection.execute('SELECT * FROM '+t+' ORDER BY 1')] for t in
                    ('orders', 'brief_versions', 'transformation_spec_versions', 'approvals', 'execution_runs', 'artifacts', 'event_log', 'qa_reports')}


def operation(kind, params, index=1, source='raw', output='result'):
    return dict(schema_version='1.1', operation_id=f'test-op-{index}', type=kind,
                input_dataset=source, output_dataset=output, params=params)


def evidence(group, identity, result):
    directory = ROOT/'docs/p4/validation'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory/(group+'-results.json')
    data = load(path) if path.exists() else {}
    data[identity] = result
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)+'\n')


def fixture_cases(pack, numbers, directory):
    cases = load(pack/'fixtures/operation_cases.json')['cases']
    for number in numbers:
        c = cases[number-1]
        source = Source(tuple(c['input']['columns']), iter(Row(i+1, tuple(row)) for i, row in enumerate(c['input']['rows'])), [])
        try:
            table = apply(SimpleNamespace(pipeline=c['pipeline']), source, Budget(), directory)
            rows = [list(row.values) for row in table.rows]
            assert c['expected']['outcome'] == 'ROWS'
            assert list(table.columns) == c['expected']['columns'] and len(rows) == len(c['expected']['rows'])
            for row, expected in zip(rows, c['expected']['rows']):
                for cell, wanted in zip(row, expected):
                    actual = encode_cell(cell) if type(wanted) is dict else cell.isoformat() if type(cell) is date else cell
                    assert actual == wanted
                    if type(wanted) in (int, bool, str):
                        assert type(actual) is type(wanted)
            if 'wire_rows' in c['expected']:
                assert [[encode_cell(v) for v in row] for row in rows] == c['expected']['wire_rows']
            record = {'result': 'PASS', 'driver': 'actual execution.engine.apply', 'rows': len(rows), 'columns': list(table.columns)}
        except ExecutionError as exc:
            assert c['expected']['outcome'] == 'ERROR' and exc.code == c['expected']['error_code']
            record = {'result': 'PASS', 'driver': 'actual execution.engine.apply', 'error': exc.code}
        record['service_integration'] = integration_fixture(c, directory/c['id'])
        evidence('f-fixture', c['id'], record)


def integration_fixture(case, directory):
    """Each F case also traverses real source registration/manual approval.

    Schema/semantic-invalid operations are rejected at the P3 boundary; valid
    operations receive their own approvals and execute through the P4 service.
    """
    import csv
    import io
    from .source_fixtures import cached_xlsx
    from vde.workflow.errors import WorkflowError
    from vde.execution.service import ExecutionService
    from vde.execution.wire import iter_payload
    columns = case['expected']['columns'] or case['input']['columns']
    template = load(ROOT/'pecs/pilot_slice_v1/fixtures/P-A_dirty_csv/brief_version.json')['fields'][0]
    fields = []
    for name in columns:
        field = deepcopy(template)
        field.update(name=name, output_name=name, label=name, data_type='string', nullable=True,
                     required=False, format=None, min_value=None, max_value=None, allowed_values=None, unique=False)
        fields.append(field)
    matrix = case['input']['rows']
    all_strings = all(type(v) is str for row in matrix for v in row)
    if all_strings:
        stream = io.StringIO(newline='')
        csv.writer(stream, lineterminator='\n').writerows([case['input']['columns']]+matrix)
        raw = stream.getvalue().encode('utf-8')
        fixture = 'P-A_dirty_csv'
    else:
        raw = cached_xlsx(case['input']['columns'], matrix)
        fixture = 'P-B_xlsx_sheet'
    try:
        a = Approved(directory, fixture, raw=raw, pipeline=case['pipeline'], fields=fields,
                     csv_options={'encoding':'UTF-8','delimiter':',','header_row':0} if all_strings else None)
    except WorkflowError as exc:
        assert case['expected']['outcome'] == 'ERROR' and exc.code == case['expected']['error_code']
        env = bootstrap(Config(directory/'workspace'))
        with UnitOfWork(env.database, env.workspace) as uow:
            assert uow.connection.execute('SELECT count(*) FROM execution_runs').fetchone()[0] == 0
            assert uow.connection.execute('SELECT count(*) FROM artifacts').fetchone()[0] == 0
        return {'result':'PASS', 'rejected_by':'P3 schema/semantic approval boundary', 'code':exc.code}
    try:
        service = ExecutionService(a.env)
        result = service.execute(a.order_id, a.order(), a.handoff)
        assert case['expected']['outcome'] == 'ROWS'
        handle, raw_result = service.read_result(result.run_id)
        actual = list(iter_payload(raw_result))
        assert list(handle.columns) == case['expected']['columns'] and len(actual) == len(case['expected']['rows'])
        for row, expected in zip(actual, case['expected']['rows']):
            for value, target in zip(row, expected):
                projected = encode_cell(value) if type(target) is dict else value.isoformat() if type(value) is date else value
                assert projected == target
                if type(target) in (str, bool, int):
                    assert type(projected) is type(target)
        assert a.order().status == 'EXECUTING'
        status = 'succeeded'
    except ExecutionError as exc:
        assert case['expected']['outcome'] == 'ERROR' and exc.code == case['expected']['error_code']
        assert a.counts()['artifacts'] == 0
        status = a.order().status
    assert a.env.workspace.path(a.asset.workspace_relpath).read_bytes() == a.raw
    return {'result':'PASS','driver':'P1 source + real P3 approval + P4 service','terminal':status,
            'source_type':a.handoff.input_selection['source_type'],'input_unchanged':True}


def assert_rejection(a, handoff, code, monkeypatch, expected_order=None):
    from vde.execution.service import ExecutionService
    before = a.snapshot()
    with monkeypatch.context() as patch:
        def forbidden(*args, **kwargs):
            raise AssertionError('Source I/O before admission was rejected')
        patch.setattr(a.env.workspace, 'read_verified', forbidden)
        with pytest.raises(ExecutionError) as caught:
            ExecutionService(a.env).start(a.order_id, expected_order or a.order(), handoff)
    assert caught.value.code == code
    assert a.snapshot() == before
    assert a.env.workspace.path(a.asset.workspace_relpath).read_bytes() == a.raw
    return caught.value


def fields_for_stress(count=200):
    template = load(ROOT/'pecs/pilot_slice_v1/fixtures/P-A_dirty_csv/brief_version.json')['fields'][0]
    fields = []
    for index in range(count):
        field = deepcopy(template)
        field.update(name=f'c{index:03}', output_name=f'c{index:03}', label=f'c{index:03}',
                     data_type='integer' if index == 1 else 'string',
                     format='INTEGER' if index == 1 else None, nullable=False, required=True,
                     min_value=None, max_value=None, unique=False, allowed_values=None)
        fields.append(field)
    return fields


def stress_pipeline():
    return [operation('parse_number', dict(column='c001', decimal_separator='.', thousands_separator=None,
                                           target_type='integer', errors='FAIL'), source='raw', output='s01'),
            operation('sort', dict(by=['c000'], ascending=[True], nulls='LAST'), index=2, source='s01', output='s02'),
            operation('deduplicate', dict(subset=['c001'], keep='FIRST'), index=3, source='s02', output='result')]
