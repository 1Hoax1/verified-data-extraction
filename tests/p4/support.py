"""Test-only real P3 workflow setup, immutable P0 inputs and state witnesses."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

from vde.bootstrap import bootstrap
from vde.config import Config
from vde.models import OrderRecord
from vde.persistence.uow import UnitOfWork
from vde.storage import Storage
from vde.workflow.service import ManualWorkflow

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads(Path(path).read_text())


class Approved:
    def __init__(self, directory, fixture='P-A_dirty_csv', *, raw=None, pipeline=None, fields=None):
        self.env = bootstrap(Config(Path(directory) / 'workspace'))
        assert self.env.health == 'ready'
        source = ROOT / 'pecs/pilot_slice_v1/fixtures' / fixture
        brief, spec = deepcopy(load(source/'brief_version.json')), deepcopy(load(source/'transformation_spec_version.json'))
        self.order_id = brief['order_id']
        self.asset_id = spec['inputs'][0]['asset_id']
        name = 'input_orders.xlsx' if spec['inputs'][0]['source_type'] == 'LOCAL_XLSX' else 'input_dirty.csv'
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
        self.workflow.publish_brief(self.order_id, brief, self.order())
        self.workflow.approve_brief(self.order_id, brief['version_id'], self.order())
        self.workflow.publish_spec(self.order_id, spec, self.order())
        self.workflow.approve_spec_and_finish(self.order_id, spec['version_id'], self.order())
        self.handoff = self.workflow.p4_handoff(self.order_id)
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
