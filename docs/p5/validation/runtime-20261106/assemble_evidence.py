"""Assemble observed final evidence only; refuse incomplete/failed validation."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import base64
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

REPO=Path('/workspace/p5-export-deterministic-qa')
WORK=Path('/workspace/p5-resume-work')
RUN=WORK/'final-03'
HISTORY=WORK/'historical-runs/full-01'
BASE='820245fc544fc66c393db548151e6d281e03d414'
EV=REPO/'docs/p5/validation/runtime-20261106'


def git(*args):return subprocess.check_output(['git',*args],cwd=REPO)
def textgit(*args):return git(*args).decode().strip()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def save(name,data):
 p=EV/name;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def main():
 assert not textgit('status','--porcelain')
 summary=json.loads((RUN/'VALIDATION_SUMMARY.json').read_text())
 assert summary['technical_validation_success'] and summary['p5']['all_76_unique_ids']
 assert summary['tested_implementation_commit']==textgit('rev-parse','HEAD')
 assert summary['tested_implementation_tree']==textgit('rev-parse','HEAD^{tree}')
 assert summary['historical']['total']==summary['historical']['pass_count']==212
 assert summary['integrated_legacy']['total']==212 and summary['integrated_legacy']['blocking_regressions']==0
 assert summary['p5']['total']==summary['p5']['passed']==76
 owner_api=json.loads((WORK/'owner-approval.api.json').read_text())
 assert owner_api['path']=='docs/p5/decisions/CR-P5-003_OWNER_APPROVAL_2026-11-06.md'
 owner_raw=base64.b64decode(owner_api['content'])
 assert owner_raw==(WORK/'OWNER_APPROVAL.md').read_bytes()==git('show',BASE+':'+owner_api['path'])
 assert owner_api['sha']==textgit('rev-parse',BASE+':'+owner_api['path'])
 assert not EV.exists()
 EV.mkdir(parents=True)
 shutil.copytree(RUN,EV/'final-run',ignore=shutil.ignore_patterns('unpacked-source'))
 shutil.copytree(HISTORY,EV/'historical-212')
 # Preserve the committed first candidate's actual outcomes and failed outer
 # classification separately; never present it as completed final validation.
 shutil.copytree(WORK/'final-01',EV/'earlier-candidate-e332519',ignore=shutil.ignore_patterns('unpacked-source'))
 shutil.copytree(WORK/'final-02',EV/'earlier-candidate-8a8b8ac',ignore=shutil.ignore_patterns('unpacked-source'))
 for name in ('final-01.runner.stdout.txt','final-01.runner.stderr.txt','final-02.runner.stdout.txt','final-02.runner.stderr.txt','final-03.runner.stdout.txt','final-03.runner.stderr.txt'):
  shutil.copyfile(WORK/name,EV/name)
 dev=EV/'development-diagnostics';dev.mkdir()
 for n in range(1,7):
  for extension in ('xml','stdout.txt','stderr.txt'):
   source=WORK/(f'dev-{n:02}.'+extension)
   if source.is_file():shutil.copyfile(source,dev/source.name)
 for source in WORK.glob('preflight-committed.*'):
  if source.is_file():shutil.copyfile(source,dev/source.name)
 for source in WORK.glob('negative-setup-check.*.txt'):
  if source.is_file():shutil.copyfile(source,dev/source.name)
 shutil.copyfile(WORK/'historical_recorder.py',EV/'historical_recorder.py')
 shutil.copyfile(WORK/'assemble_evidence.py',EV/'assemble_evidence.py')
 shutil.copyfile(WORK/'publish_and_verify.py',EV/'publish_and_verify.py')
 shutil.copyfile(WORK/'make_review_archive.py',EV/'make_review_archive.py')
 shutil.copyfile(WORK/'check_source_archive.py',EV/'check_source_archive.py')
 for name in ('source-archive.stdout.json','source-archive.stderr.txt','source-archive.command.json','final-03.runner.invocation.json'):
  shutil.copyfile(WORK/name,EV/name)
 shutil.copyfile(WORK/'OWNER_APPROVAL.md',EV/'OWNER_APPROVAL_READ_FIRST.snapshot.md')
 shutil.copyfile(WORK/'owner-approval.api.json',EV/'OWNER_APPROVAL_READ_FIRST.api.json')
 # Compare every pre-existing file against the immutable owner start. The sole
 # allowed old-file edit is the exact explicitly reviewed two-line app append.
 protected=[]
 for line in git('ls-tree','-r','--full-tree',BASE).decode().splitlines():
  obj,path=line.split('\t');mode,kind,blob=obj.split();assert kind=='blob'
  before=git('cat-file','blob',blob);actual=(REPO/path).read_bytes();expected=before
  if path=='src/vde/app.py':expected+=b'from vde.p5.ui import panel as export_qa_panel\nexport_qa_panel(result)\n'
  assert actual==expected,path
  after_blob=textgit('rev-parse','HEAD:'+path)
  assert git('show','HEAD:'+path)==actual
  assert not ((REPO/path).stat().st_mode & 0o111)
  protected.append(dict(path=path,mode=mode,blob_before=blob,blob_after=after_blob,
      sha256_before=digest(before),sha256_after=digest(actual),
      classification='APPROVED_EXACT_APP_APPEND' if path=='src/vde/app.py' else 'UNCHANGED'))
 save('PROTECTED_FILES_BEFORE_AFTER.json',dict(baseline=BASE,files=len(protected),
      unchanged=sum(r['classification']=='UNCHANGED' for r in protected),approved_app_append=1,result='PASS',records=protected))
 diff=git('diff','--binary',BASE,'HEAD')
 (EV/'IMPLEMENTATION.diff').write_bytes(diff)
 inventory=git('diff','--name-status',BASE,'HEAD').decode().splitlines()
 assert len(inventory)==24 and sum(r.startswith('M\t') for r in inventory)==1
 assert next(r for r in inventory if r.startswith('M\t'))=='M\tsrc/vde/app.py'
 (EV/'IMPLEMENTATION_CHANGED_FILES.txt').write_text('\n'.join(inventory)+'\n')
 save('IMPLEMENTATION_IDENTITIES.json',dict(owner_start=BASE,owner_start_tree=textgit('rev-parse',BASE+'^{tree}'),
      tested_commit=textgit('rev-parse','HEAD'),tested_tree=textgit('rev-parse','HEAD^{tree}'),
      parent=textgit('rev-parse','HEAD^'),branch=textgit('branch','--show-current'),
      commits_since_owner_start=git('log','--format=%H %P %s',BASE+'..HEAD').decode().splitlines(),
      source_diff_sha256=digest(diff)))
 pin_raw=git('show','HEAD:tests/p4/approved_governance_pin_v1.json');pin=json.loads(pin_raw)
 assert digest(pin_raw)=='95b7c92a417ec06a80f3d4e839e136e00100e4313d1bee021c94f5beda1f0df7'
 decisions=git('show','HEAD:DECISIONS.md')
 assert textgit('rev-parse','HEAD:DECISIONS.md')==pin['decisions_blob']
 assert digest(decisions)==pin['decisions_sha256'] and len(decisions)==pin['decisions_size_bytes']
 git('merge-base','--is-ancestor',pin['approval_commit'],'HEAD')
 save('UNCHANGED_G3_GOVERNANCE.json',dict(pin=pin,pin_sha256=digest(pin_raw),
       decisions_blob=textgit('rev-parse','HEAD:DECISIONS.md'),decisions_sha256=digest(decisions),decisions_size=len(decisions),
       repin_performed=False,result='PASS'))
 save('ENVIRONMENT_PACKAGES.json',dict(python=sys.version,executable=sys.executable,
      packages=sorted([{'name':d.metadata['Name'],'version':d.version} for d in importlib.metadata.distributions()],key=lambda d:d['name'].lower())))
 # Independently inventory the actual final JUnit, rather than only its summary.
 cases=list(ET.parse(RUN/'p5-runtime/results.xml').getroot().iter('testcase'))
 ids=[]
 for case in cases:
  assert not any(case.find(k) is not None for k in ('failure','error','skipped'))
  props={p.get('name'):p.get('value') for p in case.findall('./properties/property')}
  ids.append(props['p5_id'])
 assert len(ids)==76 and set(ids)=={f'P5-T{i:02}' for i in range(1,77)}
 save('P5_MANDATORY_TEST_ID_INVENTORY.json',dict(commit=summary['tested_implementation_commit'],tree=summary['tested_implementation_tree'],
      actual_collected_ids=sorted(ids),passed=76,failed=0,errors=0,skipped=0,xfail=0))
 observations=RUN/'p5-runtime/observations'
 stress={f:json.loads(json.loads((observations/('stress-'+f+'.json')).read_text())['stdout']) for f in ('CSV','XLSX')}
 assert all(v['result']=='PASS' and v['rows']==100000 and v['columns']==200 and v['independent_cells_checked']==20000000 and v['incremental_peak_rss_bytes']<=536870912 for v in stress.values())
 negative=json.loads(json.loads((observations/'stress-negative-expanded-text.json').read_text())['stdout'])
 assert negative['safe_preallocation_rejection'] and negative['new_final_artifacts']==0
 scopes=json.loads((observations/'P5-T76.json').read_text())['successor_scope_mutations']
 assert len(scopes)==17 and all(p['result']=='REJECTED' for p in scopes)
 schema=json.loads((RUN/'P0_SCHEMA_RESULTS.json').read_text())
 assert schema['available_schema_validation']=='PASS' and schema['schemas_checked']==20 and len(schema['missing_P_C_originals'])==13
 statics={name:json.loads((RUN/name/'stdout.txt').read_text()) for name in ('strict-design','amendment-static','numeric-static','supplement-static')}
 assert len(statics['strict-design']['mutation_probes'])==4 and all(statics['strict-design']['mutation_probes'].values())
 assert [len(statics[name]['mutations_rejected']) for name in ('amendment-static','numeric-static','supplement-static')]==[9,14,15]
 save('GOLDEN_ARTIFACT_CHECKS.json',{
   name:{'sha256':digest((observations/name).read_bytes()),'size_bytes':(observations/name).stat().st_size}
   for name in ('P-A.actual-result.csv','P-B.actual-result.xlsx','P-B.TEST-ONLY-projection.csv','P-D.actual-diagnostic.csv','P-A.original-P4-INTERNAL.json','P-B.original-P4-INTERNAL.json')})
 legacy=json.loads((RUN/'integrated-legacy/PHASE_AWARE_CLASSIFICATION.json').read_text())
 scope_ids=[r['test_id'] for r in legacy['records'] if r['classification']=='EXPECTED_HISTORICAL_SCOPE_CONFLICT']
 history=json.loads((HISTORY/'command-environment.json').read_text())
 phase_inventories={}
 expected_legacy={f'P{phase}-T{i:02}' for phase,n in ((1,42),(2,54),(3,52),(4,64)) for i in range(1,n+1)}
 for name,path in (('historical',HISTORY/'results.xml'),('actual_P5_compatibility',RUN/'integrated-legacy/results.xml')):
  records=[]
  for case in ET.parse(path).getroot().iter('testcase'):
   phase=re.search(r'(?:^|\.)p([1-4])(?:\.|$)',case.get('classname',''))
   number=re.match(r'test_T(\d+)_',case.get('name',''))
   assert phase and number
   outcome=next((tag for tag in ('failure','error','skipped') if case.find(tag) is not None),'pass')
   records.append(dict(test_id=f'P{phase[1]}-T{int(number[1]):02}',outcome=outcome))
  assert len(records)==212 and {r['test_id'] for r in records}==expected_legacy
  if name=='historical':assert all(r['outcome']=='pass' for r in records)
  else:
   assert {r['test_id'] for r in records if r['outcome']!='pass'}==set(scope_ids)
   assert all(r['outcome'] in ('pass','failure') for r in records)
  phase_inventories[name]=dict(total=len(records),passed=sum(r['outcome']=='pass' for r in records),
      failed=sum(r['outcome']=='failure' for r in records),records=records)
 save('HISTORICAL_AND_INTEGRATED_ID_INVENTORIES.json',phase_inventories)
 report=f'''# P5 Export and Deterministic QA — technical validation report

Date: {datetime.now(ZoneInfo('Europe/Moscow')).isoformat()}.

**Result: IMPLEMENTED / TECHNICALLY VALIDATED / NOT MERGED.** This is a technical result for owner review; it is not owner acceptance or closure of P5 Gate B. Gate B remains NOT_PASSED pending the owner's separate decision. No P6, merge or governance repin was performed.

## Authority, implementation and exact tested tree

The owner explicitly approved Gate A/Q01–Q08, CR-P5-001/002 and CR-P5-003. The latter's separate decision was read first from GitHub commit `{BASE}`. Versioned technical addendum v0.2c was committed as `20e78e55c8f461d01b9671c475ba7fa98ae0a745` before implementing its numeric behavior; original source archives and historical PROPOSED text remain unchanged.

- Branch: `feature/p5-export-deterministic-qa`.
- Owner-authorized start: `{BASE}`.
- **Tested implementation commit: `{summary['tested_implementation_commit']}`.**
- **Tested implementation tree: `{summary['tested_implementation_tree']}`.**
- The subsequent evidence-only commit/publication head is recorded separately after its creation. No full runtime regression on that descendant is claimed merely because its source bytes match.

P5 consumes real verified P4_INTERNAL_V2, keeps original P4 bytes/tags/checksum/Run unchanged, and applies only the approved exact integer→Decimal projection in approved decimal fields. It produces one authorized CSV or XLSX, performs full readback and all 23 DQ IDs, and uses existing P1 Artifact+Event then QAReport+Order+completion-Event commits. Existing committed Artifact reuse, detect-only orphan recovery, strict version/Approval binding, no resurrection of failed P5 Runs, read-only terminal replay and an explicit Streamlit action are implemented.

## Three separate regression families — CR-P5-002

| Family | Exact source | Observed outcome |
|---|---|---|
| Historical P1–P4 | `fd39aa1bed480313504ae8b1f76e77e170cb72ba`, tree `{history['tested_tree']}` | **212/212 PASS**: P1 42, P2 54, P3 52, P4 64; zero fail/error/skip/xfail; pytest wall time {history['elapsed_seconds']:.3f}s |
| Original legacy tests on actual P5 tree | Tested implementation SHA/tree above | **{legacy['passed']} PASS; {legacy['expected_historical_scope_conflicts']} pytest FAIL classified EXPECTED_HISTORICAL_SCOPE_CONFLICT; 0 blocking behavioral regressions** |
| P5 runtime acceptance on actual P5 tree | Same tested implementation SHA/tree above | **76/76 PASS**, complete actual ID inventory, zero fail/error/skip/xfail |

The integrated legacy exit code remains **1**, not 0. The exact conflict IDs are `{', '.join(scope_ids)}`. P2-T40/P3-T51/P4-T61/T62 reject the added approved P5 application scope. P3-T50 fails because its nested unchanged P2 suite fails P2-T40; P4-T63 contains the corresponding nested P2/P3 scope failures. The classifier checks actual child JUnit and exact assertions, and the new successor audit independently verifies the allowed integrated scope. These failures are never PASS, skip or xfail. No integrated 212/212 or combined 288/288 PASS claim is made.

## Actual stress and resource controls

| Format | Actual output / independent check | Entire P5 incremental sampled RSS | P5 export+QA wall time |
|---|---|---|---|
| CSV | READY + QA PASS, 100000×200, **20000000 cells independently checked** | {stress['CSV']['incremental_peak_rss_bytes']} bytes | {stress['CSV']['P5_elapsed_seconds']:.3f}s |
| XLSX | READY + QA PASS, 100000×200, **20000000 cells independently checked** | {stress['XLSX']['incremental_peak_rss_bytes']} bytes | {stress['XLSX']['P5_elapsed_seconds']:.3f}s |

Both are distinct isolated simulated approved Orders. Each uses the exact pinned 40500998-byte CSV source (SHA-256 `353698a4bab0ffc54633cb3fabad7eb404821b5f97dfeb7eb9676dafec4d9239`) with separately approved CSV/XLSX output format. This proves actual export and QA for both formats; it is not an XLSX input-ingestion stress claim. All headers, every output cell, actual output size/hash and zero-formula semantics are checked. Runtime RSS sampling is 10ms; the independent worker samples at 5ms. Each is within the approved 536870912-byte incremental bound. No new hard P5 time SLA is invented.

A separate actual approved-operation 100000×200 expanded-text P4 result of **{negative['P4_internal_bytes']} bytes** reaches P5 and is rejected before unsafe full-buffer allocation: EXPORT_FAILED, FAILED Order, zero new final Artifact/report, original P4 checksum unchanged. A forced-budget control, oversized XLSX text, signed64/Decimal precision extremes and intentionally bypassed preflight are additional negatives. None replaces either successful fixed workload.

## Goldens, numerical semantics and deterministic QA

- Actual P-A export equals the immutable 277-byte CSV golden, including original P4 `integer:0` in its approved decimal field projected as `0.0`; QA PASS / READY.
- Actual isolated P-B v2 export has six headers, three rows and 18 exact cells, one production RESULT_XLSX and 24 check results including separate DQ-017(PB-AC-006/007); source cached formulas produce PASS_WITH_WARNINGS, exported formulas remain zero. Its 245-byte CSV is only a test projection and is never registered as another production result.
- Actual P-D diagnostic CSV equals the immutable 118-byte golden; lexical roundtrip PASS coexists with typed DQ-011/012/014 blockers, QA_BLOCKER and NEEDS_FIX. No false READY or null→empty typed repair.
- Whole-service signed64 CSV tests include 2^53 boundaries and signed64 extrema in both strict integer and approved decimal fields. All forbidden numeric conversions remain negative. XLSX 15-digit/magnitude admission and independent raw-XML/openpyxl numeric guards reject loss, wrong type and numeric-as-text. NFD Unicode, quoting/newlines and explicit XLSX text remain unchanged data.
- Brief and Spec field domains/uniqueness are both enforced; referenced criterion IDs/targets remain distinct. Full-row metrics, exact rational null thresholds, ordered approved operation bindings, complete mandatory/conditional coverage and deterministic FAIL authority are retained. DQ-020/021 and LLM checks are absent.

## Schema, scope, recovery and failure evidence

Actual real P0 schemas: **20 schemas; {schema['positive_validations']} positive schema applications PASS**. All 116 present P0 manifest payloads match; 13 original P-C files are still absent. The 24 available negative examples include 15 schema rejections and 9 cases requiring semantic guards; original legacy behavior and available negative assertions remain executed. Full P-C positive/golden coverage is explicitly unavailable.

The four unchanged source verifiers pass against real P0 where applicable; **42/42 static mutation probes rejected** (4+9+14+15). They are static checks, not substitutes for the 76 runtime IDs. Their preserved historical stdout headings do not override subsequent owner approvals.

The successor integrated audit passes and rejects **17/17** mutations covering source, historical tests, P0 schemas/fixtures, migrations, dependencies, DECISIONS, G3 pin, old/new policies, unknown modules/files, imports, arbitrary execution, new operations and UI auto-triggering. Ambiguous final Artifacts are rejected without writes. Its finite new-source/test/document list and committed HEAD/index/mode checks preserve all historical inputs; the active G3 pin stays SHA-256 `95b7c92a417ec06a80f3d4e839e136e00100e4313d1bee021c94f5beda1f0df7`.

Actual SIGKILL witnesses cover orphan-after-promotion detect-only behavior, reuse after Artifact commit and read-only repeat after final commit. Report-UoW abort rolls back report/Order/Event together while retaining exactly one committed Artifact; explicit retry reuses it. Concurrent initial calls create one result/report. Source corruption blocks writes; writer errors, unsafe CSV formulas and altered staged data fail closed; passive Streamlit rerenders add no records.

## Preservation and evidence provenance

`PROTECTED_FILES_BEFORE_AFTER.json` compares every owner-start file: **{len(protected)-1} unchanged**, with exactly the authorized two-line `src/vde/app.py` append as the sole old-file edit. There are 23 new implementation/addendum/test/document paths plus that one edit; exact inventory/diff are included. P0–P4 contracts, runtime modules other than the permitted app integration, old tests/assertions, original fixtures/packages/evidence, migrations, dependency/lock files, DECISIONS and G3 pin remain unchanged. Test-generated historical outputs were captured under the new evidence root and the prior bytes restored, with source/commit/tree checks after each phase.

All final mandatory phases belong to the tested implementation SHA/tree above; the historical phase has its separately stated frozen identity. Full raw stdout/stderr, commands/environment/exit codes, JUnit, actual test-ID inventory, reports, small generated golden outputs, hashes and fixture/negative/recovery/resource observations are included. The unchanged original handoff ZIP is already in the repository; temporary unpacked duplicate source files are omitted from this evidence copy and are reproducible from that archive.

Earlier committed candidate `e332519fb10dfb72717876d2cbe502f23b1be54a` and development diagnostics are separate. Its legacy suite also produced 206 PASS/6 scope failures, but the first outer classifier omitted the P3-T50 cascade and stopped before P5 runtime. That new P5 runner was corrected; no historical assertion was altered. Dirty development checks are diagnostics only, not exact-tree Gate B evidence. No earlier validation evidence is overwritten or retroactively marked PASS.

The next candidate `8a8b8ace8944acacc24ba1e33a29f700d5e5b334` executed all 76 P5 tests: 75 passed and T72 failed while preparing the separate expanded-text negative's Spec, because the new generator omitted the existing mandatory `replace.params.regex=false`. Both successful stress exports on that earlier candidate are preserved, but its complete run remains FAILED. Only the new generator was corrected to conform to the unchanged P0 schema, then all mandatory actual-P5 phases were rerun on the final implementation SHA/tree above. No contract, fixture or assertion was relaxed.

## Limits and handoff

- P-C: 13 missing certified historical originals; full positive coverage is not claimed.
- P-B v2 positive mechanics use isolated simulated local-user workflow actions. Supplied future TEST_ONLY Approval is rejected as live authority. No real business Approval is issued by these tests or by the owner's project-level CR approval.
- Local single-process serialization and sampled Linux RSS are measured controls, not distributed locking, OS memory isolation, a universal worst-case success guarantee, Windows validation or physical power-loss proof.
- P5 Gate B, acceptance and integration approval remain solely with the owner/Main Managing Chat. No merge, governance repin or P6 was performed. Remote main/branch and published object verification are recorded separately after publication.

**Handoff recommendation: independent owner review of the technically validated P5 candidate under CR-P5-002. Gate B remains NOT_PASSED until the owner's separate decision.**
'''
 (EV/'P5_VALIDATION_REPORT.md').write_text(report)
 # Finite root-relative inventory: manifest excludes its own checksum only.
 files=sorted(p.relative_to(REPO).as_posix() for p in EV.rglob('*') if p.is_file())
 inventory_path=(EV/'EVIDENCE_FILES.txt').relative_to(REPO).as_posix()
 manifest_path=(EV/'MANIFEST.sha256').relative_to(REPO).as_posix()
 files=sorted(set(files+[inventory_path,manifest_path]))
 (REPO/inventory_path).write_text(''.join(f+'\n' for f in files))
 (REPO/manifest_path).write_text(''.join(digest((REPO/f).read_bytes())+'  '+f+'\n' for f in files if f!=manifest_path))
 print(json.dumps({'evidence_files':len(files),'manifest_entries':len(files)-1,'manifest_sha256':digest((REPO/manifest_path).read_bytes()),'tested_commit':summary['tested_implementation_commit']},indent=2))


if __name__=='__main__':main()
