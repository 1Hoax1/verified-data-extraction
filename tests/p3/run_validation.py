"""Run the 52-test suite including real P1/P2 regressions; record exact evidence.

This driver never turns failures into success, skips or xfails. Historical P2
evidence files are restored by the regression harness after their fresh outputs
are copied into this P3 evidence directory.
"""
from datetime import datetime, timezone
import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path
import platform
import subprocess
import sys
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/p3/validation'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sha = git('rev-parse', 'HEAD')
    # Tests must correspond to committed source. Evidence may change during run.
    changes = git('status', '--porcelain').splitlines()
    assert all(line[3:].startswith('docs/p3/validation/') for line in changes), changes
    start = datetime.now(timezone.utc).isoformat()
    command = [sys.executable, '-m', 'pytest', 'tests/p3', '-q', '--junitxml=' + str(OUT / 'p3-results.xml')]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (OUT / 'p3-run.log').write_text('COMMAND ' + json.dumps(command) + '\nTESTED_COMMIT ' + sha + '\n' + proc.stdout + proc.stderr)
    if proc.returncode:
        print(proc.stdout + proc.stderr)
        return proc.returncode
    rows, counts = [], {}
    for phase, count in [('p1', 42), ('p2', 54), ('p3', 52)]:
        suite = ET.parse(OUT / (phase + '-results.xml')).getroot()[0]
        counts[phase] = {k: int(suite.get(k)) for k in ('tests', 'failures', 'errors', 'skipped')}
        assert counts[phase] == dict(tests=count, failures=0, errors=0, skipped=0)
        for case in suite.findall('testcase'):
            identity = next(p.get('value') for p in case.findall('properties/property') if p.get('name') == phase + '_id')
            assert not list(case.findall('failure')) + list(case.findall('error')) + list(case.findall('skipped'))
            rows.append((identity, 'PASS', case.get('name'), case.get('time')))
        assert {r[0] for r in rows if r[0].startswith(phase.upper())} == {phase.upper() + f'-T{i:02}' for i in range(1, count + 1)}
    assert len(rows) == 148
    scenarios = json.loads((OUT / 'scenario-results.json').read_text())
    assert set(scenarios) == {f'P3-F{i:02}' for i in range(1, 41)}
    assert all(r['result'] == 'PASS' for r in scenarios.values())
    rss = {kind: json.loads((OUT / ('rss-' + kind + '.json')).read_text()) for kind in ('csv', 'xlsx')}
    assert all(r['tested_commit'] == sha and r['incremental_peak_bytes'] <= 536870912 for r in rss.values())
    fixture = json.loads((OUT / 'fixture-verification.json').read_text())
    assert fixture['tested_commit'] == sha and fixture['xlsx_regenerated_byte_identical'] == 21
    protected = ['pecs/pilot_slice_v1', 'docs/p1/v1.0', 'docs/p2/v1.0', 'docs/p3/v1.0',
                 'src/vde/ingestion', 'src/vde/persistence', 'src/vde/bootstrap.py', 'src/vde/config.py',
                 'src/vde/contracts.py', 'src/vde/errors.py', 'src/vde/models.py', 'src/vde/storage.py',
                 'src/vde/workspace.py', 'src/vde/recovery.py', 'uv.lock']
    assert not git('diff', 'ba73d05d2294dfb7e51b9c3c758e63c6065286d6', '--', *protected)
    source_paths = git('ls-files', 'src', 'tests', 'pyproject.toml', 'uv.lock').splitlines()
    source_hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_paths}
    summary = dict(tested_commit=sha, authorized_main='ba73d05d2294dfb7e51b9c3c758e63c6065286d6',
                   started_at_utc=start, finished_at_utc=datetime.now(timezone.utc).isoformat(),
                   command_argv=command, counts=counts, total_pass=148, fail=0, error=0, skip=0, xfail=0,
                   python=sys.version, executable=sys.executable, platform=platform.platform(),
                   packages=sorted([{'name': d.metadata['Name'], 'version': d.version} for d in distributions()], key=lambda d: d['name']),
                   rss={k: r['incremental_peak_bytes'] for k, r in rss.items()}, rss_limit_bytes=536870912,
                   approved_scenarios_pass=40, regenerated_xlsx_byte_identical=21,
                   frozen_runtime_and_packs_unchanged=True, source_sha256=source_hashes)
    (OUT / 'validation-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (OUT / 'TEST_STATUS.md').write_text('# P3 implementation test results\n\nTested commit: `' + sha + '`\n\n'
        '| ID | Actual result | Test | Seconds |\n|---|---|---|---|\n' +
        ''.join('| ' + ' | '.join(row) + ' |\n' for row in sorted(rows)))
    report = f'''# P3 Validation Report

Implementation evidence for owner review. P3 Gate B remains open; no P3 VALIDATED declaration, merge or P4 start is performed.

Tested commit: `{sha}`. Authorized main baseline: `ba73d05d2294dfb7e51b9c3c758e63c6065286d6`.
Run started `{start}`; finished `{summary['finished_at_utc']}`.

| Suite | PASS | FAIL | ERROR | SKIP | XFAIL |
|---|---:|---:|---:|---:|---:|
| P3-T01…P3-T52 | 52 | 0 | 0 | 0 | 0 |
| P2-T01…P2-T54 | 54 | 0 | 0 | 0 | 0 |
| P1-T01…P1-T42 | 42 | 0 | 0 | 0 | 0 |
| Total | 148 | 0 | 0 | 0 | 0 |

Actual command from repository root: `{sys.executable} tests/p3/run_validation.py`.
This executes `{sys.executable} -m pytest tests/p3 -q --junitxml=docs/p3/validation/p3-results.xml`.
P3-T49 and T50 actually execute separate `pytest tests/p1` and `pytest tests/p2` subprocesses with their own JUnit files, then verify every required ID. Exact argv/stdout/stderr are in [P3 log](p3-run.log), [P1 log](p1-run.log), [P2 log](p2-run.log). JUnit: [P3](p3-results.xml), [P1](p1-results.xml), [P2](p2-results.xml). All 148 individual results: [test status](TEST_STATUS.md).

Environment: `{platform.platform()}`; Python `{platform.python_version()}`; Streamlit 1.50.0, openpyxl 3.1.5, pytest 8.4.2, frozen uv dependency graph. Full installed versions and source/test SHA-256 values: [summary](validation-summary.json). Tests use temporary POSIX workspaces with SQLite foreign keys, P1 BEGIN IMMEDIATE/CAS and filesystem durability barriers. UI uses real Streamlit AppTest; restart/crash checks use separate Python processes.

Approved P3 ZIP SHA-256: `8a77848419161a5f784b61e7302a058e5c23e2ff5925e88a643c350e80930bc7`. All 64 manifest entries, sizes and hashes verified. [Verifier --repo](fixture-verifier.log) confirms 40 reachable profiles, pinned P0 bytes, NFC oracle and rejection of five corrected Approval mutants. This design verifier explicitly reports runtime tests NOT_RUN; the separate [runtime scenario evidence](scenario-results.json) records all 40 actual fixture drivers PASS.

P0 P-A/P-B previews, Brief/Spec documents and semantic hashes match unchanged goldens. P-C forbidden confirmation fields/context and P-D schema negatives are checked at their proper schema boundary. P0 NFC/RFC8785 vectors and the F07 exact normalized digest pass. All normative packs and P1/P2 runtime, migration and lock bytes are unchanged from the authorized baseline.

P2-T54 regenerates all 21 XLSX binaries in a new temporary directory and compares exact bytes; all 12 CSV fixture hashes are verified. [Fixture evidence](fixture-verification.json). Both stress probes scan 100000 rows with five preview rows and no dataset handle, including the upload buffer:

| Source | Incremental peak RSS, bytes | Limit, bytes | Result |
|---|---:|---:|---|
| CSV | {rss['csv']['incremental_peak_bytes']} | 536870912 | PASS |
| XLSX | {rss['xlsx']['incremental_peak_bytes']} | 536870912 | PASS |

Measurement uses fresh-process Linux VmRSS 5 ms samples and kernel ru_maxrss; the larger observed peak is used. Exact buffers, shapes, hashes, argv, baselines and peaks: [CSV](rss-csv.json), [XLSX](rss-xlsx.json).

Atomicity: injected EventLog failure covers every P3 mutation; stale expected Order and a late CAS failure leave all business rows unchanged; actual connection.commit failure rolls back final Approval/Order/EventLog. [Crash evidence](crash-restart-results.json) checks both approvals after uncommitted writes and after completed commit with abrupt process exit; fresh processes see the complete prior or committed state. Trusted restart preserves exact pointers, hashes, Approvals and EventLog. Tampered authoritative JSON/source blocks trust; degraded/blocked health prevents mutations. Exact duplicate approvals add no row/event. Streamlit completes the existing-Order workflow without SQL edits, keeps unsaved drafts in session only, and passive reruns produce zero business writes.

CR-P3-002 is implemented solely at the historical test boundary: P2-T40 and every original negative probe remain; explicit P1/P2 modules are frozen; reviewed P3 paths/app integration are allowed. P3-T51 checks the complete source inventory, hashes/surfaces, dependency graph, migration and actual SQLite tables, with forbidden integration/execution/dependency/schema/runtime-drift probes. [Versioned amendment](../../p2/amendments/v1.1/P2_TEST_PLAN_AMENDMENT.md), [traceability](TRACEABILITY.md).

Known limitations: CR-P3-001 remains deferred, so APPROVED revisions are blocked. Drafts are not durable. No Order creation, P4 execution, exports or QA is offered; P-D data-dependent preflight/parse/QA outcomes belong to later stages. RSS guards are sampled Linux checks, not an OS memory sandbox. Static inventory/hash audits are regression controls, not proof against deliberately obfuscated code. Immutability is enforced through supported APIs and verified loads, not against a hostile SQLite administrator. AppTest is automated Streamlit coverage; no separate human browser sign-off is claimed. No new normative conflict or unresolved implementation blocker was found; owner review and Gate B decision remain pending.

Initial unsuccessful development runs are preserved under [attempts](attempts/): 39/49 failures before correcting P2 selection adaptation, 4/49 before fixing criteria-reference validation/harness classification, 1/52 when the original positional P2 UI test encountered added P3 controls, and 1/52 from a setup assertion incorrectly assuming UUID order for two approvals timestamped in the same second. These were uncommitted development states, with no claimed exact source SHA. P3 now opens through an explicit checkbox, preserving P2 UI behavior and its original T35 assertions; no P2 test criterion was weakened. The setup assertion matches each exact approval tuple independently of UUID ordering. Final evidence above comes only from the committed tested source. Historical P2 closure artifacts are restored after regression outputs are copied into this P3 directory.

The subsequent evidence commit may change only `docs/p3/validation/`; its PR head is distinct from the tested code commit. Owners should use the tested SHA and source hash manifest when reviewing results.
'''
    (OUT / 'P3_VALIDATION_REPORT.md').write_text(report)
    print(json.dumps({'tested_commit': sha, 'tests_pass': 148, 'rss': summary['rss']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
