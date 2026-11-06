"""Exact-tree P6 validation; legacy pytest failures remain failures in raw evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

from p5.run_validation import record_command
from .scope_audit import audit, BASELINE, START

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()



def classify_legacy(meta, out):
    """Keep actual failures and prove only the owner-approved P6 scope effects."""
    from p5.run_validation import junit, legacy_id, validate_inventory
    cases = meta['testcases']; validate_inventory(cases)
    known = {'P2-T01', 'P2-T40', 'P3-T50', 'P3-T51', 'P4-T61', 'P4-T62', 'P4-T63'}

    def direct(case):
        identity = legacy_id(case); reason = case['assertion'] or ''
        if case['outcome'] != 'failure':
            return False
        if identity == 'P2-T01':
            return ("assert all('create' not in b.label.lower() for b in app.button)" in reason
                    and 'assert False' in reason and 'test_T01_existing_order_ui' in reason)
        phrase = ('AssertionError: Unapproved full application paths' if identity == 'P4-T61'
                  else 'AssertionError: Unapproved application source/module/migration')
        return identity in {'P2-T40', 'P3-T51', 'P4-T61', 'P4-T62'} and phrase in reason

    child_p2 = out / 'generated/docs/p3/validation/p2-results.xml'
    nested = junit(child_p2) if child_p2.is_file() else []
    bad_p2 = [c for c in nested if c['outcome'] != 'pass']
    p2_proven = (len(nested) == 54 and {legacy_id(c) for c in bad_p2} == {'P2-T01', 'P2-T40'}
                 and all(direct(c) for c in bad_p2))

    def p3_cascade(case):
        reason = case['assertion'] or ''
        return (case['outcome'] == 'failure' and p2_proven and 'assert 1 == 0' in reason
                and 'test_T01_existing_order_ui' in reason and 'test_T40_scope_dependencies' in reason)

    child_p0_p3 = out / 'nested-P0-P3.junit.xml'
    nested_all = junit(child_p0_p3) if child_p0_p3.is_file() else []
    bad_all = [c for c in nested_all if c['outcome'] != 'pass']
    p0_p3_proven = (len(nested_all) == 148 and {legacy_id(c) for c in bad_all} ==
                   {'P2-T01', 'P2-T40', 'P3-T50', 'P3-T51'} and all(
                       p3_cascade(c) if legacy_id(c) == 'P3-T50' else direct(c) for c in bad_all))
    records = []
    for case in cases:
        identity = legacy_id(case); outcome = case['outcome']; proven = direct(case)
        if identity == 'P3-T50':
            proven = p3_cascade(case)
        elif identity == 'P4-T63':
            proven = outcome == 'failure' and p0_p3_proven and 'assert 1 == 0' in (case['assertion'] or '')
        category = ('PASS' if outcome == 'pass' else 'EXPECTED_HISTORICAL_SCOPE_CONFLICT'
                    if identity in known and proven else 'BLOCKING_BEHAVIORAL_REGRESSION')
        records.append(dict(test_id=identity, pytest_outcome=outcome, classification=category,
                            exact_assertion=case['assertion']))
    result = dict(total=len(cases), passed=sum(c['classification'] == 'PASS' for c in records),
        expected_historical_scope_conflicts=sum(c['classification'] == 'EXPECTED_HISTORICAL_SCOPE_CONFLICT' for c in records),
        blocking_regressions=sum(c['classification'] == 'BLOCKING_BEHAVIORAL_REGRESSION' for c in records),
        nested_p2_scope_proven=p2_proven, nested_p0_p3_scope_proven=p0_p3_proven, records=records)
    (out / 'PHASE_AWARE_CLASSIFICATION.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--stress-workspace', type=Path, required=True)
    p.add_argument('--linux-smoke', type=Path); p.add_argument('--mac-smoke', type=Path)
    args = p.parse_args(); out = args.out.resolve()
    assert not out.exists() and not out.is_relative_to(ROOT)
    assert not git('status', '--porcelain'), 'Run on a clean committed implementation'
    out.mkdir(parents=True)
    commit, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    before = audit(ROOT)
    env = os.environ.copy(); env.update(PYTHONPATH=str(ROOT/'src')+os.pathsep+str(ROOT/'tests'),
        PYTHONDONTWRITEBYTECODE='1', P6_STRESS_WORKSPACE=str(args.stress_workspace.resolve()),
        P6_VALIDATION_DIR=str(out))
    if args.linux_smoke: env['P6_LINUX_SMOKE']=str(args.linux_smoke.resolve())
    if args.mac_smoke: env['P6_MAC_DOCKER_EVIDENCE']=str(args.mac_smoke.resolve())
    inputs=dict(command=sys.argv, cwd=str(ROOT), tested_commit=commit, tested_tree=tree,
                P6_STRESS_WORKSPACE=env['P6_STRESS_WORKSPACE'], P6_VALIDATION_DIR=env['P6_VALIDATION_DIR'],
                P6_RESULTS_DIR=str(out/'p6-runtime/observations'), external_platform_evidence={})
    stress_db=args.stress_workspace.resolve()/'app.sqlite3'
    inputs['stress_database_sha256']=hashlib.sha256(stress_db.read_bytes()).hexdigest()
    for label,path in (('linux_smoke',args.linux_smoke),('mac_smoke',args.mac_smoke)):
        inputs['external_platform_evidence'][label]=None if path is None else dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (out/'VALIDATION_INPUTS.json').write_text(json.dumps(inputs,indent=2)+'\n')
    history = ROOT/'docs/p5/validation/runtime-20261106'
    historical = {}
    for label, path, expected in (
        ('P1_P4', history/'historical-212/results.xml', 212),
        ('P5', history/'final-run/p5-runtime/results.xml', 76)):
        cases = list(ET.parse(path).getroot().iter('testcase'))
        assert len(cases)==expected and all(not any(c.find(t) is not None for t in ('failure','error','skipped')) for c in cases)
        historical[label]=dict(path=path.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                               passed=expected, result='PASS_ON_HISTORICAL_TREE_ONLY')
    historical['P1_P4']['commit']='fd39aa1bed480313504ae8b1f76e77e170cb72ba'
    historical['P5']['commit']='801cc2ba5db46494eaa93e5b963c3bc2f936ddc2'
    env['P5_HISTORICAL_JUNIT']=str(history/'historical-212/results.xml')
    collection = record_command(out/'p6-collection',[sys.executable,'-m','pytest','tests/p6','--collect-only','-q'],env=env)
    assert collection['exit_code']==0
    legacy = record_command(out/'legacy-p1-p4',[sys.executable,'-m','pytest','tests/p1','tests/p2','tests/p3','tests/p4','-q'],env=env,pytest=True,legacy_outputs=True)
    legacy_class = classify_legacy(legacy,out/'legacy-p1-p4')
    p5 = record_command(out/'legacy-p5',[sys.executable,'-m','pytest','tests/p5','-q'],env=env,pytest=True)
    p5_records=[]
    for case in p5.get('testcases',[]):
        ident=case['properties'].get('p5_id')
        if case['outcome']=='pass': category='PASS'
        elif (ident=='P5-T76' and case['outcome']=='failure' and
              'Protected file changed: src/vde/app.py' in (case['assertion'] or '')):
            category='EXPECTED_HISTORICAL_SCOPE_CONFLICT'
        else: category='BLOCKING_BEHAVIORAL_REGRESSION'
        p5_records.append(dict(test_id=ident,pytest_outcome=case['outcome'],classification=category,exact_assertion=case['assertion']))
    assert len(p5_records)==76 and {r['test_id'] for r in p5_records}=={f'P5-T{i:02}' for i in range(1,77)}
    (out/'P5_PHASE_AWARE_CLASSIFICATION.json').write_text(json.dumps(p5_records,indent=2)+'\n')
    # P6 conftest supports its own observations directory as well as the parent
    # recorder's P5_RESULTS_DIR. No old test or report is edited.
    p6_env=env.copy(); p6_env['P6_RESULTS_DIR']=str(out/'p6-runtime/observations')
    p6=record_command(out/'p6-runtime',[sys.executable,'-m','pytest','tests/p6','-q'],env=p6_env,pytest=True)
    cases=p6.get('testcases',[])
    import re
    ids=[]
    for case in cases:
        match=re.search(r'^test_T(\d+)_',case['name']);assert match,case['name']
        identity='P6-T'+match[1].zfill(2)
        assert case['properties'].get('p6_id')==identity,'JUnit name/property identity mismatch'
        ids.append(identity)
    assert len(ids)==20 and set(ids)=={f'P6-T{i:02}' for i in range(1,21)},ids
    (out/'P6_TEST_ID_INVENTORY.json').write_text(json.dumps([dict(test_id=i,pytest_outcome=c['outcome'],assertion=c['assertion']) for i,c in zip(ids,cases)],indent=2)+'\n')
    after=audit(ROOT)
    invalid_exits=[]
    for label,phase in (('P1-P4',legacy),('P5',p5)):
        expected_exit=1 if any(c['outcome'] in ('failure','error') for c in phase['testcases']) else 0
        if phase['exit_code']!=expected_exit:invalid_exits.append(dict(phase=label,actual=phase['exit_code'],expected=expected_exit))
    blockers=legacy_class['blocking_regressions']+sum(r['classification']=='BLOCKING_BEHAVIORAL_REGRESSION' for r in p5_records)+len(invalid_exits)
    result=dict(tested_commit=commit,tested_tree=tree,approved_start=START,main_baseline=BASELINE,
        platform=platform.platform(),python=sys.version,historical=historical,
        legacy_p1_p4={k:v for k,v in legacy_class.items() if k!='records'},
        legacy_p5=dict(total=76,passed=sum(r['classification']=='PASS' for r in p5_records),
            scope_conflicts=sum(r['classification']=='EXPECTED_HISTORICAL_SCOPE_CONFLICT' for r in p5_records),
            blocking_regressions=sum(r['classification']=='BLOCKING_BEHAVIORAL_REGRESSION' for r in p5_records),pytest_exit=p5['exit_code']),
        p6=dict(total=20,passed=sum(c['outcome']=='pass' for c in cases),failed=sum(c['outcome']=='failure' for c in cases),
                errors=sum(c['outcome']=='error' for c in cases),skipped=sum(c['outcome']=='skipped' for c in cases),pytest_exit=p6['exit_code']),
        scope_before=before,scope_after=after,blocking_behavioral_regressions=blockers,unexpected_pytest_exits=invalid_exits,
        mac_docker_smoke='EVIDENCE_PROVIDED' if args.mac_smoke else 'NOT RUN: no macOS host provided',
        status='READY FOR P6 GATE B REVIEW' if p6['exit_code']==0 and blockers==0 and args.mac_smoke else 'BLOCKED',
        gate_b='NOT CLOSED',merged=False,pilot_release='NOT AUTHORIZED',completed_at_utc=datetime.now(timezone.utc).isoformat())
    (out/'VALIDATION_SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
    return 0 if result['status']=='READY FOR P6 GATE B REVIEW' else 1


if __name__=='__main__':
    raise SystemExit(main())
