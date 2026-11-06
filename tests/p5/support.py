"""Isolated P5 scenarios use actual P1 storage, P3 actions and P4 execution."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
from types import SimpleNamespace

from vde.bootstrap import bootstrap
from vde.config import Config
from vde.models import OrderRecord
from vde.persistence.uow import UnitOfWork
from vde.storage import Storage
from vde.workflow.service import ManualWorkflow
from vde.execution.service import ExecutionService
from vde.p5.service import P5Service

ROOT = Path(__file__).resolve().parents[2]
BASELINE = 'fd39aa1bed480313504ae8b1f76e77e170cb72ba'


def load(p):
    return json.loads(Path(p).read_text())


class Scenario:
    def __init__(self, directory, fixture='P-A_dirty_csv', *, change=None, raw=None, filename=None, execute=True):
        self.directory = Path(directory)
        self.env = bootstrap(Config(self.directory/'workspace'))
        assert self.env.health=='ready'
        self.source = ROOT/'pecs/pilot_slice_v1/fixtures'/fixture
        brief, spec = deepcopy(load(self.source/'brief_version.json')), deepcopy(load(self.source/'transformation_spec_version.json'))
        original_spec = deepcopy(spec)
        if change:
            change(brief,spec)
        self.order_id = brief['order_id']
        self.asset_id = spec['inputs'][0]['asset_id']
        filename = filename or ('input_orders.xlsx' if spec['inputs'][0]['source_type']=='LOCAL_XLSX' else
                                'input_problematic.csv' if fixture.startswith('P-D') else 'input_dirty.csv')
        self.raw = raw if raw is not None else (self.source/filename).read_bytes()
        with self.uow() as u:
            u.orders.add(OrderRecord(self.order_id,'P5 isolated TEST_ONLY','No live business approval is represented.',
                                    '2026-07-12T08:00:00Z','2026-07-12T08:00:00Z'))
        self.asset = Storage(self.env.database,self.env.workspace).register_input(
            id=self.asset_id,order_id=self.order_id,original_filename=filename,data=self.raw)
        w = ManualWorkflow(self.env)
        sel = spec['inputs'][0]
        w.choose_input(self.order_id,self.asset_id,{k:deepcopy(sel[k]) for k in ('source_type','sheet_name','csv_options')})
        w.begin_manual_review(self.order_id,self.order())
        b = w.publish_brief(self.order_id,brief,self.order())
        w.approve_brief(self.order_id,b.id,self.order())  # simulated user action in this isolated test DB
        spec['brief_content_hash'] = b.content_hash
        if spec['version_number'] > 1 and spec['version_id'] != original_spec['version_id']:
            original_spec['brief_content_hash'] = b.content_hash
            w.publish_spec(self.order_id,original_spec,self.order())
        t = w.publish_spec(self.order_id,spec,self.order())
        w.approve_spec_and_finish(self.order_id,t.id,self.order())
        self.workflow = w
        self.handoff = w.p4_handoff(self.order_id)
        if execute:
            self.result = ExecutionService(self.env).execute(self.order_id,self.order(),self.handoff)
            self.run_id = self.result.run_id
            self.before = self.counts()

    def uow(self):
        return UnitOfWork(self.env.database,self.env.workspace)

    def order(self):
        with self.uow() as u:
            return u.orders.get(self.order_id)

    def counts(self):
        with self.uow() as u:
            return {t:u.connection.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in
                    ('artifacts','qa_reports','event_log','approvals','execution_runs')}

    def snapshot(self):
        with self.uow() as u:
            return {t:[dict(r) for r in u.connection.execute('SELECT * FROM '+t+' ORDER BY 1')] for t in
                    ('orders','brief_versions','transformation_spec_versions','approvals','execution_runs','artifacts','qa_reports','event_log')}

    def complete(self,**kw):
        return P5Service(self.env,**kw).complete(self.run_id,self.order())

    def delta(self):
        now=self.counts()
        return {k:now[k]-self.before[k] for k in now}


def pb_v2(brief,spec):
    spec['version_id']='transform-pb-v2-cr-p5-001'
    spec['version_number']=2
    spec['acceptance_criteria_ref'].append('PB-AC-007')


def simple_change(fields, format='CSV', pipeline=None, *, rows=2):
    def change(b,s):
        b['fields']=deepcopy(fields);s['expected_schema']=deepcopy(fields)
        names=[f['name'] for f in fields]
        for out in (b['output_contract'],s['output']):
            out.update(format=format,file_name='result.'+format.lower(),sheet_name='Data' if format=='XLSX' else None,
                       encoding='UTF-8' if format=='CSV' else None,delimiter=',' if format=='CSV' else None,column_order=names)
        b['volume_expectation'].update(mode='EXACT',exact_count=rows,min_count=None,max_count=None)
        b['data_quality_expectations'].update(duplicate_key=[names[0]] if fields[0]['unique'] else None)
        if s['inputs'][0]['source_type'] == 'LOCAL_CSV':
            s['inputs'][0]['csv_options'] = dict(encoding='UTF-8',delimiter=',',header_row=0)
        criterion=deepcopy(b['acceptance_criteria'][0])
        criterion['target']['artifact_type']='RESULT_'+format
        b['acceptance_criteria']=[criterion]
        s['acceptance_criteria_ref']=[criterion['criterion_id']]
        s['pipeline']=pipeline or [dict(schema_version='1.1',operation_id='p5-select',type='select_columns',
                                        input_dataset='raw',output_dataset='result',params={'columns':names})]
    return change


def field(name='id',kind='string',*,required=True,unique=False):
    f=deepcopy(load(ROOT/'pecs/pilot_slice_v1/fixtures/P-A_dirty_csv/brief_version.json')['fields'][0])
    f.update(name=name,output_name=name,label=name,data_type=kind,required=required,nullable=not required,
             format={'integer':'INTEGER','decimal':'DECIMAL_DOT','date':'YYYY-MM-DD'}.get(kind),
             allowed_values=None,min_value=None,max_value=None,unique=unique)
    return f


def checks(decision,dq):
    return [c for c in decision.report['deterministic_checks'] if c['check_id']==dq]


def record(name,value):
    import os
    path=Path(os.environ.get('P5_RESULTS_DIR','/tmp/vde-p5-results'))
    path.mkdir(parents=True,exist_ok=True)
    (path/(name+'.json')).write_text(json.dumps(value,indent=2,ensure_ascii=False,default=str)+'\n')


def dq_cases():
    import io,zipfile
    archive=ROOT/'docs/p5/handoff/P5_Codex_Implementation_Handoff_2026-11-05.zip'
    with zipfile.ZipFile(archive) as outer:
        prefix='P5_Codex_Implementation_Handoff_2026-11-05/sources/'
        with zipfile.ZipFile(io.BytesIO(outer.read(prefix+'P5_Implementation_Design_Pack_v0.2a_candidate.zip'))) as inner:
            return json.loads(inner.read('P5_Implementation_Design_Pack_v0.2a_candidate/fixtures/dq_cases.json'))['cases']


def projection_for(kinds,format='CSV'):
    from vde.p5.project import Projection
    fs=[field('v'+str(i),k) for i,k in enumerate(kinds)]
    names=tuple(f['name'] for f in fs)
    return Projection(names,names,tuple(fs),dict(format=format,sheet_name='Data' if format=='XLSX' else None,
                    delimiter=',' if format=='CSV' else None,encoding='UTF-8' if format=='CSV' else None,
                    dataset_id='result',file_name='result.'+format.lower(),column_order=list(names)))


def modify_xlsx(raw,coordinate,text,*,formula=False):
    import io,zipfile,xml.etree.ElementTree as ET
    ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    output=io.BytesIO();found=False
    with zipfile.ZipFile(io.BytesIO(raw)) as old,zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as new:
        for name in old.namelist():
            data=old.read(name)
            if name.startswith('xl/worksheets/') and name.endswith('.xml'):
                root=ET.fromstring(data)
                for cell in root.iter(ns+'c'):
                    if cell.get('r')==coordinate:
                        value=cell.find(ns+'v')
                        if value is None:value=ET.SubElement(cell,ns+'v')
                        value.text=text;found=True
                        if formula:
                            f=cell.find(ns+'f')
                            if f is None:f=ET.SubElement(cell,ns+'f')
                            f.text='1+1'
                data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
            new.writestr(name,data)
    assert found,coordinate
    return output.getvalue()


def assert_completed(scenario,decision,status,overall_status):
    from vde.execution.wire import REVISION
    assert decision.order_status==scenario.order().status==status
    assert decision.report['overall_status']==overall_status
    validate_report(decision.report)
    with scenario.uow() as u:
        run=u.runs.get(scenario.run_id)
        assert run.status=='succeeded'
        assert len(u.reports.list_for_run(run.id))==1
        artifacts=u.artifacts.list_for_run(run.id)
        assert len([a for a in artifacts if a.artifact_type.startswith('RESULT_')])==1
        assert len([a for a in artifacts if a.artifact_type=='P4_INTERNAL' and a.format==REVISION])==1
    assert scenario.delta()==dict(artifacts=1,qa_reports=1,event_log=2,approvals=0,execution_runs=0)
    assert bootstrap(Config(scenario.env.workspace.root)).health=='ready'


def validate_report(report):
    from vde.contracts import validate
    from vde.p5.qa import IDS,CONDITIONAL
    validate(report,'qa_report')
    results=report['deterministic_checks']
    assert set(c['check_id'] for c in results)==set(IDS)
    assert len({(c['check_id'],c['criterion_id']) for c in results})==len(results)
    assert all(c['check_id'] in CONDITIONAL for c in results if c['status']=='SKIPPED')
    for c in results:validate(c,'qa_check_result')


def child_environment():
    import os
    env=os.environ.copy()
    env['PYTHONPATH']=str(ROOT/'src')+os.pathsep+str(ROOT/'tests')
    env['PYTHONDONTWRITEBYTECODE']='1'
    return env
