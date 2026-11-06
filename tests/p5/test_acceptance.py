"""76 owner-approved P5 IDs; immutable design oracles and actual integration."""
from copy import deepcopy
from dataclasses import replace
from datetime import date
from decimal import Decimal, localcontext
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest
from openpyxl import load_workbook
from vde.bootstrap import bootstrap
from vde.config import Config
from vde.contracts import validate,content_hash
from vde.errors import StorageError
from vde.execution.service import ExecutionService
from vde.execution.wire import decode_cell,iter_payload,REVISION
from vde.execution.errors import ExecutionError
from vde.persistence.repositories import ApprovalRepository,OrderRepository,ArtifactRepository
from vde.persistence.uow import UnitOfWork
from vde.storage import Storage
from vde.p5.budget import Budget
from vde.p5.contract import rows as semantic_rows
from vde.p5.errors import P5Error
from vde.p5.export import write
from vde.p5.project import semantic_row,csv_cell,numeric_preflight,describe
from vde.p5.qa import (Facts,criterion_result,evaluate_observation,typed,predicate,IDS,CONDITIONAL)
from vde.p5.roundtrip import verify,numeric_equal
from vde.p5.service import P5Service
from .support import (ROOT,BASELINE,Scenario,field,simple_change,pb_v2,load,checks,record,dq_cases,
                      projection_for,modify_xlsx,assert_completed,validate_report,child_environment,record_bytes)


