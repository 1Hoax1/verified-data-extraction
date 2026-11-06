"""Static design-only validation of owner-approved CR-P5-001 P-B supplement.

No P5 production module and no real Approval/QA execution is performed.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, re, sys, unicodedata
from pathlib import Path
from datetime import datetime,timezone

ROOT = Path(__file__).resolve().parent.parent
V1_HASH='d7c30e08e6d03054d4a15daeb741f64c1f4fef64c225208d98c1659f8e82f2aa'
BRIEF_HASH='9b7c2b0111360714dfbc9cbdbc755b693b11e067f32771cb226126fdcd1ffb49'
KEYS=('schema_version','brief_version_id','brief_content_hash','inputs','pipeline','output','execution_policy','provenance_policy','expected_schema','acceptance_criteria_ref')


def read(path):return json.loads((ROOT/path).read_text('utf-8'))
def need(test,why):
    if not test: raise AssertionError(why)
def norm(v):
    if isinstance(v,str):return unicodedata.normalize('NFC',v)
    if isinstance(v,list):return [norm(x) for x in v]
    if isinstance(v,dict):return {norm(k):norm(x) for k,x in v.items()}
    return v

def hash_semantic(o):
    payload={k:o[k] for k in KEYS}
    def no_floats(v):
        if isinstance(v,float):raise AssertionError('No binary floating point permitted in P-B hash source')
        if isinstance(v,list):[no_floats(x) for x in v]
        if isinstance(v,dict):[no_floats(x) for x in v.values()]
    no_floats(payload)
    return hashlib.sha256(json.dumps(norm(payload),ensure_ascii=False,separators=(',',':'),sort_keys=True,allow_nan=False).encode('utf-8')).hexdigest()

def validate(old,spec,approval,req,oracle,report):
    need(hash_semantic(old)==V1_HASH,'original normative Spec semantic reconstruction hash differs')
    need(spec['content_hash']==hash_semantic(spec),'v2 content hash invalid')
    need(spec['schema_version']=='1.1' and spec['version_id']=='transform-pb-v2-cr-p5-001' and spec['version_number']==2,'wrong P-B version identity')
    need(spec['order_id']=='order-pb' and spec['brief_version_id']=='brief-pb-v1' and spec['brief_content_hash']==BRIEF_HASH,'wrong Brief context')
    need(spec['output']['format']=='XLSX' and len(spec['output']['column_order'])==6,'wrong production format/full-six output')
    need(spec['acceptance_criteria_ref']==[f'PB-AC-{i:03d}' for i in range(1,8)],'incorrect reference list')
    need(len(spec['expected_schema'])==6 and spec['expected_schema'][-1]['name']=='line_total','sixth field missing')
    # Only CR-approved semantic difference is adding a single criterion reference.
    spec_sem={k:spec[k] for k in KEYS}
    orig_sem={k:old[k] for k in KEYS}
    need(set(old)==set(KEYS),'old semantic payload is not exact closed set')
    need({k:spec_sem[k] for k in KEYS if k!='acceptance_criteria_ref'}=={k:orig_sem[k] for k in KEYS if k!='acceptance_criteria_ref'},'unauthorized semantic drift')
    need(spec['acceptance_criteria_ref']==old['acceptance_criteria_ref']+['PB-AC-007'],'not append-only reference')
    need(approval['schema_version']=='1.1' and approval['order_id']==spec['order_id'] and approval['target_type']=='TRANSFORMATION_SPEC','Approval wrong scope')
    need(approval['target_version_id']==spec['version_id'] and approval['target_content_hash']==spec['content_hash'],'Approval hash/version mismatch')
    need(approval['context_brief_version_id']==spec['brief_version_id'] and approval['context_brief_content_hash']==BRIEF_HASH,'Approval Brief context mismatch')
    need(approval['approved_by']=='local_user' and approval['approved_at']=='2099-01-01T00:00:00Z' and 'TEST-ONLY' in approval['id'],'test-only approval must be unambiguously synthetic')
    need(req['status']=='PENDING_NEW_EXPLICIT_LOCAL_APPROVAL' and req['target_version_id']==spec['version_id'] and req['target_content_hash']==spec['content_hash'],'missing real Approval guard')
    need(oracle['new_content_hash']==spec['content_hash'] and oracle['new_version_id']==spec['version_id'],'oracle wrong spec hash/identity')
    need(oracle['approved_spec_version_exists_in_runtime'] is False and oracle['real_approval_issued'] is False,'false live approval claim')
    need(oracle['p0_original_spec_v1_hash']==V1_HASH and oracle['original_p0_unchanged'] is True,'P0 preservation claim')
    need(oracle['full_order']==spec['output']['column_order'] and len(oracle['full_order'])==6,'oracle schema mismatch')
    need(oracle['one_production_result']=='RESULT_XLSX' and oracle['test_only_csv'] is True,'second production output')
    need(oracle['pb_ac002']['scope']=='P_B_ONLY' and oracle['pb_ac002']['global_sequence_equals_unchanged'] is True,'generic sequence_equals changed')
    need(oracle['pb_ac002']['five_targets']==oracle['full_order'][:5],'PB-AC-002 five targets changed')
    need(oracle['dq022']['expected']=={'rows':3,'columns':6} and len(oracle['dq022']['headers'])==6 and oracle['dq022']['cells']==18,'DQ-022 wrong 3x6 full result')
    need(oracle['dq022']['requires_actual_export_re_read'] is True,'roundtrip must be real at Gate B')
    checks=oracle['dq017']
    need(len(checks)==2 and [(c['check_id'],c['criterion_id'],c['column'],c['expected']) for c in checks]==[
      ('DQ-017','PB-AC-006','quantity',1),('DQ-017','PB-AC-007','line_total',0)],'DQ017 criterion multiplicity incorrect')
    need(all(c['criterion_id'] in spec['acceptance_criteria_ref'] for c in checks),'unreferenced DQ017 criterion')
    need(report['schema_version']=='1.1' and report['transformation_spec_version_id']==spec['version_id']
      and report['brief_version_id']==spec['brief_version_id'],'QAReport exact Spec/Brief binding')
    need('TEST-ONLY' in report['report_id'] and 'TEST-ONLY' in report['run_id'] and report['generated_at'].startswith('2099-'),'false QAReport live authority')
    checks_report=report['deterministic_checks']
    need(len(checks_report)==24 and len(set(c['check_id'] for c in checks_report))==23,'incorrect v2 report check coverage')
    dq17=[c for c in checks_report if c['check_id']=='DQ-017']
    need([(c['criterion_id'],c['target']['column']) for c in dq17]==[(x['criterion_id'],x['column']) for x in checks],'wrong DQ17 criterion report binding')
    need(report['dataset_summary']['columns']==oracle['full_order'] and report['dataset_summary']['row_count']==3,'QAReport six-column dataset mismatch')
    need([x['artifact_type'] for x in report['artifacts']]==['RESULT_XLSX'],'QAReport incorrect production artifact')
    need(report['llm_review']=={'status':'NOT_APPLICABLE','reason':'PILOT_SLICE_V1_NO_LLM'},'LLM added')
    return spec['content_hash']

def mutations(old,spec,approval,req,oracle,report):
    changes=[
      ('wrong_v2_hash',0,'content_hash','0'*64),
      ('reintroduce_missing_007',0,'acceptance_criteria_ref',[f'PB-AC-{i:03d}' for i in range(1,7)]),
      ('forbidden_second_format',0,'output', {**spec['output'],'format':'CSV'}),
      ('silent_sixth_drop',0,'expected_schema',spec['expected_schema'][:5]),
      ('forged_approval_target',1,'target_version_id','transform-pb-v1'),
      ('forged_approval_hash',1,'target_content_hash',V1_HASH),
      ('wrong_brief_context',1,'context_brief_content_hash','f'*64),
      ('fake_real_approval',3,'real_approval_issued',True),
      ('wrong_DQ022',3,'dq022',{**oracle['dq022'],'expected':{'rows':3,'columns':5}}),
      ('wrong_DQ017_duplicate',3,'dq017', [{**oracle['dq017'][0]},{**oracle['dq017'][1],'criterion_id':'PB-AC-006'}]),
      ('generic_sequence_equals_modification',3,'pb_ac002',{**oracle['pb_ac002'],'scope':'GLOBAL'}),
      ('second_registered_csv',3,'one_production_result','RESULT_CSV'),
      ('wrong_QAReport_spec_version',4,'transformation_spec_version_id','transform-pb-v1'),
      ('missing_QAReport_DQ017',4,'deterministic_checks',[x for x in report['deterministic_checks'] if x['criterion_id']!='PB-AC-007']),
      ('extra_QAReport_CSV_artifact',4,'artifacts',report['artifacts']+[{'artifact_type':'RESULT_CSV','path':'bad.csv','checksum':'a'*64}]),
    ]
    all=[]
    for label,which,key,newval in changes:
      arr=copy.deepcopy([spec,approval,req,oracle,report]);arr[which][key]=newval
      try:validate(old,*arr)
      except AssertionError:all.append(label)
      else:raise AssertionError('mutation accepted: '+label)
    return all

def baseline_manifest(base):
  m=json.loads((base/'PACK_MANIFEST.json').read_text('utf-8'))
  fail=[]
  for o in m['files']:
    p=base/o['path']
    if not p.is_file() or p.stat().st_size!=o['size_bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=o['sha256']:
      fail.append(o['path'])
  need(not fail,'v0.2a original manifest mismatch: '+repr(fail))
  return len(m['files'])

def main():
  ap=argparse.ArgumentParser();ap.add_argument('--mutations',action='store_true');ap.add_argument('--base-root',type=Path,required=True);args=ap.parse_args()
  old=read('fixtures/P-B_versioned/original_spec_v1_semantic_payload_RECONSTRUCTED.json')
  spec=read('fixtures/P-B_versioned/transformation_spec_version_v2_CANDIDATE.json')
  approval=read('fixtures/P-B_versioned/transformation_approval_v2_TEST_ONLY.json')
  req=read('fixtures/P-B_versioned/approval_request_v2_PENDING.json')
  oracle=read('fixtures/P-B_versioned/p_b_versioned_oracle_candidate.json')
  report=read('fixtures/P-B_versioned/qa_report_specimen_v2_TEST_ONLY.json')
  digest=validate(old,spec,approval,req,oracle,report)
  result={
    'status':'STATIC_DESIGN_SUPPLEMENT_PASS','base_v02a_manifest_checked':baseline_manifest(args.base_root),
    'historical_spec_semantic_hash_reproduced':V1_HASH,'new_spec_v2_hash':digest,
    'new_spec_refs':len(spec['acceptance_criteria_ref']),'full_output_columns':6,
    'production_format':'XLSX','DQ022_cells_to_check_at_runtime':18,
    'DQ017_criterion_pairs':[(x['check_id'],x['criterion_id']) for x in oracle['dq017']],
    'QAReport_TEST_ONLY_check_rows':len(report['deterministic_checks']),
    'test_only_synthetic_approval_valid_binding':'YES','real_owner_approval':'NOT_ISSUED',
    'p0_schema_full_checkout':'NOT_RUN','P5_runtime':'NOT_RUN','gate_a':'NOT_PASSED'
  }
  if args.mutations:result['mutations_rejected']=mutations(old,spec,approval,req,oracle,report)
  print(json.dumps(result,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':
  try:sys.exit(main())
  except Exception as exc:
    print('P5_PB_SUPPLEMENT_STATIC_FAIL: '+repr(exc),file=sys.stderr);sys.exit(1)
