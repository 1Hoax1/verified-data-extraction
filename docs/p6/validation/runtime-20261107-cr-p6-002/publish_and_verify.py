"""Publish the BLOCKED P6 review candidate and verify independently fetched objects."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys

REPO = Path('/workspace/p6-streamlit-e2e')
WORK = Path('/workspace/p6-cr2-work')
OUT = WORK / 'publication'
BARE = WORK / 'published.git'
BRANCH = 'feature/p6-streamlit-e2e'
MAIN = '0af4a1ff49ccf8fa59c39780d749e15cb5042fc3'
OWNER = '66c2b4f97e2b4dbe4e7a01696c89ae5fd0431981'
PREFIX = 'docs/p6/validation/runtime-20261107-cr-p6-002/'
AUTH = ['-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential']


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def run(label, argv, cwd=REPO):
    started = datetime.now(timezone.utc).isoformat()
    r = subprocess.run(argv, cwd=cwd, capture_output=True)
    (OUT / (label + '.stdout')).write_bytes(r.stdout)
    (OUT / (label + '.stderr')).write_bytes(r.stderr)
    save(label + '.command.json', dict(command=argv, cwd=str(cwd),
         started_at_utc=started, finished_at_utc=datetime.now(timezone.utc).isoformat(),
         exit_code=r.returncode))
    assert r.returncode == 0, (label, r.returncode, r.stderr.decode(errors='replace'))
    return r.stdout


def git(*args, cwd=REPO):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=cwd)


def ref(label, branch):
    raw = run(label, ['gh', 'api', 'repos/1Hoax1/verified-data-extraction/git/ref/heads/' + branch])
    return json.loads(raw)['object']['sha']


def paginated_commit(label, commit):
    raw = run(label, ['gh', 'api', '--paginate',
              'repos/1Hoax1/verified-data-extraction/commits/' + commit + '?per_page=100'])
    source = raw.decode(); decoder = json.JSONDecoder(); records = []
    while source.strip():
        rec, end = decoder.raw_decode(source.lstrip()); records.append(rec)
        source = source.lstrip()[end:]
    assert records and all(r['sha'] == commit for r in records)
    files = [f for rec in records for f in rec.get('files', [])]
    assert len(files) == len({f['filename'] for f in files})
    return records[0], files


def main():
    OUT.mkdir(exist_ok=True)
    assert not git('status', '--porcelain').strip()
    summary = json.loads((REPO / PREFIX / 'final-run/VALIDATION_SUMMARY.json').read_text())
    assert summary['status'] == 'BLOCKED' and summary['p6']['total'] == 20
    assert summary['correction_start'] == OWNER
    assert summary['scope_policy_format'] == 'P6_SCOPE_POLICY_V2_CR_P6_002'
    assert summary['approved_p5_qa_sha256'] == '8caee87fce7a0c748e2333b8fe3b1b3333fee3548ee78111516a8eac541d8a52'
    assert summary['legacy_p1_p4']['total'] == 212 and summary['legacy_p5']['total'] == 76
    implementation = summary['tested_commit']
    evidence = git('rev-parse', 'HEAD').decode().strip()
    assert git('branch', '--show-current').decode().strip() == BRANCH
    assert git('rev-list', '--parents', '-n', '1', evidence).decode().split() == [evidence, implementation]
    assert git('rev-parse', implementation + '^{tree}').decode().strip() == summary['tested_tree']
    git('merge-base', '--is-ancestor', OWNER, implementation)
    changes = [line.split('\t') for line in git('diff', '--name-status', implementation, evidence).decode().splitlines()]
    assert changes and all(status == 'A' and path.startswith(PREFIX) for status, path in changes)
    assert ref('main-immediate-before', 'main') == MAIN
    assert ref('feature-immediate-before', BRANCH) == OWNER
    run('push-feature-only', ['git', *AUTH, 'push', 'origin', 'HEAD:refs/heads/' + BRANCH])
    assert not BARE.exists()
    run('bare-init', ['git', 'init', '--bare', str(BARE)])
    run('independent-fetch', ['git', *AUTH, '-C', str(BARE), 'fetch', '--no-tags',
         'https://github.com/1Hoax1/verified-data-extraction.git',
         '+refs/heads/' + BRANCH + ':refs/remotes/github/' + BRANCH,
         '+refs/heads/main:refs/remotes/github/main'])
    assert git('rev-parse', 'refs/remotes/github/' + BRANCH, cwd=BARE).decode().strip() == evidence
    assert git('rev-parse', 'refs/remotes/github/main', cwd=BARE).decode().strip() == MAIN
    assert git('cat-file', '-p', evidence, cwd=BARE) == git('cat-file', '-p', evidence)
    assert git('cat-file', '-p', implementation, cwd=BARE) == git('cat-file', '-p', implementation)
    git('merge-base', '--is-ancestor', OWNER, evidence, cwd=BARE)
    git('merge-base', '--is-ancestor', implementation, evidence, cwd=BARE)
    actual_changes = git('diff', '--name-status', implementation, evidence, cwd=BARE)
    assert actual_changes == git('diff', '--name-status', implementation, evidence)
    (OUT / 'PUBLISHED_EVIDENCE_CHANGED_FILES.txt').write_bytes(actual_changes)
    entries = {}
    for item in git('ls-tree', '-rz', '--full-tree', evidence, cwd=BARE).split(b'\0'):
        if not item:
            continue
        obj, path = item.decode().split('\t'); mode, kind, blob = obj.split()
        assert kind == 'blob'
        entries[path] = (mode, blob)
    checked = []
    for path in git('ls-files').decode().splitlines():
        actual = (REPO / path).read_bytes()
        mode, blob = entries[path]
        published = git('cat-file', 'blob', blob, cwd=BARE)
        assert published == actual, path
        assert hashlib.sha1(b'blob ' + str(len(actual)).encode() + b'\0' + actual).hexdigest() == blob
        checked.append(dict(path=path, mode=mode, blob=blob, size=len(actual), sha256=hashlib.sha256(actual).hexdigest()))
    save('PUBLISHED_ALL_TRACKED_BYTES.json', dict(result='PASS', files=len(checked), records=checked))
    manifest_path = PREFIX + 'MANIFEST.sha256'
    manifest = git('show', evidence + ':' + manifest_path, cwd=BARE)
    manifest_count = 0
    for row in manifest.decode().splitlines():
        expected, path = row.split('  ', 1)
        assert hashlib.sha256(git('show', evidence + ':' + path, cwd=BARE)).hexdigest() == expected, path
        manifest_count += 1
    assert set(p for _, p in changes) == {p for p in entries if p.startswith(PREFIX)}
    for label, commit in [('implementation-api', implementation), ('evidence-api', evidence)]:
        record, files = paginated_commit(label, commit)
        assert record['commit']['tree']['sha'] == git('rev-parse', commit + '^{tree}', cwd=BARE).decode().strip()
        assert [p['sha'] for p in record['parents']] == git('rev-list', '--parents', '-n', '1', commit, cwd=BARE).decode().split()[1:]
        if label == 'evidence-api':
            assert len(files) == len(changes)
            assert {f['filename'] for f in files} == {p for _, p in changes}
            assert all(f['status'] == 'added' and f['sha'] == entries[f['filename']][1] for f in files)
    assert ref('feature-after', BRANCH) == evidence
    assert ref('main-after', 'main') == MAIN
    assert not git('status', '--porcelain').strip()
    run('independent-fsck', ['git', '-C', str(BARE), 'fsck', '--strict', '--no-dangling'])
    result = dict(result='PASS', branch_url='https://github.com/1Hoax1/verified-data-extraction/tree/' + BRANCH,
         tested_implementation_commit=implementation, tested_implementation_tree=summary['tested_tree'],
         evidence_commit=evidence, evidence_parent=implementation, evidence_tree=git('rev-parse', evidence+'^{tree}', cwd=BARE).decode().strip(),
         evidence_added_files=len(changes), evidence_manifest_passes=manifest_count,
         evidence_manifest_sha256=hashlib.sha256(manifest).hexdigest(), independently_checked_files=len(checked),
         remote_main_before=MAIN, remote_main_after=MAIN, main_unchanged=True,
         source_and_tests_same_as_tested_implementation=True, complete_runtime_rerun_on_evidence_commit=False,
         source_scope='Exactly seven authorized existing-file amendments relative to CR-P6-002 owner commit; previous P6 runtime/app and historical evidence unchanged',
         governance_repin=False, merge=False, gate_b_closed=False, P6_implemented=True, next_stage_started=False, validation_status=summary['status'],
         verified_at_utc=datetime.now(timezone.utc).isoformat())
    save('PUBLICATION_VERIFICATION_REPORT.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