@pytest.mark.parametrize('case',dq_cases(),ids=lambda c:c['test_id'])
def test_deterministic_check(case,tmp_path,design,monkeypatch):
    # The independent immutable pack supplies input observations and expected
    # status/count, never production output copied back into its own oracle.
    observation=deepcopy(case['setup'].get('dataset',{}))
    result=evaluate_observation(case['check_id'],observation,applicable=case['kind']!='NOT_APPLICABLE')
    expected=case['expected']
    for key in ('status','severity','affected_count'):
        assert result[key]==expected[key],(case['case_id'],key,result)
    if 'actual' in expected:assert result['actual']==expected['actual']
    assert (result['status']=='FAIL' and result['severity'] in ('BLOCKER','ERROR'))==expected['blocking']
    validate(result,'qa_check_result')
    number=int(case['test_id'][-2:])
    supplemental=[]
    if number==25:
        assert evaluate_observation('DQ-013',dict(null_count=3,row_count=10,max_ratio=0.3))['status']=='PASS'
        assert evaluate_observation('DQ-013',dict(null_count=4,row_count=10,max_ratio=0.3))['status']=='FAIL'
    if number in (19,20):
        a=Scenario(tmp_path/'pb','P-B_xlsx_sheet')
        context=P5Service(a.env).inspect(a.run_id,a.order())
        c=next(c for c in context.brief.document_json['acceptance_criteria'] if c['criterion_id']=='PB-AC-002')
        p=context.projection
        if number==20:
            columns=list(p.columns);columns[2],columns[3]=columns[3],columns[2];p=replace(p,columns=tuple(columns))
        f=SimpleNamespace(projection=p)
        r=criterion_result(c,f,{},context)
        assert r['status']==('PASS' if number==19 else 'FAIL')
        assert len(p.columns)==6
        assert not predicate('sequence_equals',list(context.projection.columns),c['expected'])
        generic=deepcopy(c);generic['criterion_id']='OTHER-AC-002'
        assert criterion_result(generic,f,{},context)['status']=='FAIL'
        supplemental.append({'PB_AC002_status':r['status'],'full_column_count':6,'generic_sequence_equals':'UNCHANGED'})
    if number in (21,22,31,32):
        decimal=projection_for(['decimal']);integer=projection_for(['integer'])
        if number in (21,31):
            values=[0,-1,10,9007199254740991,9007199254740992,9007199254740993,-(2**63),2**63-1]
            with localcontext() as ctx:
                ctx.prec=3
                for original in values:
                    raw=(original,);wide=semantic_row(raw,decimal)
                    assert type(wide[0]) is Decimal and wide[0]==Decimal(original)
                    assert raw==(original,) and type(raw[0]) is int
                    assert typed(wide[0],'decimal') and csv_cell(wide[0])==str(original)+'.0'
                    strict=semantic_row(raw,integer)
                    assert type(strict[0]) is int and csv_cell(strict[0])==str(original)
        else:
            for original in ('10','',None,True,False,10.0):
                projected=semantic_row((original,),decimal)[0]
                assert type(projected) is type(original) and projected==original
                assert not typed(projected,'decimal')
            assert not typed(semantic_row((Decimal('10'),),integer)[0],'integer')
            for token in ({'type':'integer','value':'01'},{'type':'integer','value':'9223372036854775808'},
                          {'type':'decimal','value':'10.00'},10.0,10):
                with pytest.raises(ExecutionError):decode_cell(token,expected_type='integer')
            with pytest.raises(P5Error):semantic_row((2**63,),decimal)
        supplemental.append({'CR_P5_003':'PASS','all_other_conversions':'FORBIDDEN'})
    if number in (33,34):
        raw=None
        if number==34:
            raw=modify_xlsx((ROOT/'pecs/pilot_slice_v1/fixtures/P-B_xlsx_sheet/input_orders.xlsx').read_bytes(),'F2','-20')
        a=Scenario(tmp_path/'ranges','P-B_xlsx_sheet',change=pb_v2,raw=raw)
        d=a.complete()
        scoped={c['criterion_id']:c for c in checks(d,'DQ-017') if c['criterion_id']}
        assert set(scoped)=={'PB-AC-006','PB-AC-007'}
        assert scoped['PB-AC-006']['target']['column']=='quantity' and scoped['PB-AC-006']['status']=='PASS'
        assert scoped['PB-AC-007']['target']['column']=='line_total'
        assert scoped['PB-AC-007']['status']==('PASS' if number==33 else 'FAIL')
        if number==33:
            assert scoped['PB-AC-006']['actual']==1 and Decimal(str(scoped['PB-AC-007']['actual']))==Decimal('20')
        else:assert d.order_status=='NEEDS_FIX'
        supplemental.append({'isolated_simulated_approval_only':True,'criterion_instances':list(scoped.values())})
    if number==34:
        # Exact Spec approval cannot silently erase an independent frozen Brief
        # field constraint. The real source/approval path still runs unchanged.
        def stricter_brief(b,s):
            simple_change([field('id','decimal')],rows=1)(b,s)
            b['fields'][0]['min_value']=10
            s['pipeline']=[dict(schema_version='1.1',operation_id='parse-domain',type='parse_number',input_dataset='raw',output_dataset='result',
                               params=dict(column='id',decimal_separator='.',thousands_separator=None,target_type='decimal',errors='FAIL'))]
        bounded=Scenario(tmp_path/'brief-domain',raw=b'id\n1\n',change=stricter_brief)
        checked=bounded.complete()
        assert checked.order_status=='NEEDS_FIX' and 'DQ-017' in checked.report['blocking_issues']
    if number in (39,40):
        a=Scenario(tmp_path/'roundtrip','P-B_xlsx_sheet',change=pb_v2)
        context=P5Service(a.env).inspect(a.run_id,a.order())
        _,raw=ExecutionService(a.env).read_result(a.run_id)
        path=tmp_path/'test-only.xlsx'
        with Budget() as budget:
            write(path,context.projection,semantic_rows(raw,context),budget)
            if number==40:path.write_bytes(modify_xlsx(path.read_bytes(),'F2','21'))
            if number==39:
                proof=verify(path,context.projection,semantic_rows(raw,context),budget)
                assert (proof['rows'],proof['columns'],proof['cells'])==(3,6,18)
            else:
                with pytest.raises(P5Error,match='Numeric value changed'):verify(path,context.projection,semantic_rows(raw,context),budget)
        numeric=load(design['base']/'fixtures/v02a_numeric_cases.json')
        for numeric_case in numeric['csv_positive']:
            value=decode_cell({'type':numeric_case['kind'],'value':numeric_case['p4_canonical_value']})
            assert csv_cell(value)==numeric_case['expected_csv_field']
        for numeric_case in numeric['csv_negative']:
            value=decode_cell({'type':numeric_case['kind'],'value':numeric_case['p4_canonical_value']})
            assert csv_cell(value)!=numeric_case['mutated_csv_field']
        assert a.delta()==dict(artifacts=0,qa_reports=0,event_log=0,approvals=0,execution_runs=0)
        supplemental.append({'full_PB_readback_cells':18,'real_P5_result_published':False,'numeric_csv_cases':15})
    record(case['test_id'],{'fixture':case['case_id'],'result':'PASS','observed_check':result,'supplemental':supplemental})


def test_T55_pa_actual_golden(tmp_path):
    a=Scenario(tmp_path)
    with a.uow() as u:run_before=u.runs.get(a.run_id);internal=u.artifacts.list_for_run(a.run_id)[0]
    raw=a.env.workspace.path(internal.workspace_relpath).read_bytes()
    assert {'type':'integer','value':'0'} in json.loads(raw)['rows'][-1]
    d=a.complete();assert_completed(a,d,'READY','PASS')
    actual=a.env.workspace.path(d.artifact.workspace_relpath).read_bytes()
    assert actual==(a.source/'expected_result.csv').read_bytes() and len(actual)==277
    record_bytes('P-A.actual-result.csv',actual)
    record_bytes('P-A.original-P4-INTERNAL.json',raw)
    assert d.report['dataset_summary']['checksum']=='c3b4e1f9a885bcf969cd34a9041951c1bed1abcd6aaba4c4f1f2fcd414d86cc9'
    assert a.env.workspace.path(internal.workspace_relpath).read_bytes()==raw
    with a.uow() as u:assert u.runs.get(a.run_id)==run_before
    import csv
    stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerows([['id'],['e\u0301'],['quoted, value'],['line\nbreak']])
    source=stream.getvalue().encode('utf-8')
    unicode_case=Scenario(tmp_path/'unicode',raw=source,change=simple_change([field()],rows=3))
    extra=unicode_case.complete()
    assert extra.order_status=='READY' and unicode_case.env.workspace.path(extra.artifact.workspace_relpath).read_bytes()==source
    record('P5-T55',{'result':'PASS','report':d.report,'P4_internal_unchanged':True,'source_unchanged':a.env.workspace.path(a.asset.workspace_relpath).read_bytes()==a.raw})


