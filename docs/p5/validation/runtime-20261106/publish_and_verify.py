"""Publish the validated P5 evidence descendant; verify independently fetched objects."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys

REPO = Path('/workspace/p5-export-deterministic-qa')
WORK = Path('/workspace/p5-resume-work')
OUT = WORK / 'publication'
BARE = WORK / 'published.git'
BRANCH = 'feature/p5-export-deterministic-qa'
MAIN = 'fd39aa1bed480313504ae8b1f76e77e170cb72ba'
OWNER = '820245fc544fc66c393db548151e6d281e03d414'
PREFIX = 'docs/p5/validation/runtime-20261106/'
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
    assert summary['technical_validation_success']
    implementation = summary['tested_implementation_commit']
    evidence = git('rev-parse', 'HEAD').decode().strip()
    assert git('branch', '--show-current').decode().strip() == BRANCH
    assert git('rev-list', '--parents', '-n', '1', evidence).decode().split() == [evidence, implementation]
    assert git('rev-parse', implementation + '^{tree}').decode().strip() == summary['tested_implementation_tree']
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
         tested_implementation_commit=implementation, tested_implementation_tree=summary['tested_implementation_tree'],
         evidence_commit=evidence, evidence_parent=implementation, evidence_tree=git('rev-parse', evidence+'^{tree}', cwd=BARE).decode().strip(),
         evidence_added_files=len(changes), evidence_manifest_passes=manifest_count,
         evidence_manifest_sha256=hashlib.sha256(manifest).hexdigest(), independently_checked_files=len(checked),
         remote_main_before=MAIN, remote_main_after=MAIN, main_unchanged=True,
         source_and_tests_same_as_tested_implementation=True, complete_runtime_rerun_on_evidence_commit=False,
         source_scope='23 new P5-owned paths and exact two-line app append relative to owner start',
         governance_repin=False, merge=False, gate_b_closed=False, P6_started=False,
         verified_at_utc=datetime.now(timezone.utc).isoformat())
    save('PUBLICATION_VERIFICATION_REPORT.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
