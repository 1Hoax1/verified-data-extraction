"""Reproducible CR-P5-002 outer runner: three distinct evidence families.

Run from a committed P5 tree, with an actual prior historical-run directory.
Original test-generated validation files are captured separately and restored.
No test is deselected, skipped, xfailed, patched or reclassified as PASS.
"""
import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
from time import monotonic
import xml.etree.ElementTree as ET
import zipfile
from zoneinfo import ZoneInfo

from .support import ROOT,BASELINE,child_environment


def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()


def junit(path):
    rows=[]
    for c in ET.parse(path).getroot().iter('testcase'):
        outcome=next((k for k in ('failure','error','skipped') if c.find(k) is not None),'pass')
        properties={p.get('name'):p.get('value') for p in c.findall('./properties/property')}
        rows.append(dict(name=c.get('name'),classname=c.get('classname'),outcome=outcome,
                         properties=properties,assertion=c.find(outcome).text if outcome!='pass' else None))
    return rows


def record_command(out,command,*,cwd=ROOT,env=None,pytest=False,legacy_outputs=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    assert not git('status','--porcelain'),'Phases require a clean committed tree'
    commit,tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}')
    environment=child_environment() if env is None else env.copy()
    if pytest:environment['PYTEST_ADDOPTS']='--junitxml='+str(out/'results.xml')
    environment['P5_RESULTS_DIR']=str(out/'observations')
    validation_roots=[ROOT/'docs'/p/'validation' for p in ('p1','p2','p3','p4')]
    original={p:p.read_bytes() for r in validation_roots if r.exists() for p in r.rglob('*') if p.is_file()}
    tracked=git('ls-files').splitlines()
    inputs={p:sha((ROOT/p).read_bytes()) for p in tracked if ROOT/p not in original}
    if legacy_outputs:
        for group in ('f-fixture','x-fixture','w-fixture','golden','generator','p0-semantic'):
            path=ROOT/'docs/p4/validation'/(group+'-results.json');path.write_text('{}\n')
    started=monotonic();meta=dict(command=command,shell_command=shlex.join(command),cwd=str(cwd),
        tested_commit=commit,tested_tree=tree,python=sys.version,executable=sys.executable,
        platform=platform.platform(),started_at_moscow=datetime.now(ZoneInfo('Europe/Moscow')).isoformat(),
        packages={n:importlib.metadata.version(n) for n in ('pytest','jsonschema','referencing','rfc8785','openpyxl','streamlit')},
        environment={k:environment.get(k) for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE','PYTEST_ADDOPTS','P5_RESULTS_DIR','P5_HISTORICAL_JUNIT')},
        input_sha256=inputs)
    run=None
    try:
        with (out/'stdout.txt').open('wb') as stdout,(out/'stderr.txt').open('wb') as stderr:
            run=subprocess.run(command,cwd=cwd,env=environment,stdout=stdout,stderr=stderr)
    finally:
        generated={}
        for r in validation_roots:
            if not r.exists():continue
            for p in r.rglob('*'):
                if not p.is_file():continue
                raw=p.read_bytes()
                if p not in original or raw!=original[p] or legacy_outputs and p.name.endswith('-results.json'):
                    target=out/'generated'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
                    generated[str(p.relative_to(ROOT))]=sha(raw)
                if p not in original:p.unlink()
        for p,raw in original.items():p.write_bytes(raw)
        nested_command=out/'generated/docs/p4/validation/T63-p0-p3-regression.command.json'
        if nested_command.is_file():
            argv=json.loads(nested_command.read_text())['argv']
            nested=next((Path(a.split('=',1)[1]) for a in argv if a.startswith('--junitxml=')),None)
            if nested is not None and nested.is_file():
                (out/'nested-P0-P3.junit.xml').write_bytes(nested.read_bytes())
        meta.update(exit_code=None if run is None else run.returncode,elapsed_seconds=monotonic()-started,
                    finished_at_moscow=datetime.now(ZoneInfo('Europe/Moscow')).isoformat(),generated=generated,
                    historical_evidence_restored=all(p.read_bytes()==raw for p,raw in original.items()),
                    inputs_unchanged=all(sha((ROOT/p).read_bytes())==h for p,h in inputs.items()),
                    commit_unchanged=git('rev-parse','HEAD')==commit and git('rev-parse','HEAD^{tree}')==tree,
                    final_git_status=git('status','--porcelain'))
        if pytest and (out/'results.xml').is_file():meta['testcases']=junit(out/'results.xml')
        (out/'command.json').write_text(json.dumps(meta,indent=2)+'\n')
        (out/'exit-code.txt').write_text(str(meta['exit_code'])+'\n')
        assert meta['historical_evidence_restored'] and meta['inputs_unchanged'] and meta['commit_unchanged'] and not meta['final_git_status'],meta
    print(json.dumps({'phase':out.name,'exit_code':run.returncode,'seconds':meta['elapsed_seconds']}),flush=True)
    return meta


def legacy_id(case):
    phase=re.search(r'(?:^|\.)p([1-4])(?:\.|$)',case['classname'])
    number=re.search(r'^test_T(\d+)_',case['name'])
    assert phase and number,case
    return f'P{phase[1]}-T{int(number[1]):02}'


def validate_inventory(cases):
    expected={f'P{p}-T{i:02}' for p,n in ((1,42),(2,54),(3,52),(4,64)) for i in range(1,n+1)}
    assert len(cases)==212 and {legacy_id(c) for c in cases}==expected


def classify_legacy(meta,out):
    cases=meta['testcases'];validate_inventory(cases)
    known={'P2-T40','P3-T51','P4-T61','P4-T62','P4-T63'}
    records=[]
    for c in cases:
        identity=legacy_id(c);state=c['outcome'];reason=c['assertion'] or ''
        if state=='pass':classification='PASS'
        elif state=='failure' and identity in known:
            if identity=='P4-T63':
                nested=out/'nested-P0-P3.junit.xml'
                checks=junit(nested)
                failures=[n for n in checks if n['outcome']!='pass']
                assert failures and all(legacy_id(n) in {'P2-T40','P3-T51'} and n['outcome']=='failure' for n in failures),failures
                assert len(checks)==148 and all('AssertionError: Unapproved application source/module/migration' in n['assertion'] for n in failures),failures
            else:
                assertion=('AssertionError: Unapproved full application paths' if identity=='P4-T61'
                           else 'AssertionError: Unapproved application source/module/migration')
                assert assertion in reason,c
            classification='EXPECTED_HISTORICAL_SCOPE_CONFLICT'
        else:classification='BLOCKING_BEHAVIORAL_REGRESSION'
        records.append(dict(test_id=identity,pytest_outcome=state,classification=classification,exact_assertion=reason))
    result=dict(total=212,passed=sum(r['classification']=='PASS' for r in records),
                expected_historical_scope_conflicts=sum(r['classification']=='EXPECTED_HISTORICAL_SCOPE_CONFLICT' for r in records),
                blocking_regressions=sum(r['classification']=='BLOCKING_BEHAVIORAL_REGRESSION' for r in records),records=records)
    (out/'PHASE_AWARE_CLASSIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--historical-run',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();assert not out.exists();assert not out.is_relative_to(ROOT)
    out.mkdir(parents=True)
    historical=args.historical_run.resolve();history=json.loads((historical/'command-environment.json').read_text())
    assert history['tested_commit']==BASELINE and history['exit_code']==0
    assert history['old_validation_restored'] and history['inputs_unchanged'] and history['commit_unchanged']
    old_cases=junit(historical/'results.xml');validate_inventory(old_cases);assert all(c['outcome']=='pass' for c in old_cases)
    assert not git('status','--porcelain')
    commit,tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}')
    from .scope_audit import audit
    scope_before=audit(ROOT)
    env=child_environment();env['P5_HISTORICAL_JUNIT']=str(historical/'results.xml')
    collection=record_command(out/'p5-collection',[sys.executable,'-m','pytest','tests/p5','--collect-only','-q'],env=env)
    assert collection['exit_code']==0
    compat=record_command(out/'integrated-legacy',[sys.executable,'-m','pytest','tests/p1','tests/p2','tests/p3','tests/p4','-q'],env=env,pytest=True,legacy_outputs=True)
    classification=classify_legacy(compat,out/'integrated-legacy')
    p5=record_command(out/'p5-runtime',[sys.executable,'-m','pytest','tests/p5','-q'],env=env,pytest=True)
    actual={c['properties'].get('p5_id') for c in p5['testcases']}
    p5_success=p5['exit_code']==0 and len(p5['testcases'])==76 and actual=={f'P5-T{i:02}' for i in range(1,77)} and all(c['outcome']=='pass' for c in p5['testcases'])
    # Extract the unchanged original source packs for independent real-schema
    # checks. Their historical proposal labels are preserved in raw stdout.
    extracts=out/'unpacked-source';extracts.mkdir()
    with zipfile.ZipFile(ROOT/'docs/p5/handoff/P5_Codex_Implementation_Handoff_2026-11-05.zip') as z:z.extractall(extracts)
    handoff=extracts/'P5_Codex_Implementation_Handoff_2026-11-05'
    base_name='P5_Implementation_Design_Pack_v0.2a_candidate';pb_name='P5_Gate_A_PB_Supplement_v0.2b_candidate'
    for name in (base_name,pb_name):
        with zipfile.ZipFile(handoff/'sources'/(name+'.zip')) as z:z.extractall(extracts)
    base,pb=extracts/base_name,extracts/pb_name
    static=[]
    for label,root,command in (
        ('strict-design',base,[sys.executable,'tools/verify_p5_design_pack.py','--p0-root',str(ROOT/'pecs/pilot_slice_v1'),'--require-p0','--mutation-probes']),
        ('amendment-static',base,[sys.executable,'tools/verify_p5_v02_amendments.py','--mutation-probes']),
        ('numeric-static',base,[sys.executable,'tools/verify_p5_v02a_precision.py','--mutation-probes']),
        ('supplement-static',pb,[sys.executable,'tools/verify_gate_a_supplement.py','--base-root',str(base),'--mutations']),
        ('real-p0-schemas',ROOT,[sys.executable,str(ROOT/'docs/p5/validation/implementation-admission-20261106/validate_available_p0.py'),
                               '--p0-root',str(ROOT/'pecs/pilot_slice_v1'),'--out',str(out/'P0_SCHEMA_RESULTS.json'),'--supplement',str(pb)])):
        static.append(record_command(out/label,command,cwd=root,env=env))
    after=audit(ROOT)
    summary=dict(tested_implementation_commit=commit,tested_implementation_tree=tree,
        historical=dict(commit=BASELINE,tree=history['tested_tree'],total=212,pass_count=212),
        integrated_legacy={k:v for k,v in classification.items() if k!='records'},
        p5=dict(total=len(p5['testcases']),passed=sum(c['outcome']=='pass' for c in p5['testcases']),all_76_unique_ids=p5_success),
        static_all_pass=all(m['exit_code']==0 for m in static),scope_before=scope_before,scope_after=after,
        completed_at_moscow=datetime.now(ZoneInfo('Europe/Moscow')).isoformat(),
        gates_closed_by_runner=False,merged=False,P6_started=False)
    success=p5_success and classification['blocking_regressions']==0 and all(m['exit_code']==0 for m in static)
    summary['technical_validation_success']=success
    (out/'VALIDATION_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)
    return 0 if success else 1


if __name__=='__main__':raise SystemExit(main())
