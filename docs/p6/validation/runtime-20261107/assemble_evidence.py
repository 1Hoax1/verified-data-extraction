"""Assemble actual P6 outcomes including failures; never fabricate Gate B PASS."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

REPO = Path('/workspace/p6-streamlit-e2e')
WORK = Path('/workspace/p6-work')
RUN = WORK / 'final-02'
DOCKER = WORK / 'docker-smoke/implementation-deddc2799464-20261107'
START = 'b93e0ef4ed69343968ff7ae4188d586c0d1485a5'
MAIN = '0af4a1ff49ccf8fa59c39780d749e15cb5042fc3'
IMPLEMENTATION = 'deddc2799464076227173bd2e4890f552ffe64bf'
EVIDENCE = REPO / 'docs/p6/validation/runtime-20261107'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    p = EVIDENCE / name; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def main():
    assert not git('status', '--porcelain').strip()
    assert git('rev-parse', 'HEAD').decode().strip() == IMPLEMENTATION
    summary = json.loads((RUN / 'VALIDATION_SUMMARY.json').read_text())
    assert summary['tested_commit'] == IMPLEMENTATION
    tree = git('rev-parse', 'HEAD^{tree}').decode().strip()
    assert summary['tested_tree'] == tree
    for phase in ('p6-collection', 'legacy-p1-p4', 'legacy-p5', 'p6-runtime'):
        meta = json.loads((RUN / phase / 'command.json').read_text())
        assert meta['tested_commit'] == IMPLEMENTATION and meta['tested_tree'] == tree
        assert meta['historical_evidence_restored'] and meta['inputs_unchanged'] and meta['commit_unchanged']
        assert not meta['final_git_status']
    assert summary['scope_before']['result'] == summary['scope_after']['result'] == 'PASS'
    assert not EVIDENCE.exists()
    EVIDENCE.mkdir(parents=True)
    shutil.copytree(RUN, EVIDENCE / 'final-run')
    for name in ('final-02.runner.stdout.txt', 'final-02.runner.stderr.txt', 'final-02.runner.invocation.json'):
        shutil.copyfile(WORK / name, EVIDENCE / name)
    shutil.copytree(WORK / 'p0-final-02', EVIDENCE / 'p0-schemas')
    docker = json.loads((DOCKER / 'diagnostic-summary.json').read_text())
    assert docker['status'] == 'LINUX_DOCKER_PASSED' and docker['source_commit'] == IMPLEMENTATION
    assert (DOCKER / 'source-commit.stdout.txt').read_text().splitlines() == [IMPLEMENTATION, tree]
    assert not (DOCKER / 'source-status.stdout.txt').read_text().strip()
    shutil.copytree(DOCKER, EVIDENCE / 'linux-docker', ignore=shutil.ignore_patterns('workspace'))
    for name in ('run.py', 'driver.py'):
        shutil.copyfile(WORK / 'docker-smoke' / name, EVIDENCE / 'linux-docker' / name)
    for name in ('final-deddc27.stdout.txt', 'final-deddc27.stderr.txt'):
        shutil.copyfile(WORK / 'docker-smoke' / name, EVIDENCE / 'linux-docker' / name)
    shutil.copytree(WORK / 'dev-final-01', EVIDENCE / 'development-diagnostics')
    shutil.copytree(WORK / 'final-01', EVIDENCE / 'earlier-candidate-9838151')
    for name in ('final-01.runner.stdout.txt', 'final-01.runner.stderr.txt'):
        shutil.copyfile(WORK / name, EVIDENCE / 'earlier-candidate-9838151' / name)
    shutil.copyfile(WORK / 'CR-P6-002_PROPOSED.md', EVIDENCE / 'CR-P6-002_PROPOSED.md')
    shutil.copyfile(Path(__file__), EVIDENCE / 'assemble_evidence.py')
    shutil.copyfile(WORK / 'publish_and_verify.py', EVIDENCE / 'publish_and_verify.py')
    shutil.copyfile(WORK / 'make_review_archive.py', EVIDENCE / 'make_review_archive.py')

    # Independently inspect JUnit rather than accepting a green console string.
    cases = list(ET.parse(RUN / 'p6-runtime/results.xml').getroot().iter('testcase'))
    rows = []
    for case in cases:
        props = {p.get('name'):p.get('value') for p in case.findall('./properties/property')}
        outcome = next((t for t in ('failure', 'error', 'skipped') if case.find(t) is not None), 'pass')
        rows.append(dict(test_id=props['p6_id'], name=case.get('name'), outcome=outcome,
                         assertion=case.find(outcome).text if outcome != 'pass' else None))
    assert len(rows) == 20 and {r['test_id'] for r in rows} == {f'P6-T{i:02}' for i in range(1,21)}
    assert not any(r['outcome'] in ('error', 'skipped') for r in rows)
    save('P6_ACTUAL_TEST_ID_INVENTORY.json', dict(commit=IMPLEMENTATION, tree=tree, records=rows))
    legacy = json.loads((RUN / 'legacy-p1-p4/PHASE_AWARE_CLASSIFICATION.json').read_text())
    old_p5 = json.loads((RUN / 'P5_PHASE_AWARE_CLASSIFICATION.json').read_text())
    assert len(legacy['records']) == 212 and len(old_p5) == 76
    save('REGRESSION_ACTUAL_TEST_ID_INVENTORY.json', {
        'tested_commit': IMPLEMENTATION, 'tested_tree': tree,
        'P1_P4': legacy['records'], 'P5': old_p5})
    save('LEGACY_SCOPE_FAILURE_IDS.json', {
        'P1_P4':[r['test_id'] for r in legacy['records'] if r['classification']=='EXPECTED_HISTORICAL_SCOPE_CONFLICT'],
        'P5':[r['test_id'] for r in old_p5 if r['classification']=='EXPECTED_HISTORICAL_SCOPE_CONFLICT']})

    # Exact old bytes/modes with only the expressly authorized app integration.
    sys.path[:0] = [str(REPO / 'src'), str(REPO / 'tests')]
    from p6.scope_audit import expected_app, SOURCES, TESTS, DOCS
    protected = []
    for item in git('ls-tree', '-rz', '--full-tree', START).split(b'\0'):
        if not item: continue
        header, path = item.decode().split('\t'); mode, kind, blob = header.split()
        assert kind == 'blob'
        original = git('cat-file', 'blob', blob)
        wanted = expected_app(original) if path == 'src/vde/app.py' else original
        actual = (REPO / path).read_bytes()
        assert wanted == actual == git('show', IMPLEMENTATION + ':' + path), path
        protected.append(dict(path=path, mode=mode, blob_before=blob,
            blob_after=git('rev-parse', IMPLEMENTATION + ':' + path).decode().strip(),
            sha256_before=digest(original), sha256_after=digest(actual),
            classification='EXACT_FOUR_APP_LINES' if path == 'src/vde/app.py' else 'UNCHANGED'))
    save('PROTECTED_FILES_BEFORE_AFTER.json', dict(start=START, baseline=MAIN, result='PASS',
        files=len(protected), unchanged=sum(r['classification']=='UNCHANGED' for r in protected), records=protected))
    diff = git('diff', '--binary', START, IMPLEMENTATION)
    (EVIDENCE / 'IMPLEMENTATION.diff').write_bytes(diff)
    inventory = git('diff', '--name-status', START, IMPLEMENTATION).decode().splitlines()
    assert len(inventory) == 13 and set(r.split('\t')[1] for r in inventory) == set(SOURCES) | set(TESTS) | set(DOCS) | {'src/vde/app.py'}
    (EVIDENCE / 'IMPLEMENTATION_CHANGED_FILES.txt').write_text('\n'.join(inventory) + '\n')
    save('IMPLEMENTATION_IDENTITIES.json', dict(tested_commit=IMPLEMENTATION, tested_tree=tree,
        approved_start=START, main_baseline=MAIN, exact_diff_sha256=digest(diff),
        commits_since_start=git('log', '--format=%H %P %s', START + '..' + IMPLEMENTATION).decode().splitlines()))
    pin = (REPO / 'tests/p4/approved_governance_pin_v1.json').read_bytes()
    assert digest(pin) == '95b7c92a417ec06a80f3d4e839e136e00100e4313d1bee021c94f5beda1f0df7'
    save('GOVERNANCE_UNCHANGED.json',dict(pin_sha256=digest(pin), pin=json.loads(pin), repin=False,
         decisions_sha256=digest((REPO / 'DECISIONS.md').read_bytes()), source_main_unchanged=True))
    save('ENVIRONMENT_PACKAGES.json',dict(python=sys.version,executable=sys.executable,
        packages=sorted([dict(name=d.metadata['Name'],version=d.version) for d in importlib.metadata.distributions()],key=lambda r:r['name'].lower())))
    observations = RUN / 'p6-runtime/observations'
    resource = json.loads((observations / 'T17.json').read_text())
    stress = {}
    for label in ('CSV', 'XLSX', 'negative-expanded-text'):
        raw = json.loads((RUN / 'legacy-p5/observations' / ('stress-' + label + '.json')).read_text())
        assert raw['exit_code'] == 0
        outcome = json.loads(raw['stdout']); assert outcome['result'] == 'PASS'
        if label != 'negative-expanded-text':
            assert outcome['tested_commit'] == IMPLEMENTATION and outcome['tested_tree'] == tree
            assert outcome['independent_cells_checked'] == 20000000
        stress[label] = outcome
    save('STRESS_TEST_RESULTS.json', dict(tested_commit=IMPLEMENTATION, tested_tree=tree,
         outcomes=stress, raw_commands_stdout_stderr='final-run/legacy-p5/observations/stress-*.json'))
    scope = json.loads((observations / 'T18.json').read_text())
    probes = scope['negative_probes']; assert len(probes) >= 23 and all(p['result']=='REJECTED' for p in probes)
    pb = json.loads((observations / 'T06.json').read_text())
    save('CR-P6-002_RUNTIME_WITNESS.json',dict(tested_commit=IMPLEMENTATION,tested_tree=tree,
        proposal_status='PROPOSED_NOT_IMPLEMENTED', protected_path='src/vde/p5/qa.py',
        protected_sha256=digest((REPO / 'src/vde/p5/qa.py').read_bytes()),
        P6_tests=[r for r in rows if r['test_id'] in ('P6-T06','P6-T07')], actual_PB_evidence=pb))
    p0=json.loads((EVIDENCE / 'p0-schemas/P0_SCHEMA_RESULTS.json').read_text())
    assert p0['available_schema_validation']=='PASS' and p0['schemas_checked']==20
    table='\n'.join('| '+r['test_id']+' | '+r['outcome'].upper()+' |' for r in rows)
    p6=summary['p6']; regressions=summary['blocking_behavioral_regressions']
    report=f'''# P6 — implementation validation report

Date: {datetime.now(ZoneInfo('Europe/Moscow')).isoformat()}.

**Outcome: BLOCKED. P6 is not declared VALIDATED. P6 Gate B remains NOT CLOSED. No merge, governance repin, Pilot release or next stage was performed.**

## Exact source and authority

- Branch: `feature/p6-streamlit-e2e`.
- Approved main baseline: `{MAIN}`.
- Approved implementation start: `{START}`.
- **Tested implementation commit: `{IMPLEMENTATION}`.**
- **Tested implementation tree: `{tree}`.**
- Subsequent evidence-only commit and published branch HEAD are recorded separately. No full runtime regression on that descendant is claimed.

The three approved design/decision documents were read completely. The later owner Gate A decision supersedes preserved historical PROPOSED/OPEN headings. CR-P6-001 permits only four P6 runtime files, six P6 test files, two new release documents and exactly four app integration lines. The original three authority/design files remain byte-identical.

P6 implements explicit idempotent DRAFT creation; fresh-health/ownership/P5-backed read-only terminal views; one verified immutable Result and QA snapshot; diagnostic labeling; exact QA JSON MIME/serialization; conservative memory admission and sampling; selection/restart invalidation. Two original independent P3 approval actions are retained. No production auto-Approval or arbitrary generated execution exists.

## Blocking findings

1. **P-B behavioral integration failure, CR-P6-002 PROPOSED.** The frozen P3 UI assigns a UUID Brief. Frozen P5 limits PB-AC-002 recognition to literal `brief-pb-v1`; legally adapted P-B therefore gets DQ-010 FAIL / NEEDS_FIX, although its XLSX contains the correct 18 values. P6-T06/T07 retain their required READY/PASS_WITH_WARNINGS assertions and are real FAILs. This is not a scope conflict. No P5 fix, forced fixture ID, acceptance-criterion change or false READY was applied.
2. **Actual Mac-host Docker smoke NOT RUN.** This machine is Linux and no Mac host was supplied. T19 actually executes Linux launch/restart checks, then remains a real pytest FAIL because required Mac evidence is absent. Linux Docker evidence does not stand in for Mac execution.
3. Any other actual failure or blocking regression remains visible in the raw JUnit and summary; it is not excused by the two findings above.

## Actual mandatory test outcomes

P6: **{p6['passed']} PASS, {p6['failed']} FAIL, {p6['errors']} ERROR, {p6['skipped']} SKIP**, all 20 actual unique IDs. No skip/xfail replacement was used.

| Test ID | Actual pytest outcome |
|---|---|
{table}

| Regression family | Actual outcome and source |
|---|---|
| Historical P1–P4 | Previously executed **212/212 PASS** at `fd39aa1bed480313504ae8b1f76e77e170cb72ba`, cited by exact frozen JUnit checksum. Not rerun or represented as a new P6 result. |
| Historical P5 | Previously executed **76/76 PASS** at `801cc2ba5db46494eaa93e5b963c3bc2f936ddc2`, cited by exact frozen JUnit checksum. |
| Unmodified P1–P4 on tested P6 tree | **{legacy['passed']} PASS, {legacy['expected_historical_scope_conflicts']} real FAIL classified EXPECTED_HISTORICAL_SCOPE_CONFLICT**, {legacy['blocking_regressions']} blocking behavioral regressions; raw exit 1. |
| Unmodified P5 on tested P6 tree | **{summary['legacy_p5']['passed']} PASS, {summary['legacy_p5']['scope_conflicts']} real FAIL classified EXPECTED_HISTORICAL_SCOPE_CONFLICT**, {summary['legacy_p5']['blocking_regressions']} blocking regressions; raw exit {summary['legacy_p5']['pytest_exit']}. |

The P6 successor classifier separately proves the old P2-T01 no-Create-button assertion now contradicted by authorized C01, the prior scope assertions, and the exact child JUnit failures in P3-T50/P4-T63. Raw failures remain FAIL, never PASS/SKIPPED/XFAIL. All unclassified behavioral regressions block; the summary records {regressions} such regressions in legacy suites. P5-T76 rejects the extra approved app integration; the new P6 audit independently proves the finite exception. No combined all-green count is claimed.

## Outputs, resources, corruption and restart

P-A executes the UI-created Order, separate simulated explicit test-user Brief/Spec actions, P4 and P5, and transfers exact 277-byte CSV golden plus the schema-valid QA JSON. P-D executes the corresponding negative route and delivers only a conspicuously named NOT_FOR_DELIVERY diagnostic with QA FAIL / NEEDS_FIX. P-B independently checks all 18 XLSX cells and file hash, but its business QA remains failed; it is delivered only as a diagnostic in this candidate.

HTTP tests use the actual Streamlit media storage and HTTP handler. Response bodies, SHA-256, Content-Length, Content-Disposition and exact CSV/XLSX/QA MIME are independently read back. These are automated isolated test sessions, not owner browser acceptance or live business Approval. A pinned Streamlit compatibility guard buffers widget messages until postbinding RSS succeeds and revokes newly registered media on failure. The injected post-first-registration allocation failure returns HTTP 404 for captured URLs, exposes zero new widgets and changes zero business rows.

The actual generated P5 test artifact used for P6 resource validation is **100000×200**, **{resource['actual_result_bytes']} bytes**, checksum `353698a4bab0ffc54633cb3fabad7eb404821b5f97dfeb7eb9676dafec4d9239`. It is copied from an existing isolated generated P5 test workspace, not an owner workspace or a replacement P0 fixture. Actual P6 RSS (including HTTP server/client transfer in the test process) is recorded in T17: **{resource['P6_resources']['incremental_peak_rss']} incremental bytes**, limit **536870912**. Admission accounts for at least 3×Result + serialized QA +64MiB. Both ordinary transfer and tightened-budget/fault denial execute; no refusal is substituted for the successful admitted workload.

The unchanged P5-T72 also actually reruns both approved **100000×200** export workloads on this same implementation tree, with **20000000 independently checked cells per format**:

| Format | Actual result | P5 elapsed seconds | Sampled incremental peak RSS bytes |
|---|---|---|---|
| CSV | PASS | {stress['CSV']['P5_elapsed_seconds']} | {stress['CSV']['incremental_peak_rss_bytes']} |
| XLSX | PASS | {stress['XLSX']['P5_elapsed_seconds']} | {stress['XLSX']['incremental_peak_rss_bytes']} |

The separate expanded-text 100000×200 negative workload has **{stress['negative-expanded-text']['P4_internal_bytes']} P4 internal bytes** and is safely rejected with EXPORT_FAILED, zero new final Artifacts and zero QAReports. Original P4 bytes remain unchanged. Its refusal is not counted as either positive workload. Full worker argv, stdout/stderr, exits, exact cells, input/output hashes and resource samples are retained in `STRESS_TEST_RESULTS.json` and the raw observations.

Corruption checks mutate disposable workspace copies only: source CSV/XLSX, P4 internal/final bytes, approval/hash/context, missing report, altered metadata and degraded/orphan states fail closed. Cross-Order rejection occurs before artifact bytes. Three-plus passive renders, repeat prepare/transfer and restart preserve persisted records/checksums and create no automatic Approval/Run/Artifact/Event. Prepared copies are verified immutable snapshots; the final browser click is not a fresh disk reread. Sampled RSS is not hard OS isolation.

Linux native smoke launches/restarts the app and checks health 200. Clean **Linux-host Docker** smoke at the exact tested commit installs the unchanged lock in an ephemeral writable copy of a read-only source mount, uses the same persistent writable workspace, runs P-A, transfers Result/QA, destroys/recreates the container and verifies byte/row persistence and fresh-session reprepare. Commands, stdout/stderr, versions and actual image digest are preserved. Mac-host execution remains NOT RUN.

## Schema, source preservation and evidence

Actual P0 validation: **20 schemas, {p0['positive_validations']} positive schema applications PASS**, {p0['manifest_present_matches']}/{p0['manifest_declared_count']} original manifest files present and matching. Thirteen P-C originals remain absent; full P-C positive coverage is not claimed. Available negative schema/semantic guards remain in unchanged executed historical suites and P6 corruption cases.

The successor source audit passes, including a clean extracted positive control and **{len(probes)}/{len(probes)} rejected mutations**. Protected classes include P1–P5 source, historical tests/policies/evidence, schema, fixture, dependency/lock, migration, governance/pin, authority record, extra path, new owned source/policy and file mode. `PROTECTED_FILES_BEFORE_AFTER.json` independently records all {len(protected)} owner-start files: {len(protected)-1} unchanged and the exact four-line app edit. Thirteen implementation changed paths comprise 12 permitted additions and that one modification. No historical contract/test/fixture/schema/migration/dependency/governance/evidence bytes are changed; temporary generated old-test outputs are captured and restored exactly after every phase.

Full commands, versions, exits, stdout/stderr, JUnit, test-ID inventory, observations, protected-file hashes, exact diff, CR proposal and a finite SHA-256 manifest are included. The evidence-only descendant is checked for byte/scope identity without claiming a full new runtime run.

Earlier uncommitted development diagnostics and candidate `9838151ca50e10976c85d087fe17ec0d30ae2fea` are separate. Its old-suite run was 205 PASS / 7 FAIL; a P5-only nested-failure classifier then stopped because it expected only the six pre-P6 scope cases. Only the new P6 runner was corrected to prove the authorized CreateOrder assertion and nested cascades; historical tests/assertions were not changed. Earlier failed attempts are not retroactively labeled successful.

**Handoff: BLOCKED pending owner decision on CR-P6-002, the required actual Mac Docker smoke and resolution of every remaining blocking failure. No P6 VALIDATED, Gate B closure, merge or Pilot release is asserted.**
'''
    (EVIDENCE / 'P6_VALIDATION_REPORT.md').write_text(report)
    files=sorted(p.relative_to(REPO).as_posix() for p in EVIDENCE.rglob('*') if p.is_file())
    inventory_path=(EVIDENCE/'EVIDENCE_FILES.txt').relative_to(REPO).as_posix()
    manifest_path=(EVIDENCE/'MANIFEST.sha256').relative_to(REPO).as_posix()
    files=sorted(set(files+[inventory_path,manifest_path]))
    (REPO/inventory_path).write_text(''.join(p+'\n' for p in files))
    (REPO/manifest_path).write_text(''.join(digest((REPO/p).read_bytes())+'  '+p+'\n' for p in files if p!=manifest_path))
    print(json.dumps(dict(files=len(files),manifest_entries=len(files)-1,manifest_sha256=digest((REPO/manifest_path).read_bytes()),tested_commit=IMPLEMENTATION,status='BLOCKED'),indent=2))


if __name__=='__main__':
    main()