def test_T56_pb_actual_six_column_xlsx(tmp_path,design):
    a=Scenario(tmp_path,'P-B_xlsx_sheet',change=pb_v2)
    with a.uow() as u:
        spec=u.specs.get(a.handoff.transformation_spec_version_id)
        assert spec.version_number==2 and len(u.specs.list_for_order(a.order_id))==2
        assert spec.content_hash==load(design['pb']/'fixtures/P-B_versioned/transformation_spec_version_v2_CANDIDATE.json')['content_hash']
    _,original=ExecutionService(a.env).read_result(a.run_id)
    d=a.complete();assert_completed(a,d,'READY','PASS_WITH_WARNINGS')
    record_bytes('P-B.original-P4-INTERNAL.json',original)
    record_bytes('P-B.actual-result.xlsx',a.env.workspace.path(d.artifact.workspace_relpath).read_bytes())
    assert len(d.report['deterministic_checks'])==24 and 'XLSX_FORMULA_PRESENT' in d.report['warnings']
    assert d.report['dataset_summary']['column_count']==6 and d.report['dataset_summary']['row_count']==3
    book=load_workbook(io.BytesIO(a.env.workspace.path(d.artifact.workspace_relpath).read_bytes()),read_only=True,data_only=False)
    try:
        actual=list(book['Data'].rows)
        assert len(actual)==4 and all(len(r)==6 for r in actual)
        assert all(c.data_type!='f' for r in actual for c in r)
        assert [c.value for c in actual[0]]==d.report['dataset_summary']['output_headers']
    finally:book.close()
    p=projection_for(['string'],'XLSX');path=tmp_path/'formula-like-text.xlsx'
    values=[('=SUM(1,1)',),('+1',),('@x',),('-text',),('e\u0301',),('',),(None,)]
    with Budget() as b:
        write(path,p,iter(values),b);proof=verify(path,p,iter(values),b)
    assert proof['rows']==7
    record('P5-T56',{'result':'PASS','isolated_simulated_local_user_approval_only':True,'report':d.report,'numeric_and_string_readback':'PASS'})


