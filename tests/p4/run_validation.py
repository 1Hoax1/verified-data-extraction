"""Record mandatory live P1-P4 validation without altering historical evidence."""
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'docs/p4/validation'
BASE = '7685110506d115805c473b064752f86e9e5c045b'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    assert git('branch', '--show-current') == 'feature/p4-deterministic-engine'
    sha = git('rev-parse', 'HEAD')
    OUT.mkdir(parents=True, exist_ok=True)
    changes = git('status', '--porcelain=v1').splitlines()
    assert all(line[3:].startswith('docs/p4/validation/') for line in changes), changes
    for group in ('f-fixture', 'x-fixture', 'w-fixture', 'golden', 'generator', 'p0-semantic'):
        (OUT/(group+'-results.json')).write_text('{}\n')
    # Original upstream tests intentionally emit files in their historical
    # validation folders. Preserve their original bytes and retain new evidence
    # under P4 instead of committing changed P2/P3 validation history.
    originals = {p: p.read_bytes() for phase in ('p2','p3') for p in (ROOT/'docs'/phase/'validation').iterdir() if p.is_file()}
    command = [sys.executable, '-m', 'pytest', 'tests/p1', 'tests/p2', 'tests/p3', 'tests/p4',
               '-q', '--junitxml='+str(OUT/'all-results.xml')]
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT/'src')+os.pathsep+str(ROOT/'tests')
    started = datetime.now(ZoneInfo('Europe/Moscow')).isoformat()
    try:
        run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
    finally:
        for phase in ('p2','p3'):
            for p in (ROOT/'docs'/phase/'validation').iterdir():
                if not p.is_file():
                    continue
                data = p.read_bytes()
                if p not in originals or data != originals[p]:
                    target = OUT/'upstream-generated'/phase/p.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                if p in originals:
                    p.write_bytes(originals[p])
                else:
                    p.unlink()
    finished = datetime.now(ZoneInfo('Europe/Moscow')).isoformat()
    (OUT/'all-tests.stdout.txt').write_bytes(run.stdout)
    (OUT/'all-tests.stderr.txt').write_bytes(run.stderr)
    record = dict(tested_commit=sha, baseline_commit=BASE, command=command, cwd=str(ROOT),
                  started_at_moscow=started, finished_at_moscow=finished, exit_code=run.returncode,
                  PYTHONPATH=env['PYTHONPATH'], python=sys.version, executable=sys.executable,
                  platform=platform.platform(), packages={p:importlib.metadata.version(p) for p in
                  ('pytest','jsonschema','referencing','rfc8785','openpyxl','streamlit')})
    (OUT/'command-environment.json').write_text(json.dumps(record,indent=2)+'\n')
    print(run.stdout.decode(), end='')
    print(run.stderr.decode(), end='', file=sys.stderr)
    if run.returncode:
        return run.returncode
    wanted = {'p1':42, 'p2':54, 'p3':52, 'p4':64}
    results = {p:{} for p in wanted}
    for case in ET.parse(OUT/'all-results.xml').getroot().iter('testcase'):
        name, module = case.get('name'), case.get('classname')
        phase = next((p for p in wanted if f'test_{p}' in module), 'p4' if 'test_execution' in module else None)
        assert phase is not None, (name,module)
        number = re.fullmatch(r'test_T(\d{2})_.+', name).group(1)
        identity = phase.upper()+'-T'+number
        assert identity not in results[phase]
        assert all(case.find(k) is None for k in ('failure','error','skipped')), identity
        results[phase][identity] = {'status':'PASS','seconds':float(case.get('time')),'test':name}
    assert sum(map(len, results.values())) == 212
    for phase, count in wanted.items():
        assert set(results[phase]) == {phase.upper()+f'-T{i:02}' for i in range(1,count+1)}
    for group, prefix, count in [('f-fixture','P4-F',38),('x-fixture','P4-X',19),('w-fixture','P4-W',45)]:
        data = json.loads((OUT/(group+'-results.json')).read_text())
        assert set(data) == {prefix+f'{i:02}' for i in range(1,count+1)}
        assert all(v['result'] == 'PASS' for v in data.values())
    stress = json.loads((OUT/'stress.stdout.txt').read_text())
    assert stress['result']=='PASS' and stress['elapsed_seconds']<=120 and stress['incremental_peak_rss_bytes']<=536870912
    assert stress['tested_commit'] == sha
    (OUT/'TEST_STATUS.json').write_text(json.dumps(results,indent=2)+'\n')
    summary = dict(status='TECHNICAL_ACCEPTANCE_PASS; GATE_B_PENDING_OWNER_REVIEW', tested_commit=sha,
                   mandatory_tests={p:{'passed':n,'failures':0,'errors':0,'skips':0,'xfails':0} for p,n in wanted.items()},
                   total_passed=212, f_fixtures=38, x_fixtures=19, w_fixtures=45,
                   approved_zip_sha256=hashlib.sha256((ROOT/'docs/p4/v1.0/P4_Implementation_Pack_v1.0_APPROVED.zip').read_bytes()).hexdigest(),
                   stress=stress, CRs=['CR-P4-001','CR-P4-002','CR-P4-003','CR-P4-004'],
                   upstream_validation_history_restored=True)
    (OUT/'validation-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    changed = set(git('diff','--name-only',BASE).splitlines())
    changed.update(p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file())
    changed.add('docs/p4/validation/P4_GATE_B_VALIDATION_REPORT.md')
    changed.add('docs/p4/validation/CHANGED_FILES.txt')
    (OUT/'CHANGED_FILES.txt').write_text('\n'.join(sorted(changed))+'\n')
    report = f'''# P4 Gate B — implementation validation report

**Status: READY FOR INDEPENDENT REVIEW. Gate B NOT_CLOSED; P4 not self-declared VALIDATED.**

Branch: `feature/p4-deterministic-engine`. Exact tested code/tests commit: `{sha}`. Authorized baseline: `{BASE}`.

## Actual required results

| Suite | PASS | FAIL / ERROR / SKIP / XFAIL |
|---|---:|---|
| P1 | 42/42 | 0 / 0 / 0 / 0 |
| P2 | 54/54 | 0 / 0 / 0 / 0 |
| P3 | 52/52 | 0 / 0 / 0 / 0 |
| P4 | 64/64 | 0 / 0 / 0 / 0 |

All **212 exact IDs** were executed in one combined pytest invocation, with original P3's required nested P1/P2 regressions also retained. Exact command, cwd, environment, package versions, timestamps and exit code: `command-environment.json`; complete stdout/stderr: `all-tests.stdout.txt` / `all-tests.stderr.txt`; JUnit: `all-results.xml`; per-ID duration/results: `TEST_STATUS.json`. Exit code 0. Original upstream validation files were restored byte-for-byte; new upstream-run artifacts are retained under `upstream-generated/`.

38/38 F fixtures execute real operations and compare every ordered cell/error. 19/19 X drivers exercise actual immutable-fact admission, failure UoWs, manual UI or separate-process crash/reopen. 45/45 W cases exercise actual parse/encode/decode/Unicode/overflow behavior. P0 P-A/P-B all ordered fields and exact golden CSV SHA match under the approved test-only projection. Frozen P0 NFC/JCS vectors pass. The approved ZIP SHA and 53 payload entries pass, and its actual strict verifier uses real P0 schemas/goldens and rejects 9/9 mutants. Source bytes remain unchanged. Detailed driver records: `f-fixture-results.json`, `x-fixture-results.json`, `w-fixture-results.json`, `golden-results.json`, `fixture-verifier.*`.

## Implemented components

P4-owned execution admission/service, full-row CSV/XLSX adapter reusing frozen P2 SafeZip/cached-cell guards, all 12 closed operations, stable bounded external sort/dedup, checksummed spill records, bounded provenance, sampled resource budget, exact signed64/Decimal/date/Unicode V2 wire, P1-native artifact publication and separate Run completion, read-only internal delivery checks, explicit Streamlit Execute control. P3 P4Handoff fields unchanged. Order stays EXECUTING after Run.succeeded. No QAReport, final CSV/XLSX, READY or automatic retry/recovery.

## Full-density runtime resource evidence

Fresh process reads the reproducible **40,801,000-byte 100000×200** source, raw SHA `5c5d2dbf69c0b8f4d27be5ec8a258677eb883d5ad267a4ec644b0205978aa97d`, executes parse_number→sort→deduplicate and stores **90000×200**. All **18,000,000** resulting typed cells and the canonical digest match an independent streaming modular-arithmetic reference.

- Elapsed from verified start to durable completion: **{stress['elapsed_seconds']:.6f} seconds**, limit 120 seconds.
- Independent incremental peak RSS: **{stress['incremental_peak_rss_bytes']} bytes**, limit 536870912 bytes; Linux VmRSS 5 ms sampling and ru_maxrss.
- Runtime scratch peak: **{stress['runtime_resources']['scratch_peak_bytes']} bytes**, limit 2147483648 bytes.
- Merge fan-in: **{stress['runtime_resources']['merge_fan_in']}**, limit 16.
- Result canonical SHA-256: `{stress['result_sha256']}`.

Positive workload succeeds; injected RSS/time/scratch/row/column/parse failures additionally exercise actual guards and legal failed-run handling. Corrupted spill records reject by checksum. No controlled failure substitutes for the positive capacity result. Exact resource process output and command: `stress.*`.

## Crash/restart and atomicity

Actual child SIGKILL (-9) before start commit, after start commit, mid-pipeline, after promotion and after final success; injected Artifact EventLog insert failure; additional crash between Artifact commit and Run completion. Fresh bootstrap observes exact statuses, per-attempt events/artifacts/orphans and stale-run counts. X13: no Run/event; X14/15: running+EXECUTING, one event, degraded; X16/X18: one orphan, no Artifact metadata, running, one event; X17: succeeded, one verified Artifact, three events, ready health. Intermediate Artifact commit alone leaves running with two events and no eligible handoff. No adoption, deletion, resume or auto-terminalization. Explicit ready FAILED retry creates a new Run, retaining prior immutable IDs. Full checkpoints/public failures: `x-fixture-results.json` and `restart-*.command.json/stdout.txt/stderr.txt`.

## Scope and authorized amendments

P4-T61/T62 audit all 42 source files, exact P4 paths/hashes/surfaces, frozen legacy source/contracts, dependency/lock/migration inventory and forbidden-feature mutations. CR-P4-001 is implemented in the test boundary only; every original P3-T51 negative probe remains. Frozen P1/P2/P3 production modules and original approved packs are unchanged; app.py only appends the approved P4 panel integration.

Owner explicitly approved during implementation: **CR-P4-002** corrects T13 to four original P-B source rows (T42 remains three final rows); **CR-P4-003** updates only P2-T40/P3-T51 changed-path diff baseline to the authorized start; **CR-P4-004** corrects signed Decimal proper-fraction wire grammar (-0.25), retaining all canonical-spelling rejections. Separate versioned amendments and supplemental Decimal cases document these exact changes. Original ZIP and F/X/W source fixtures are untouched. No other contract deviation, dependency, infrastructure or operation added. DECISIONS.md and authoritative Gate decisions remain unchanged.

## Risks and limits for owner review

Linux/Python 3.12.14/openpyxl 3.1.5 only; no Windows/network-filesystem/physical-power-loss or independent-host/CI validation. RSS is sampled, not hard OS isolation; 120 seconds is a soft cooperative deadline. AppTest is automated, not manual browser sign-off. P1 requires one complete opaque byte allocation at final publication; logical datasets/stream buffers stay bounded and the allocation is budget-checked. Artifact commit and Run completion remain separate P1 UoWs, with the intervening crash explicitly rejected. Static inventory checks are regression controls, not a malicious-code sandbox.

The known 13 missing P0 P-C manifest files remain an inherited separate discrepancy; no synthetic restoration or P0 manifest rewrite. Strict P4 verifier uses the real required P0 subset. The legacy X17 descriptive string mentioning V1 is interpreted under the binding approved Q03 V2 decision; its executable format/checksum/identity assertions use V2. No P5 export/QA, unapproved statuses, new SQLite schema, network ingestion or external automation is implemented.

Changed-file inventory: `CHANGED_FILES.txt`. This report/evidence may be committed after the tested SHA; a later evidence-only commit is not a different tested runtime. Final PR must stay Draft and unmerged. **Main managing chat alone decides P4 Gate B closure.**
'''
    (OUT/'P4_GATE_B_VALIDATION_REPORT.md').write_text(report)
    print('VALIDATED TEST OUTCOMES: 212/212, F38/X19/W45, owner Gate B closure still pending')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
