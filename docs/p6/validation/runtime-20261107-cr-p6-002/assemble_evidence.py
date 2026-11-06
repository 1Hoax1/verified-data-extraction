"""Preserve actual CR-P6-002 results; no source edit or manufactured PASS."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import ast
import copy
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path('/workspace/p6-streamlit-e2e')
WORK = Path('/workspace/p6-cr2-work')
RUN = WORK / 'final-01'
I = '245b1ccf5d4212d3f34973e526172f20a4928539'
TREE = '0db696f5e14284849f969310fadf4ee585713045'
AUTH = '66c2b4f97e2b4dbe4e7a01696c89ae5fd0431981'
OLD = 'deddc2799464076227173bd2e4890f552ffe64bf'
PREFIX = 'docs/p6/validation/runtime-20261107-cr-p6-002/'
OUT = ROOT / PREFIX
DOCKER = WORK / 'docker-smoke/implementation-245b1ccf5d42-20261107'


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, data):
    target = OUT / path; target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def main():
    assert not OUT.exists() and not git('status', '--porcelain').strip()
    assert git('rev-parse', 'HEAD').decode().strip() == I
    assert git('rev-parse', 'HEAD^{tree}').decode().strip() == TREE
    assert git('rev-list', '--parents', '-n', '1', I).decode().split() == [I, AUTH]
    s = read(RUN / 'VALIDATION_SUMMARY.json')
    assert s['tested_commit'] == I and s['tested_tree'] == TREE
    assert s['scope_before']['result'] == s['scope_after']['result'] == 'PASS'
    for phase in ('p6-collection', 'legacy-p1-p4', 'legacy-p5', 'p6-runtime'):
        m = read(RUN / phase / 'command.json')
        assert m['tested_commit'] == I and m['tested_tree'] == TREE
        assert m['inputs_unchanged'] and m['commit_unchanged'] and m['historical_evidence_restored'] and not m['final_git_status']
    OUT.mkdir(parents=True)
    shutil.copytree(RUN, OUT / 'final-run')
    for name in ('original-reproduction', 'dev-focused-01', 'dev-focused-02', 'p0-final-01'):
        shutil.copytree(WORK / name, OUT / name)
    for p in WORK.iterdir():
        if p.is_file() and p.name != 'LATEST_PROGRESS.json' and (p.name.endswith(('.json', '.stdout', '.stderr', '.diff')) or p.name.startswith('final-01.runner.')):
            shutil.copyfile(p, OUT / p.name)
    for name in ('assemble_evidence.py', 'publish_and_verify.py', 'make_review_archive.py'):
        shutil.copyfile(WORK / name, OUT / name)
    d = read(DOCKER / 'diagnostic-summary.json')
    assert d['status'] == 'LINUX_DOCKER_PASSED' and d['source_commit'] == I
    assert (DOCKER / 'source-commit.stdout.txt').read_text().splitlines() == [I, TREE]
    assert not (DOCKER / 'source-status.stdout.txt').read_text().strip()
    shutil.copytree(DOCKER, OUT / 'linux-docker', ignore=shutil.ignore_patterns('workspace'))
    for name in ('run.py', 'driver.py', 'runner.stdout.txt', 'runner.stderr.txt', 'runner.command.json'):
        shutil.copyfile(WORK / 'docker-smoke' / name, OUT / 'linux-docker' / name)

    retired = []
    for p in ('tests/p6/scope_policy_v1.json', 'tests/p6/scope_audit.py', 'tests/p6/run_validation.py', 'tests/p6/test_acceptance.py'):
        raw = git('show', OLD + ':' + p)
        target = OUT / 'retired-v1' / p; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        retired.append(dict(path=p, commit=OLD, blob=git('rev-parse', OLD + ':' + p).decode().strip(), sha256=sha(raw), active=False))
    save('RETIRED_V1_PROVENANCE.json', dict(active_format='P6_SCOPE_POLICY_V2_CR_P6_002', historical_only=retired))

    old_qa = git('show', AUTH+':src/vde/p5/qa.py'); new_qa = (ROOT/'src/vde/p5/qa.py').read_bytes()
    before_ast, after_ast = ast.parse(old_qa), ast.parse(new_qa)
    before_function = next(n for n in before_ast.body if isinstance(n,ast.FunctionDef) and n.name=='criterion_result')
    after_function = next(n for n in after_ast.body if isinstance(n,ast.FunctionDef) and n.name=='criterion_result')
    before_guard = next(n for n in ast.walk(before_function) if isinstance(n,ast.If) and "context.brief.id == 'brief-pb-v1'" in ast.unparse(n.test))
    after_guard = next(n for n in ast.walk(after_function) if isinstance(n,ast.If) and ast.unparse(n.test)=='_certified_pb_columns(c, facts.projection, context)')
    after_guard.test = copy.deepcopy(before_guard.test)
    assert ast.dump(before_function)==ast.dump(after_function)
    after_ast.body=[n for n in after_ast.body if not (isinstance(n,ast.FunctionDef) and n.name=='_certified_pb_columns') and not (isinstance(n,ast.ImportFrom) and n.module=='copy')]
    for node in after_ast.body:
        if isinstance(node,ast.ImportFrom) and node.module=='vde.contracts':
            assert [a.name for a in node.names]==['content_hash','validate']
            node.names=[a for a in node.names if a.name!='content_hash']
    assert ast.dump(before_ast)==ast.dump(after_ast)
    save('QA_CHANGE_BOUNDARY_VERIFICATION_FINAL.json', dict(result='PASS', tested_commit=I, tested_tree=TREE,
        baseline=AUTH, sha256_before=sha(old_qa), sha256_after=sha(new_qa),
        unchanged_AST_after_reversing_only_guard_helper_imports=True,
        reproducible_verifier='assemble_evidence.py'))

    cases = list(ET.parse(RUN / 'p6-runtime/results.xml').getroot().iter('testcase'))
    ids = []
    for c in cases:
        props = {p.get('name'):p.get('value') for p in c.findall('./properties/property')}
        outcome = next((k for k in ('failure', 'error', 'skipped') if c.find(k) is not None), 'pass')
        ids.append(dict(test_id=props['p6_id'], name=c.get('name'), outcome=outcome,
                        assertion=None if outcome == 'pass' else c.find(outcome).text))
    assert len(ids) == 20 and {r['test_id'] for r in ids} == {f'P6-T{i:02}' for i in range(1,21)}
    assert all(r['outcome'] == 'pass' for r in ids if r['test_id'] != 'P6-T19')
    assert next(r for r in ids if r['test_id'] == 'P6-T19')['outcome'] == 'failure'
    save('P6_ACTUAL_TEST_ID_INVENTORY.json', dict(tested_commit=I, tested_tree=TREE, records=ids))
    legacy = read(RUN / 'legacy-p1-p4/PHASE_AWARE_CLASSIFICATION.json')
    p5 = read(RUN / 'P5_PHASE_AWARE_CLASSIFICATION.json')
    assert len(legacy['records']) == 212 and len(p5) == 76 and s['blocking_behavioral_regressions'] == 0
    save('REGRESSION_ACTUAL_TEST_ID_INVENTORY.json', dict(tested_commit=I, tested_tree=TREE, P1_P4=legacy['records'], P5=p5))

    records = []
    after_tree = {}
    for entry in git('ls-tree', '-rz', '--full-tree', I).split(b'\0'):
        if not entry: continue
        obj, name = entry.decode().split('\t'); mode, kind, blob = obj.split()
        assert kind == 'blob'; after_tree[name] = (mode, blob)
    amended = set(s['scope_after']['authorized_amended_paths'])
    changes = git('diff', '--name-status', AUTH, I).decode().splitlines()
    assert len(changes) == 7 and {r.split('\t')[1] for r in changes} == amended and all(r.startswith('M\t') for r in changes)
    for entry in git('ls-tree', '-rz', '--full-tree', AUTH).split(b'\0'):
        if not entry: continue
        obj, path = entry.decode().split('\t'); mode, kind, blob = obj.split(); assert kind == 'blob'
        before = git('cat-file', 'blob', blob); after = (ROOT / path).read_bytes()
        after_mode, after_blob = after_tree[path]
        assert mode == after_mode and after == git('cat-file', 'blob', after_blob)
        if path not in amended: assert after == before, path
        records.append(dict(path=path, mode_before=mode, mode_after=after_mode, blob_before=blob,
            blob_after=after_blob, sha256_before=sha(before), sha256_after=sha(after),
            classification='AUTHORIZED_CR_P6_002_AMENDMENT' if path in amended else 'UNCHANGED'))
    assert len(records) == 1914
    save('PROTECTED_FILES_BEFORE_AFTER.json', dict(result='PASS', baseline=AUTH, tested_commit=I,
         records=records, files=len(records), unchanged=len(records)-7, authorized_modifications=7))
    (OUT / 'IMPLEMENTATION_CHANGED_FILES.txt').write_text('\n'.join(changes)+'\n')
    (OUT / 'IMPLEMENTATION.diff').write_bytes(git('diff', '--binary', AUTH, I))
    (OUT / 'P5_QA_ONLY.diff').write_bytes(git('diff', AUTH, I, '--', 'src/vde/p5/qa.py'))
    save('GOVERNANCE_UNCHANGED.json', dict(decisions_sha256=sha((ROOT/'DECISIONS.md').read_bytes()),
         governance_pin_sha256=sha((ROOT/'tests/p4/approved_governance_pin_v1.json').read_bytes()),
         repin=False, owner_decision_unchanged=True))
    assert sha((ROOT/'tests/p4/approved_governance_pin_v1.json').read_bytes()) == '95b7c92a417ec06a80f3d4e839e136e00100e4313d1bee021c94f5beda1f0df7'
    assert sha((ROOT/'src/vde/p5/qa.py').read_bytes()) == s['approved_p5_qa_sha256']

    old_manifest = ROOT / 'docs/p6/validation/runtime-20261107/MANIFEST.sha256'
    old_rows = old_manifest.read_text().splitlines()
    for row in old_rows:
        digest, path = row.split('  ',1); assert sha((ROOT/path).read_bytes()) == digest
    save('ORIGINAL_FAILED_EVIDENCE_INTEGRITY.json', dict(result='PASS', manifest_sha256=sha(old_manifest.read_bytes()),
        entries=len(old_rows), actual_reproduction=read(WORK/'original-reproduction/command.json'), historical_evidence_rewritten=False))

    obs = RUN / 'p6-runtime/observations'
    t06, t07, t13, t17, t18 = [read(obs/(n+'.json')) for n in ('T06','T07','T13','T17','T18')]
    guards = t06['CR_P6_002_guards']; negatives = guards['negatives']
    assert len(negatives) >= 34 and all(c['outcome']=='REJECTED' and c['qa_status']=='FAIL' for c in negatives)
    assert t06['observed_order_status']=='READY' and t06['observed_qa_status']=='PASS_WITH_WARNINGS'
    assert t06['canonical_pb']['report']['overall_status']=='PASS_WITH_WARNINGS' and t07['data_cells']==18
    assert len(t13['CR_P6_002_PB_real_context_denials']) == 12
    probes = t18['negative_probes']; assert len(probes)==30 and all(c['result']=='REJECTED' for c in probes)
    save('PB_CORRECTION_POSITIVE_NEGATIVE_RESULTS.json', dict(tested_commit=I, tested_tree=TREE,
        actual_uuid_pb=t06, actual_downloads=t07, actual_context_denials=t13['CR_P6_002_PB_real_context_denials'],
        approval_boundary='Pure recognition copies and isolated automated test actions are not owner/business authority.'))
    stress = {}
    for label in ('CSV', 'XLSX', 'negative-expanded-text'):
        raw=read(RUN/'legacy-p5/observations'/('stress-'+label+'.json'));assert raw['exit_code']==0
        outcome=json.loads(raw['stdout']);assert outcome['result']=='PASS'
        if label != 'negative-expanded-text':
            assert outcome['tested_commit']==I and outcome['tested_tree']==TREE and outcome['independent_cells_checked']==20000000
        stress[label]=outcome
    save('STRESS_TEST_RESULTS.json', dict(tested_commit=I,tested_tree=TREE,outcomes=stress,P6_download=t17))
    save('ENVIRONMENT_PACKAGES.json', dict(python=sys.version, executable=sys.executable,
        packages=sorted([dict(name=d.metadata['Name'],version=d.version) for d in importlib.metadata.distributions()],key=lambda d:d['name'].lower())))
    readme=(ROOT/'docs/p6/README_PILOT.md').read_text()
    mac=readme.split('### Required actual Mac P6-T19 record\n',1)[1].split('\n## Explicit operator workflow',1)[0]
    mac_readback = r'''

## Concrete read-only checks of the Mac-saved P-B downloads

These are instructions, **NOT RUN on a Mac here**. Run them on the actual Mac
after the manual browser workflow, while its README container is running.
Select actual saved filenames in a private evidence directory outside the
workspace. The commands only read downloaded bytes and the frozen golden; they
never approve, execute, repair or update SQLite. Keep stdout/stderr and exits.

```bash
export VDE_SAVED_XLSX=/absolute/private/evidence/orders_clean.xlsx
export VDE_SAVED_QA=/absolute/private/evidence/qa_report_actual_id.json
shasum -a 256 "$VDE_SAVED_XLSX" "$VDE_SAVED_QA"
cat "$VDE_SAVED_XLSX" | docker exec -i vde-pilot /tmp/vde-venv/bin/python -c '
import hashlib, io, sys
from openpyxl import load_workbook
raw = sys.stdin.buffer.read()
actual = load_workbook(io.BytesIO(raw), read_only=True, data_only=False, keep_links=False)
golden = load_workbook("/tmp/code/pecs/pilot_slice_v1/fixtures/P-B_xlsx_sheet/expected_result.xlsx", read_only=True, data_only=False, keep_links=False)
try:
    assert actual.sheetnames == ["Data"]
    rows = list(actual["Data"].rows)
    assert len(rows) == 4 and all(len(row) == 6 for row in rows)
    assert all(cell.data_type != "f" for row in rows for cell in row)
    assert [[cell.value for cell in row] for row in rows] == [[cell.value for cell in row] for row in golden.active.rows]
    print("18 values and six headers PASS", len(raw), hashlib.sha256(raw).hexdigest())
finally:
    actual.close()
    golden.close()
'
cat "$VDE_SAVED_QA" | docker exec -i vde-pilot /tmp/vde-venv/bin/python -c '
import json, sys
from vde.contracts import validate
report = json.load(sys.stdin)
validate(report, "qa_report")
assert report["overall_status"] == "PASS_WITH_WARNINGS" and not report["blocking_issues"]
assert report["dataset_summary"]["row_count"] == 3 and report["dataset_summary"]["column_count"] == 6
checks = report["deterministic_checks"]
assert len(checks) == 24 and not any(c["status"] == "FAIL" for c in checks)
assert {c["criterion_id"]: c["status"] for c in checks if c["check_id"] == "DQ-017"} == {"PB-AC-006": "PASS", "PB-AC-007": "PASS"}
assert report["warnings"] and len(report["artifacts"]) == 1
print(json.dumps({k: report[k] for k in ("report_id", "run_id", "brief_version_id", "transformation_spec_version_id", "dataset_summary", "artifacts", "warnings")}, ensure_ascii=False, indent=2))
'
```

Compare the XLSX SHA-256/length printed by the first command to the Artifact and
dataset summary from the QA and the UI. Match the actual Run/version/report IDs
to the two independently approved business versions and persisted context.
Retain original browser response metadata, explicit operator action record and
before/after restart proof; these readback commands alone do not complete T19.
Do not fabricate successful fields in the Mac evidence JSON. Gate B and release
still require separate owner decisions.
'''
    (OUT/'MACOS_DOCKER_T19_HANDOFF.md').write_text('# Actual macOS Docker P6-T19 — NOT RUN / BLOCKED\n\nTest exact implementation `'+I+'`, tree `'+TREE+'`.\n\n'+mac+mac_readback)
    p0=read(OUT/'p0-final-01/P0_SCHEMA_RESULTS.json')
    table='\n'.join('| '+r['test_id']+' | '+r['outcome'].upper()+' |' for r in ids)
    report=f'''# CR-P6-002 — corrected P6 validation

Recorded: {datetime.now(ZoneInfo('Europe/Moscow')).isoformat()}.

**Status: CR-P6-002 correction technically verified on Linux; P6 BLOCKED by actual Mac Docker T19 NOT RUN. No Gate B closure, merge, governance repin, Pilot release or next stage is asserted.**

## Authority and exact tested source

Owner-approved start: `{AUTH}`. Main remains the separately verified frozen baseline `0af4a1ff49ccf8fa59c39780d749e15cb5042fc3`. Branch: `feature/p6-streamlit-e2e`.

**Tested implementation: `{I}`. Tree: `{TREE}`.** Its only parent is the owner-authority commit. Exactly seven existing files are modified; `IMPLEMENTATION_CHANGED_FILES.txt` and `IMPLEMENTATION.diff` provide the complete inventory and bytes. A later evidence-only commit has identical source/tests and separate publication verification; no full runtime rerun on that descendant is claimed.

The owner decision was read fully and independently fetched from GitHub before source edits. Its exact blob, SHA-256 and ancestry remain pinned. This project authority is separate from the two actual business-version Approvals required by unchanged P5 admission. No live owner workspace or Approval was changed.

## Fix and exact boundaries

Only P5 `qa.py`'s PB-AC-002 recognition guard changes, with a private pure helper and its required imports. `QA_CHANGE_BOUNDARY_VERIFICATION_FINAL.json` proves the entire prior AST is identical after reversing precisely those changes. Generic `predicate`, every other QA function, admission, transformations, stored identities/hashes/history and source bytes remain unchanged.

All guards are conjunctive: admitted real Order/source/Brief/Spec/Approval/Run; exactly one matching LOCAL_XLSX/Orders input; source SHA-256 `d275fa7393e73ef1be7815e83b31b1a710b3f345bb7138c72569b03f66edf80d`; exact approved XLSX output; PB-AC-002/COLUMNS/sequence_equals with the same five target/expected columns and exact six output columns. A separate deep copy substitutes solely its verified input asset binding to asset-pb-xlsx for frozen P0 semantic hash comparison with `9b7c2b0111360714dfbc9cbdbc755b693b11e067f32771cb226126fdcd1ffb49`. The original document/hash is never changed or replaced as authority.

Corrected QA file SHA-256: `{s['approved_p5_qa_sha256']}`. Active audit version is `{s['scope_policy_format']}` in the historical filename scope_policy_v1.json. Original baselines are unchanged; correction authority is separately named. Exact hash protection covers only this single P5 edit. V1 policy/audit/runner remain at `{OLD}` and are copied under retired-v1 with immutable Git blob/SHA provenance, clearly inactive. No broad P5 waiver or latest-main trust exists.

## Actual results on the corrected tree

| Suite | Actual outcome |
|---|---|
| P6-T01…T20 | {s['p6']['passed']} PASS / {s['p6']['failed']} FAIL / {s['p6']['errors']} ERROR / {s['p6']['skipped']} SKIP; raw exit {s['p6']['pytest_exit']} |
| Unchanged P1–P4 | {legacy['passed']} PASS / {legacy['expected_historical_scope_conflicts']} actual historical scope FAIL; {legacy['blocking_regressions']} behavioral regressions |
| Unchanged P5 | {s['legacy_p5']['passed']} PASS / {s['legacy_p5']['scope_conflicts']} actual historical scope FAIL; {s['legacy_p5']['blocking_regressions']} behavioral regressions |
| New successor audit | PASS; {len(probes)}/{len(probes)} negative mutations rejected |
| P0 | {p0['schemas_checked']} schemas / {p0['positive_validations']} positive schema applications PASS; {p0['manifest_present_matches']}/{p0['manifest_declared_count']} original files present+matching |

| P6 ID | Actual outcome |
|---|---|
{table}

The only corrected-tree P6 failure is T19: native Linux launch/restart passed, but actual Mac-host Docker execution is NOT RUN. It remains a real FAIL, never skip/xfail or Linux substitution. The historical eight scope failures remain FAIL with exact assertion and child-JUnit proof. Historical 212/212 and 76/76 PASS remain tied solely to `fd39aa1bed480313504ae8b1f76e77e170cb72ba` and `801cc2ba5db46494eaa93e5b963c3bc2f936ddc2`, respectively. No combined all-green result is claimed.

Both original certified P-B and fresh UUID UI P-B actually reach READY/PASS_WITH_WARNINGS, one RESULT_XLSX, 3×6/18 exact values, no formulas, 24 checks, source warnings and separate DQ-017/PB-AC-006/007 PASS. Actual HTTP XLSX/QA checks verify bodies, SHA-256, sizes, MIME, names and exact report linkage. The original-identity scenario uses the approved isolated P1/P3/P4 procedure; its explicit simulated API test actions are not live owner Approvals. The UUID scenario retains the original two separate explicit UI test actions. Generic five-versus-six remains FAIL.

Recognition-only controls reject {len(negatives)} semantic/input/output mutations; an additional original-ID/wrong-source control fails. Twelve real persisted-context negatives reject invalid source/Spec/Run/Approvals on disposable copies. The existing SQLite CHECK prevents a forged approver before persistence; it was not disabled. P-A exact 277-byte golden and P-D authoritative NEEDS_FIX/FAIL diagnostic remain covered, with restart, corruption, ownership, idempotency and no unauthorized business writes.

## Resources and platform

Both actual 100000×200 P5 exports reread all 20000000 values independently. CSV: PASS, P5 elapsed {stress['CSV']['P5_elapsed_seconds']} seconds, incremental peak RSS {stress['CSV']['incremental_peak_rss_bytes']} bytes. XLSX: PASS, P5 elapsed {stress['XLSX']['P5_elapsed_seconds']} seconds, incremental peak RSS {stress['XLSX']['incremental_peak_rss_bytes']} bytes. Expanded-text negative: {stress['negative-expanded-text']['P4_internal_bytes']} internal bytes, safe EXPORT_FAILED, zero new final Artifacts/QAReports and unchanged P4 bytes. This rejection is not a positive-workload substitute.

P6 actual verified download: {t17['actual_result_bytes']} bytes, incremental peak RSS {t17['P6_resources']['incremental_peak_rss']} bytes against 536870912. Conservative admission and sampled memory remain unchanged. Actual injected allocation failure revokes the newly registered URL (HTTP 404), exposes no new widget/snapshot and changes no business rows. Frozen Streamlit private compatibility and preverified-snapshot last-click limitations remain explicit.

Linux native and clean Linux-host Docker smoke actually pass on this exact source: unchanged frozen-lock install, health 200, P-A Result/QA HTTP, container removal/recreation on the same mount, exact row/payload persistence and fresh-session reprepare. Actual Mac Docker is NOT RUN. `MACOS_DOCKER_T19_HANDOFF.md` gives the exact source SHA/tree, real host/container requirements, explicit human workflow, readback/hash/restart evidence and separate T19 rerun procedure. No success receipt is fabricated.

## Preservation and evidence

All {len(records)} owner-start files were independently compared by bytes/blob/mode: {len(records)-7} unchanged; seven explicitly authorized modifications. P6 runtime, app integration, conftest, P0–P4/P5 historical tests/contracts/fixtures/schema/migrations/dependencies/governance and original FAILED evidence remain unchanged. Available P0 passes do not imply full positive coverage of the 13 absent P-C originals; no replacement fixture exists.

Original T06/T07 were actually rerun on frozen `{OLD}` / tree afc4126ccddce4ca4615ac411b1dd6281a98a960, giving two real FAIL and exit 1. That reproduction and original manifest integrity are preserved separately. Uncommitted dev-focused-01 recorded two passes and a new test-harness failure when SQLite correctly rejected an impossible approver mutation; dev-focused-02 correctly asserted that denial and passed all three selected tests. Neither diagnostic is substituted for final exact-tree outcomes.

Complete commands, timestamps, versions, exits, stdout/stderr, JUnit, unique ID inventories, guards, resources, protected-file hashes, source diff, Mac handoff and finite SHA-256 manifest are included. Temporary output writes from historical tests were captured and restored exactly by the unchanged recorder. The later evidence-only commit/published HEAD is separately identified; its full runtime suite was not rerun.

**Handoff: BLOCKED pending actual Mac-host P6-T19 and separate owner review. CR-P6-002 recognition correction passes its executed Linux obligations; no P6 VALIDATED, Gate B closure, merge or Pilot release is claimed.**
'''
    (OUT/'P6_CR_P6_002_VALIDATION_REPORT.md').write_text(report)
    files=sorted(p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file())
    inventory=PREFIX+'EVIDENCE_FILES.txt';manifest=PREFIX+'MANIFEST.sha256'
    files=sorted(set(files+[inventory,manifest]))
    (ROOT/inventory).write_text(''.join(p+'\n' for p in files))
    (ROOT/manifest).write_text(''.join(sha((ROOT/p).read_bytes())+'  '+p+'\n' for p in files if p!=manifest))
    print(json.dumps(dict(status='BLOCKED',files=len(files),manifest_entries=len(files)-1,manifest_sha256=sha((ROOT/manifest).read_bytes()),tested_commit=I),indent=2))


if __name__=='__main__': main()