def test_T57_pb_csv_is_test_projection_only(tmp_path):
    a=Scenario(tmp_path,'P-B_xlsx_sheet',change=pb_v2)
    context=P5Service(a.env).inspect(a.run_id,a.order());_,raw=ExecutionService(a.env).read_result(a.run_id)
    p=replace(context.projection,output={**context.projection.output,'format':'CSV','encoding':'UTF-8','delimiter':',','sheet_name':None})
    path=tmp_path/'test-only.csv'
    with Budget() as b:write(path,p,semantic_rows(raw,context),b);verify(path,p,semantic_rows(raw,context),b)
    assert path.read_bytes()==(a.source/'expected_result.csv').read_bytes() and path.stat().st_size==245
    record_bytes('P-B.TEST-ONLY-projection.csv',path.read_bytes())
    assert all(v==0 for v in a.delta().values())
    record('P5-T57',{'result':'PASS','csv_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'production_RESULT_CSV':0,'all_cells':18})


def test_T58_pd_diagnostic_csv_and_typed_failures(tmp_path):
    a=Scenario(tmp_path,'P-D_errors_and_qa_blockers');d=a.complete();assert_completed(a,d,'NEEDS_FIX','FAIL')
    assert a.env.workspace.path(d.artifact.workspace_relpath).read_bytes()==(a.source/'expected_result.csv').read_bytes()
    record_bytes('P-D.actual-diagnostic.csv',a.env.workspace.path(d.artifact.workspace_relpath).read_bytes())
    assert {'DQ-011','DQ-012','DQ-014'}<=set(d.report['blocking_issues'])
    assert d.error_json['code']=='QA_BLOCKER'
    validate(d.error_json,'execution_error')
    assert all(c['status']=='PASS' for c in checks(d,'DQ-022'))
    assert any(c['criterion_id']=='PD-AC-005' and c['actual'] is False for c in checks(d,'DQ-012'))
    record('P5-T58',{'result':'PASS','report':d.report,'diagnostic_not_delivery':True})


def test_T59_forged_approval_and_available_pc(tmp_path,monkeypatch,design):
    a=Scenario(tmp_path);before=a.snapshot();original=ApprovalRepository.get
    def forged(self,identity):
        value=original(self,identity)
        return replace(value,target_content_hash='0'*64) if value.target_type=='TRANSFORMATION_SPEC' else value
    with monkeypatch.context() as patch:
        patch.setattr('vde.p5.contract.health',lambda env:None)  # isolate post-recovery admission guard
        patch.setattr(ApprovalRepository,'get',forged)
        with pytest.raises((P5Error,StorageError)):
            a.complete()
    assert a.snapshot()==before and all(v==0 for v in a.delta().values())
    availability=load(design['base']/'fixtures/p0_pc_reachability_v02.json')
    assert len(availability['available_paths'])==10 and len(availability['missing_manifest_paths'])==13
    for p in availability['available_paths']:assert (ROOT/p).is_file()
    for p in availability['missing_manifest_paths']:assert not (ROOT/p).exists()
    pc=ROOT/'pecs/pilot_slice_v1/fixtures/P-C_approval_safety/invalid_examples'
    from jsonschema.exceptions import ValidationError
    for name,schema in [('brief_approval_with_context.schema_invalid.json','approval'),('brief_with_approved_at.schema_invalid.json','brief_version'),('output_name_with_tab.invalid.json','brief_version')]:
        with pytest.raises(ValidationError):validate(load(pc/name),schema)
    record('P5-T59',{'result':'PASS','forged_admission':'REJECTED_NO_WRITES','available_PC_files':10,'missing_PC_files':13,'full_PC_positive':'BLOCKED'})


def test_T60_missing_required_column_fails_without_dummy_report(tmp_path,monkeypatch):
    a=Scenario(tmp_path);original=describe
    def missing(brief,spec,columns):
        return original(brief,spec,columns[1:])
    with monkeypatch.context() as patch:
        patch.setattr('vde.p5.contract.describe',missing)
        with pytest.raises(P5Error) as err:a.complete()
    assert err.value.code=='SCHEMA_MISMATCH' and a.order().status=='FAILED'
    assert a.delta()==dict(artifacts=0,qa_reports=0,event_log=1,approvals=0,execution_runs=0)
    record('P5-T60',{'result':'PASS','error':err.value.code,'final_artifacts':0,'reports':0,'Order':'FAILED'})


def test_T61_duplicate_id_blocks_ready(tmp_path):
    fs=[field(unique=True)]
    a=Scenario(tmp_path,raw=b'id\nA\nA\n',change=simple_change(fs))
    d=a.complete();assert_completed(a,d,'NEEDS_FIX','FAIL')
    assert checks(d,'DQ-014')[0]['affected_count']==1
    record('P5-T61',{'result':'PASS','duplicate_count':1,'report':d.report})


def test_T62_parse_null_preserved_and_warned(tmp_path):
    a=Scenario(tmp_path,'P-D_errors_and_qa_blockers');_,raw=ExecutionService(a.env).read_result(a.run_id)
    before=list(iter_payload(raw));assert any(None in row for row in before)
    d=a.complete();assert_completed(a,d,'NEEDS_FIX','FAIL')
    assert any(c['status']=='WARN' for c in checks(d,'DQ-015'))
    assert all(c['status']=='PASS' for c in checks(d,'DQ-022'))
    assert csv_cell(None)==csv_cell('')==''
    record('P5-T62',{'result':'PASS','typed_null_evidence':True,'lexical_roundtrip':'PASS','report':d.report})


def test_T63_writer_failure_and_csv_injection(tmp_path,monkeypatch):
    a=Scenario(tmp_path/'io')
    with monkeypatch.context() as patch:
        def broken(*args,**kwargs):raise OSError('Injected writer failure')
        patch.setattr('vde.p5.service.writer.write',broken)
        with pytest.raises(P5Error) as err:a.complete()
    assert err.value.code=='EXPORT_FAILED' and a.order().status=='FAILED'
    assert a.delta()['artifacts']==0 and a.delta()['qa_reports']==0 and a.delta()['event_log']==1
    for index,text in enumerate(('=SUM(1,1)',' +1','\t-2','\u2003\x01@calc')):
        # Quoting/escaping is done solely to form the input fixture. The source
        # cell itself must remain unchanged and must be rejected at export.
        import csv
        s=io.StringIO(newline='');csv.writer(s,lineterminator='\n').writerows([['id'],[text]])
        b=Scenario(tmp_path/str(index),raw=s.getvalue().encode(),change=simple_change([field()],rows=1))
        with pytest.raises(P5Error) as caught:b.complete()
        assert caught.value.code=='EXPORT_FAILED' and b.order().status=='FAILED' and b.delta()['artifacts']==0
        assert b.env.workspace.path(b.asset.workspace_relpath).read_bytes()==b.raw
    record('P5-T63',{'result':'PASS','writer_failure':'EXPORT_FAILED','formula_strings_rejected':4,'silent_prefix':False})


def test_T64_precision_and_independent_numeric_guards(tmp_path,monkeypatch,design):
    numeric=load(design['base']/'fixtures/v02a_numeric_cases.json')
    for item in numeric['xlsx_positive']:
        v=decode_cell({'type':item['kind'],'value':item['p4_canonical_value']})
        p=projection_for([item['kind']],'XLSX');path=tmp_path/(item['case_id']+'.xlsx')
        with Budget() as b:
            write(path,p,iter([(v,)]),b);assert verify(path,p,iter([(v,)]),b)['cells']==1
    for value in (9007199254740993,-(2**63),2**63-1,Decimal('123456789012345.6789'),Decimal('0.10000000000000001')):
        with pytest.raises(P5Error):numeric_preflight(value)
    for actual,xml,kind in ((15.6,'15.5','n'),(15.5,'15.6','n'),('15.5','15.5','s'),(True,'15.5','n')):
        with pytest.raises(P5Error) as error:numeric_equal(Decimal('15.5'),actual,kind,(kind,xml))
        assert error.value.code=='ROUNDTRIP_MISMATCH'
    for index,(kind,token,parse_kind) in enumerate((('integer','9007199254740993','integer'),('decimal','9007199254740993','integer'),('decimal','123456789012345.6789','decimal'))):
        fields=[field('id',kind)]
        change=simple_change(fields,'XLSX',rows=1)
        raw=('id\n'+token+'\n').encode()
        def transform(b,s,change=change,parse_kind=parse_kind):
            change(b,s)
            s['pipeline']=[dict(schema_version='1.1',operation_id='parse-exact',type='parse_number',input_dataset='raw',output_dataset='result',
                               params=dict(column='id',decimal_separator='.',thousands_separator=None,target_type=parse_kind,errors='FAIL'))]
        a=Scenario(tmp_path/f'preflight-{index}',raw=raw,change=transform)
        with pytest.raises(P5Error) as error:a.complete()
        assert error.value.code=='EXPORT_FAILED' and a.order().status=='FAILED' and a.delta()['artifacts']==0
        b=Scenario(tmp_path/f'bypass-{index}',raw=raw,change=transform)
        with monkeypatch.context() as patch:
            patch.setattr('vde.p5.export.numeric_preflight',lambda value:None)
            with pytest.raises(P5Error) as error:b.complete()
        assert error.value.code=='ROUNDTRIP_MISMATCH' and b.order().status=='FAILED' and b.delta()['artifacts']==0
    # Whole-service signed64 boundaries are exact in integer CSV and in the
    # approved decimal semantic projection, with original P4 tags retained.
    tokens=['9007199254740991','9007199254740992','9007199254740993',str(-(2**63)),str(2**63-1)]
    for kind in ('integer','decimal'):
        def bounds(b,s,kind=kind):
            simple_change([field('id',kind)],rows=len(tokens))(b,s)
            s['pipeline']=[dict(schema_version='1.1',operation_id='parse-bounds',type='parse_number',input_dataset='raw',output_dataset='result',
                params=dict(column='id',decimal_separator='.',thousands_separator=None,target_type='integer',errors='FAIL'))]
        a=Scenario(tmp_path/('csv-bounds-'+kind),raw=('id\n'+'\n'.join(tokens)+'\n').encode(),change=bounds)
        with a.uow() as u:internal=u.artifacts.list_for_run(a.run_id)[0]
        original=a.env.workspace.path(internal.workspace_relpath).read_bytes()
        d=a.complete();assert d.order_status=='READY'
        expected=('id\n'+'\n'.join(t+('.0' if kind=='decimal' else '') for t in tokens)+'\n').encode()
        assert a.env.workspace.path(d.artifact.workspace_relpath).read_bytes()==expected
        assert a.env.workspace.path(internal.workspace_relpath).read_bytes()==original
    large=Scenario(tmp_path/'xlsx-text-capacity',raw=b'id\n'+b'x'*32768+b'\n',
                   change=simple_change([field()],'XLSX',rows=1))
    with pytest.raises(P5Error) as error:large.complete()
    assert error.value.code=='EXPORT_FAILED' and large.order().status=='FAILED' and large.delta()['artifacts']==0
    # An actual changed staged CSV is rejected before publication.
    a=Scenario(tmp_path/'changed-csv')
    def tamper(stage):
        if stage=='after_stage':
            p=next(a.env.workspace.path('.staging').glob('p5-*/result.csv'))
            p.write_bytes(p.read_bytes().replace(b'1234.5',b'1234.6'))
    with pytest.raises(P5Error) as error:a.complete(checkpoint=tamper)
    assert error.value.code=='ROUNDTRIP_MISMATCH' and a.delta()['artifacts']==0
    record('P5-T64',{'result':'PASS','preflight_rejections':5,'separate_numeric_guard_mutations':4,'actual_service_preflight_and_bypass':6,'changed_CSV':'REJECTED'})


def test_T65_corrupt_internal_storage_blocks_without_writes(tmp_path):
    a=Scenario(tmp_path)
    with a.uow() as u:internal=u.artifacts.list_for_run(a.run_id)[0]
    before=a.snapshot();a.env.workspace.path(internal.workspace_relpath).write_bytes(b'corrupt')
    with pytest.raises(P5Error) as err:a.complete()
    assert err.value.code=='STORAGE_ERROR' and a.snapshot()==before
    assert bootstrap(Config(a.env.workspace.root)).health=='blocked'
    record('P5-T65',{'result':'PASS','health':'blocked','writes':0})


def test_T66_wrong_context_and_missing_pb_reference(tmp_path,monkeypatch):
    a=Scenario(tmp_path/'context');before=a.snapshot();get=OrderRepository.get
    selected=replace(a.order(),selected_transformation_spec_version_id='foreign-spec')
    def wrong(self,identity):return replace(get(self,identity),selected_transformation_spec_version_id='foreign-spec')
    with monkeypatch.context() as patch:
        patch.setattr('vde.p5.contract.health',lambda env:None)
        patch.setattr(OrderRepository,'get',wrong)
        with pytest.raises(P5Error) as error:P5Service(a.env).complete(a.run_id,selected)
    assert error.value.code=='VERSION_INCOMPATIBLE' and a.snapshot()==before
    future=Scenario(tmp_path/'future-test-only');snapshot=future.snapshot();get_approval=ApprovalRepository.get
    def synthetic(self,identity):
        approval=get_approval(self,identity)
        return replace(approval,approved_at='2099-01-01T00:00:00Z') if approval.target_type=='TRANSFORMATION_SPEC' else approval
    with monkeypatch.context() as patch:
        patch.setattr('vde.p5.contract.health',lambda env:None)
        patch.setattr(ApprovalRepository,'get',synthetic)
        with pytest.raises(P5Error) as error:future.complete()
    assert error.value.code=='APPROVAL_MISSING' and future.snapshot()==snapshot
    b=Scenario(tmp_path/'original-pb','P-B_xlsx_sheet');d=b.complete()
    assert all(c['criterion_id']!='PB-AC-007' for c in d.report['deterministic_checks'])
    assert 'PB-AC-007' not in b.handoff.transformation_spec_version_id
    record('P5-T66',{'result':'PASS','wrong_context':'REJECTED','PB_AC007_in_original_spec':'NOT_AUTHORIZED_NOT_EVALUATED'})


def test_T67_repeat_and_competing_calls_do_not_duplicate(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    a=Scenario(tmp_path);service=P5Service(a.env)
    expected=a.order()
    with ThreadPoolExecutor(max_workers=2) as pool:
        initial=list(pool.map(lambda _:service.complete(a.run_id,expected),range(2)))
    assert {r.repeated for r in initial}=={False,True} and initial[0].artifact==initial[1].artifact
    first=initial[0];before=a.snapshot()
    second=service.complete(a.run_id,a.order())
    assert second.repeated and second.artifact==first.artifact and second.report==first.report and a.snapshot()==before
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:service.complete(a.run_id,a.order()),range(2)))
    assert all(r.repeated and r.artifact.id==first.artifact.id for r in results) and a.snapshot()==before
    retry=Scenario(tmp_path/'fresh-P4-required')
    def fail_write(stage):
        if stage=='before_write':raise P5Error('EXPORT_FAILED','Injected first attempt failure')
    with pytest.raises(P5Error):retry.complete(checkpoint=fail_write)
    old_run=retry.run_id
    execution=ExecutionService(retry.env)
    newer=execution.execute(retry.order_id,retry.order(),execution.fresh_handoff(retry.order_id))
    snapshot=retry.snapshot()
    with pytest.raises(P5Error) as error:P5Service(retry.env).complete(old_run,retry.order())
    assert error.value.code=='STATE_INVALID_TRANSITION' and retry.snapshot()==snapshot
    fresh=P5Service(retry.env).complete(newer.run_id,retry.order())
    assert fresh.order_status=='READY'
    record('P5-T67',{'result':'PASS','terminal_repeats':3,'artifacts_total':1,'reports_total':1,'writes_after_first':0})


def crash_case(tmp_path,stage):
    a=Scenario(tmp_path)
    command=[sys.executable,'-m','p5.restart_probe',str(a.env.workspace.root),a.run_id,stage]
    child=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,env=child_environment())
    assert child.returncode==-signal.SIGKILL,(stage,child.stdout,child.stderr)
    env=bootstrap(Config(a.env.workspace.root));before=a.snapshot()
    record('crash-'+stage,{'command':command,'exit_code':child.returncode,'stdout':child.stdout,'stderr':child.stderr,
                          'health':env.health,'delta':a.delta(),'Order':a.order().status})
    return a,env,before


def test_T68_orphan_after_promotion_detect_only(tmp_path):
    a,env,before=crash_case(tmp_path,'artifact_promoted')
    assert env.health=='degraded' and env.recovery.orphans and a.order().status=='EXECUTING'
    assert a.delta()['artifacts']==a.delta()['qa_reports']==a.delta()['event_log']==0
    with pytest.raises(P5Error) as error:P5Service(env).complete(a.run_id,a.order())
    assert error.value.code=='STORAGE_ERROR' and a.snapshot()==before
    record('P5-T68',{'result':'PASS','detect_only':'degraded_orphan','auto_adoption':False})


def test_T69_committed_artifact_reused_after_sigkill(tmp_path,monkeypatch):
    a,env,before=crash_case(tmp_path,'after_artifact_commit')
    assert env.health=='ready' and a.order().status=='EXECUTING' and a.delta()['artifacts']==1
    assert a.delta()['qa_reports']==0 and a.delta()['event_log']==1
    with monkeypatch.context() as patch:
        def forbidden(*args,**kwargs):raise AssertionError('A committed Artifact must be reused')
        patch.setattr(Storage,'register_artifact',forbidden)
        patch.setattr(ExecutionService,'read_result',forbidden)
        d=P5Service(env).complete(a.run_id,a.order())
    assert_completed(a,d,'READY','PASS')
    pb=Scenario(tmp_path/'pb-reuse','P-B_xlsx_sheet',change=pb_v2)
    def pause(stage):
        if stage=='after_artifact_commit':raise SystemExit('Isolated interrupted completion')
    with pytest.raises(SystemExit):pb.complete(checkpoint=pause)
    assert pb.delta()['artifacts']==1 and pb.delta()['qa_reports']==0 and pb.order().status=='EXECUTING'
    with monkeypatch.context() as patch:
        patch.setattr(Storage,'register_artifact',lambda *a,**k:pytest.fail('XLSX Artifact must be reused'))
        finished=pb.complete()
    assert_completed(pb,finished,'READY','PASS_WITH_WARNINGS')
    record('P5-T69',{'result':'PASS','new_artifact_registrations_on_retry':0,'reused_artifact_id':d.artifact.id})


def test_T70_report_transaction_rolls_back_and_retry_reuses(tmp_path,monkeypatch):
    a=Scenario(tmp_path)
    def abort(stage):
        if stage=='after_report_append':raise StorageError('Injected report UoW abort')
    with pytest.raises(P5Error) as error:a.complete(checkpoint=abort)
    assert error.value.code=='STORAGE_ERROR' and a.order().status=='EXECUTING'
    assert a.delta()['artifacts']==1 and a.delta()['qa_reports']==0 and a.delta()['event_log']==1
    assert bootstrap(Config(a.env.workspace.root)).health=='ready'
    with monkeypatch.context() as patch:
        patch.setattr(Storage,'register_artifact',lambda *a,**k:pytest.fail('Second registration forbidden'))
        d=a.complete()
    assert_completed(a,d,'READY','PASS')
    record('P5-T70',{'result':'PASS','report_uow_rolled_back':True,'artifact_reused':True})


def test_T71_terminal_commit_survives_restart_read_only(tmp_path,monkeypatch):
    a,env,before=crash_case(tmp_path,'after_report_commit')
    assert env.health=='ready' and a.order().status=='READY'
    with monkeypatch.context() as patch:
        patch.setattr(ExecutionService,'read_result',lambda *a,**k:pytest.fail('Terminal replay cannot call P4 read_result'))
        patch.setattr(Storage,'register_artifact',lambda *a,**k:pytest.fail('Terminal replay cannot register'))
        d=P5Service(env).complete(a.run_id,a.order())
    assert d.repeated and a.snapshot()==before
    assert_completed(a,d,'READY','PASS')
    record('P5-T71',{'result':'PASS','terminal_repeat_read_only':True,'artifact_id':d.artifact.id})


def test_T72_csv_and_xlsx_100000_by_200(tmp_path,design):
    outcomes=[]
    for format in ('CSV','XLSX'):
        directory=tmp_path/format;directory.mkdir()
        command=[sys.executable,'-m','p5.stress_probe','--design-root',str(design['base']),'--directory',str(directory),'--format',format]
        run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=3600,env=child_environment())
        record('stress-'+format,{'command':command,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
        assert run.returncode==0,(format,run.stdout,run.stderr)
        outcome=json.loads(run.stdout)
        assert outcome['rows']==100000 and outcome['columns']==200 and outcome['independent_cells_checked']==20000000
        assert outcome['incremental_peak_rss_bytes']<=536870912 and outcome['Order']=='READY' and outcome['QA']=='PASS'
        outcomes.append(outcome)
    command=[sys.executable,'-m','p5.stress_probe','--design-root',str(design['base']),
             '--directory',str(tmp_path/'oversized'),'--format','CSV','--negative-oversized']
    run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=1800,env=child_environment())
    record('stress-negative-expanded-text',{'command':command,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
    assert run.returncode==0,(run.stdout,run.stderr)
    negative=json.loads(run.stdout)
    assert negative['safe_preallocation_rejection'] and negative['new_final_artifacts']==0
    # A separate forced budget limit is a negative control, never a substitute
    # for either successful fixed workload above.
    a=Scenario(tmp_path/'limit')
    with pytest.raises(P5Error) as error:a.complete(budget_factory=lambda:Budget(limit=0,rss_reader=iter([100,101,102,103,104]).__next__))
    assert error.value.code=='EXPORT_FAILED' and a.order().status!='READY' and a.delta()['artifacts']==0
    record('P5-T72',{'result':'PASS','positive_runs':outcomes,'large_text_negative':negative,'separate_budget_exceed':'FAIL_CLOSED'})


def test_T73_external_historical_212_and_76_inventory(design):
    path=Path(os.environ.get('P5_HISTORICAL_JUNIT',str(ROOT/'docs/p5/validation/implementation-admission-20261106/historical-212/results.xml')))
    cases=list(ET.parse(path).getroot().iter('testcase'))
    assert len(cases)==212
    import re,ast
    phases={i:[] for i in range(1,5)}
    for case in cases:
        assert not any(case.find(k) is not None for k in ('failure','error','skipped'))
        phase=int(re.search(r'(?:^|\.)p([1-4])(?:\.|$)',case.get('classname')).group(1))
        number=int(re.search(r'^test_T(\d+)_',case.get('name')).group(1));phases[phase].append(number)
    for phase,count in ((1,42),(2,54),(3,52),(4,64)):assert sorted(phases[phase])==list(range(1,count+1))
    source=ast.parse(Path(__file__).read_text())
    names=[int(n.name.split('_')[1][1:]) for n in source.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_T')]
    ids={c['test_id'] for c in dq_cases()}|{f'P5-T{n:02}' for n in names}
    assert ids=={f'P5-T{i:02}' for i in range(1,77)}
    record('P5-T73',{'result':'PASS','external_historical_junit':str(path),'historical_tests':212,'P5_unique_definitions':76,'nested_full_pytest_invocations':0})


def test_T74_real_p0_schemas_and_immutable_pb_specimen(design):
    from vde.contracts import validators
    assert len(validators())==20
    for name in ('P_A','P_B','P_D'):
        validate(load(design['base']/f'fixtures/qa_report_specimen_{name}.json'),'qa_report')
    specimen=load(design['pb']/'fixtures/P-B_versioned/qa_report_specimen_v2_TEST_ONLY.json')
    validate(specimen,'qa_report')
    assert len(specimen['deterministic_checks'])==24
    assert {c['criterion_id'] for c in specimen['deterministic_checks'] if c['check_id']=='DQ-017'}=={'PB-AC-006','PB-AC-007'}
    old=load(ROOT/'pecs/pilot_slice_v1/fixtures/P-B_xlsx_sheet/expected_qa_report.json')
    assert next(c for c in old['deterministic_checks'] if c['check_id']=='DQ-022')['actual']=={'rows':3,'columns':5}
    original=load(ROOT/'pecs/pilot_slice_v1/fixtures/P-B_xlsx_sheet/transformation_spec_version.json')
    assert 'PB-AC-007' not in original['acceptance_criteria_ref']
    assert load(design['pb']/'fixtures/P-B_versioned/transformation_approval_v2_TEST_ONLY.json')['approved_at'].startswith('2099-')
    record('P5-T74',{'result':'PASS','real_schema_count':20,'original_PB_contradictions':'PRESERVED','synthetic_approval_is_business_authority':False})


def test_T75_streamlit_explicit_action_and_passive_rerender(tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    a=Scenario(tmp_path);monkeypatch.setenv('VDE_WORKSPACE',str(a.env.workspace.root))
    app=AppTest.from_file(str(ROOT/'src/vde/app.py'),default_timeout=120).run()
    assert not app.exception
    app.checkbox(key='p5_open').check().run()
    assert not app.exception
    before=a.counts()
    app.button(key='p5_complete').click().run()
    assert not app.exception
    assert a.order().status=='READY' and a.counts()['qa_reports']==before['qa_reports']+1
    snapshot=a.snapshot();app.run();app.run()
    assert not app.exception and a.snapshot()==snapshot
    assert a.delta()['artifacts']==1 and a.delta()['event_log']==2
    record('P5-T75',{'result':'PASS','clicks':1,'passive_rerenders':2,'report_count':1,'artifact_count':1})


def test_T76_successor_scope_negatives_and_ambiguous_result(tmp_path,monkeypatch):
    from .scope_audit import audit,negative_probes
    audit(ROOT);probes=negative_probes(ROOT,tmp_path/'mutations')
    assert probes and all(p['result']=='REJECTED' for p in probes)
    a=Scenario(tmp_path/'ambiguity');d=a.complete();before=a.snapshot();get=ArtifactRepository.list_for_run
    def ambiguous(self,run_id):
        actual=get(self,run_id)
        return actual+[replace(d.artifact,id='extra-unapproved-result')] if run_id==a.run_id else actual
    with monkeypatch.context() as patch:
        patch.setattr('vde.p5.contract.health',lambda env:None)
        patch.setattr(ArtifactRepository,'list_for_run',ambiguous)
        with pytest.raises(P5Error) as error:a.complete()
    assert error.value.code=='STORAGE_ERROR' and a.snapshot()==before
    record('P5-T76',{'result':'PASS','successor_scope_mutations':probes,'ambiguous_final_result':'REJECTED_NO_WRITES'})
