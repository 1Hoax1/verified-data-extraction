"""CR-P4-001 whole-application inventory with frozen baselines and negatives."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import tomllib

POLICY = Path(__file__).with_name('scope_allowlist_v1.json')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def audit_snippet(text):
    tree = ast.parse(text)
    denied = ('requests', 'httpx', 'socket', 'openai', 'telegram', 'playwright', 'celery',
              'fastapi', 'pandas', 'sqlalchemy', 'subprocess', 'threading', 'multiprocessing',
              'urllib.request', 'http.client', 'importlib')
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(not any(a.name == d or a.name.startswith(d+'.') for d in denied) for a in node.names), 'Unapproved import'
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            assert not any(module == d or module.startswith(d+'.') for d in denied), 'Unapproved import'
        elif isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            assert name not in {'eval', 'exec', 'compile', '__import__'} and not name.endswith(('.save', '.to_csv', '.to_excel', '.reports.append')), 'Unapproved invocation'


def frozen_baseline(root, *, authority_root=None):
    policy = json.loads(POLICY.read_text())
    from scope_policy import GOVERNANCE_PIN, GOVERNANCE_PIN_SHA256, verify_governance_document
    assert policy['governance_pin'] == {'path': GOVERNANCE_PIN, 'sha256': GOVERNANCE_PIN_SHA256}, 'Unapproved governance pin policy'
    verify_governance_document(root, authority_root=authority_root)
    for path, expected in policy['frozen_sha256'].items():
        if path == 'DECISIONS.md':
            # Retain its original baseline hash; only the separately proved
            # owner-approved version may replace it on integrated history.
            assert expected == 'b3f20206fc7a8344e5cb16136d664153a8e5b552797e49567867ebfb967cf780'
            continue
        assert digest((root/path).read_bytes()) == expected, 'Unapproved frozen runtime/contract drift: '+path


def audit_p4(root, *, authority_root=None):
    policy = json.loads(POLICY.read_text())
    frozen_baseline(root, authority_root=authority_root)
    actual = {p.relative_to(root).as_posix() for p in (root/'src').rglob('*') if p.is_file()
              and '__pycache__' not in p.parts and not any(n.endswith('.egg-info') for n in p.parts)}
    assert actual == set(policy['source_sha256']), 'Unapproved full application paths'
    for path, expected in policy['source_sha256'].items():
        assert digest((root/path).read_bytes()) == expected, 'Unapproved application source: '+path
    for path in policy['p4_source_paths']:
        audit_snippet((root/path).read_text())
    assert digest((root/'uv.lock').read_bytes()) == policy['lock_sha256'], 'Unapproved lock dependency drift'
    project = tomllib.loads((root/'pyproject.toml').read_text())
    assert project == policy['pyproject'], 'Unapproved project/dependency/test configuration'
    from vde.workflow.validation import OPERATIONS
    assert OPERATIONS == frozenset(('rename','select_columns','drop_columns','trim','change_case','replace',
                                   'parse_number','parse_date','fill_missing','drop_missing','deduplicate','sort'))


def negative_repository_probes(root, tmp_path):
    import pytest
    scratch = tmp_path/'whole-app'
    shutil.copytree(root/'src', scratch/'src', ignore=shutil.ignore_patterns('__pycache__','*.egg-info'))
    policy = json.loads(POLICY.read_text())
    # Copy exactly the protected inputs needed by the same complete audit.
    for name in set(policy['frozen_sha256']) | {'pyproject.toml','uv.lock'}:
        if name.startswith('src/'):
            continue
        target = scratch/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root/name, target)
    audit_p4(scratch, authority_root=root)
    for name, contents in [('src/vde/execution/worker.py','import celery'),
                           ('src/vde/p5.py','def export(): pass'),
                           ('src/vde/persistence/migrations/002_p4.sql','CREATE TABLE rows(id);')]:
        target = scratch/name
        target.write_text(contents)
        with pytest.raises(AssertionError):
            audit_p4(scratch, authority_root=root)
        target.unlink()
    for name in ('src/vde/workflow/service.py','src/vde/storage.py',
                 'src/vde/persistence/migrations/001_p1_baseline.sql','src/vde/execution/engine.py'):
        target = scratch/name
        original = target.read_bytes()
        target.write_bytes(original+b'\n# unapproved drift\n')
        with pytest.raises(AssertionError):
            audit_p4(scratch, authority_root=root)
        target.write_bytes(original)
    target = scratch/'pyproject.toml'
    original = target.read_text()
    target.write_text(original.replace('"openpyxl==3.1.5"','"openpyxl==3.1.5", "sqlalchemy==2.0.0"'))
    with pytest.raises(AssertionError):
        audit_p4(scratch, authority_root=root)
    target.write_text(original)


def governance_repository_probes(root, tmp_path, monkeypatch):
    """P01-P05/N01-N14; mutations use isolated real Git history, never root."""
    import subprocess
    import unicodedata
    import pytest
    import scope_policy as scope
    results, commands = {}, []

    def run(directory, *args, input=None):
        argv = ['git', '-c', 'user.name=P4 test fixture', '-c', 'user.email=p4-fixture@example.invalid', *args]
        proc = subprocess.run(argv, cwd=directory, input=input, capture_output=True)
        commands.append({'argv': argv, 'cwd': str(directory), 'exit_code': proc.returncode,
                         'stdout': proc.stdout.decode(errors='replace'), 'stderr': proc.stderr.decode(errors='replace')})
        assert proc.returncode == 0, proc.stderr.decode(errors='replace')
        return proc.stdout

    def passed(identity, detail, count=1, enforcement='executed assertion'):
        results[identity] = {'result': 'PASS', 'detail': detail, 'subcases': count, 'enforcement': enforcement}

    def rejected(action):
        with pytest.raises(AssertionError, match='Unapproved'):
            action()

    pin = scope.verify_governance_document(root)
    frozen_baseline(root)
    passed('P01', 'Real integrated HEAD/index/disk and exact G/B/H/L/M/P verified by both auditors')
    changed = run(root, 'diff', '--name-only', scope.GOVERNANCE_BASELINE).decode().splitlines()
    untracked = run(root, 'ls-files', '--others', '--exclude-standard').decode().splitlines()
    scope.audit_repository_paths(changed + untracked, root=root)
    passed('P02', 'Full real changed/untracked inventory; original P2-T40/P3-T51 also run separately and in combined suite')
    copied = tmp_path / 'whole-app'
    audit_p4(copied, authority_root=root)
    passed('P03', 'Full clean copied tree passes with explicitly verified real authority')

    repo = tmp_path / 'governance-git'
    run(tmp_path, 'clone', '--shared', '--no-checkout', '--quiet', str(root), str(repo))
    start = run(root, 'rev-parse', 'HEAD').decode().strip()
    run(repo, 'switch', '--detach', '--quiet', start)
    document = repo / 'DECISIONS.md'
    pin_path = repo / scope.GOVERNANCE_PIN
    original, original_pin = document.read_bytes(), pin_path.read_bytes()

    def restore():
        # This path is a disposable clone under pytest tmp storage only.
        assert repo.parent == tmp_path and repo != root
        run(repo, 'restore', '--source=' + start, '--staged', '--worktree', '--', 'DECISIONS.md', scope.GOVERNANCE_PIN)
        run(repo, 'switch', '--detach', '--quiet', start)
        document.chmod(0o644)
        assert document.read_bytes() == original and pin_path.read_bytes() == original_pin
        scope.verify_governance_document(repo)

    def commit_document(raw):
        document.write_bytes(raw)
        run(repo, 'add', '--', 'DECISIONS.md')
        run(repo, 'commit', '--quiet', '-m', 'Synthetic governance probe, not owner approval')
        return run(repo, 'rev-parse', 'HEAD').decode().strip()

    # A descendant evidence-only commit does not rotate the approved document.
    extra = repo / 'docs/p4/validation/probe-evidence.txt'
    extra.write_text('test-only descendant\n')
    run(repo, 'add', '--', str(extra.relative_to(repo)))
    run(repo, 'commit', '--quiet', '-m', 'Synthetic evidence-only descendant')
    scope.verify_governance_document(repo)
    passed('P04', 'Descendant evidence-only commit passes without repin')
    restore()

    rejected(lambda: scope.audit_repository_paths(['DECISIONS.md']))
    passed('N01', 'Unchanged no-context singleton rejection; both historical assertions remain', 2)
    variants = [original + b' ', original[:-1], original.replace(b'\n', b'\r\n'),
                original + 'é'.encode(), original + unicodedata.normalize('NFD', 'é').encode()]
    assert all(raw != original for raw in variants)
    for raw in variants:
        document.write_bytes(raw)
        rejected(lambda: scope.verify_governance_document(repo))
    restore()
    passed('N02', 'Byte addition/removal, CRLF and Unicode normalization each rejected', len(variants))

    document.write_bytes(original + b'\n')
    run(repo, 'add', '--', 'DECISIONS.md')
    document.write_bytes(original)
    rejected(lambda: scope.verify_governance_document(repo))
    restore()
    document.write_bytes(original + b'\n')
    rejected(lambda: scope.verify_governance_document(repo))
    restore()
    commit_document(original + b'\n')
    run(repo, 'restore', '--source=' + start, '--staged', '--worktree', '--', 'DECISIONS.md')
    rejected(lambda: scope.verify_governance_document(repo))
    restore()
    passed('N03', 'Staged-only, unstaged-only, and changed HEAD with approved index/disk each rejected', 3)

    document.unlink()
    rejected(lambda: scope.verify_governance_document(repo))
    target = repo / 'document-target.txt'
    target.write_bytes(original)
    document.symlink_to(target)
    rejected(lambda: scope.verify_governance_document(repo))
    document.unlink()
    document.write_bytes(original)
    document.chmod(0o755)
    rejected(lambda: scope.verify_governance_document(repo))
    document.chmod(0o644)
    conflict = ''.join(f"100644 {pin['decisions_blob']} {stage}\tDECISIONS.md\n" for stage in (1, 2, 3)).encode()
    run(repo, 'update-index', '--index-info', input=b'0 ' + b'0' * 40 + b'\tDECISIONS.md\n' + conflict)
    rejected(lambda: scope.verify_governance_document(repo))
    restore()
    passed('N04', 'Missing file, symlink, executable mode, conflicting index stages each rejected', 4)

    for revision in (scope.PRIOR_OWNER_APPROVAL, scope.GOVERNANCE_BASELINE):
        document.write_bytes(run(repo, 'cat-file', 'blob', revision + ':DECISIONS.md'))
        rejected(lambda: scope.verify_governance_document(repo))
    restore()
    passed('N05', 'Both obsolete approved/baseline document versions rejected', 2)

    run(repo, 'switch', '--detach', '--quiet', scope.GOVERNANCE_BASELINE)
    pin_path.parent.mkdir(parents=True, exist_ok=True)
    pin_path.write_bytes(original_pin)
    document.write_bytes(original)
    rejected(lambda: scope.verify_governance_document(repo))
    pin_path.unlink()
    restore()
    run(repo, 'replace', pin['approval_commit'], scope.PRIOR_OWNER_APPROVAL)
    rejected(lambda: scope.verify_governance_document(repo))
    run(repo, 'replace', '-d', pin['approval_commit'])
    shallow = repo / '.git/shallow'
    shallow.write_text(start + '\n')
    rejected(lambda: scope.verify_governance_document(repo))
    shallow.unlink()
    missing = dict(pin, approval_commit='0' * 40)
    raw = (json.dumps(missing, sort_keys=True, indent=2) + '\n').encode()
    pin_path.write_bytes(raw)
    with monkeypatch.context() as patch:
        patch.setattr(scope, 'GOVERNANCE_PIN_SHA256', digest(raw))
        rejected(lambda: scope.verify_governance_document(repo))
    restore()
    passed('N06', 'Missing ancestry, replace ref, shallow history, unknown authority object rejected', 4)

    malformed = [dict(pin, path='*'), dict(pin, implementation_baseline='0' * 40),
                 dict(pin, decisions_size_bytes=True), dict(pin, decisions_sha256=['0' * 64]),
                 dict(pin, approval_commit='<G>'), dict(pin, git_mode='100755'),
                 dict(pin, extra='unapproved')]
    raws = [(json.dumps(value, sort_keys=True, indent=2) + '\n').encode() for value in malformed]
    raws += [original_pin.replace(b'{', b'{"path":"DECISIONS.md",', 1), original_pin + b' ']
    for raw in raws:
        pin_path.write_bytes(raw)
        rejected(lambda: scope.load_governance_pin(repo))
        # Independently exercise the closed parser beyond the outer digest.
        with monkeypatch.context() as patch:
            patch.setattr(scope, 'GOVERNANCE_PIN_SHA256', digest(raw))
            rejected(lambda: scope.load_governance_pin(repo))
    restore()
    passed('N07', 'Digest and closed-schema/serialization negatives both exercised', len(raws) * 2)

    second = commit_document(original + b'\n# Synthetic future decision fixture only\n')
    second_pin = dict(pin, approval_commit=second,
                      decisions_blob=run(repo, 'rev-parse', 'HEAD:DECISIONS.md').decode().strip(),
                      decisions_sha256=digest(document.read_bytes()), decisions_size_bytes=document.stat().st_size)
    second_raw = (json.dumps(second_pin, sort_keys=True, indent=2) + '\n').encode()
    pin_path.write_bytes(second_raw)
    rejected(lambda: scope.verify_governance_document(repo))
    passed('N08', 'Recomputed arbitrary document/pin still fails the original expected P')

    receipt = json.loads((root / 'docs/p4/validation/cr-p4-005/STAGE_A_APPROVAL_RECEIPT.json').read_bytes())
    with pytest.raises(AssertionError):
        assert all(second_pin[key] == receipt[key] for key in ('approval_commit', 'decisions_blob', 'decisions_sha256', 'decisions_size_bytes', 'git_mode'))
    passed('N09', 'Changed pin/P requires independent owner receipt; synthetic alternative mismatches actual receipt',
           enforcement='executed independent receipt comparison; human authorization remains a review boundary')
    restore()

    rejected(lambda: scope.audit_repository_paths(['DECISIONS.md', 'worker.py'], root=repo))
    passed('N10', 'Approved document never authorizes a forbidden neighboring path')
    pin_path.unlink()
    rejected(lambda: scope.verify_governance_document(repo))
    restore()
    rejected(lambda: scope.verify_governance_document(copied))
    rejected(lambda: scope.verify_governance_document(copied, authority_root=copied))
    copied_document = copied / 'DECISIONS.md'
    copied_document.write_bytes(original + b' ')
    rejected(lambda: scope.verify_governance_document(copied, authority_root=root))
    copied_document.write_bytes(original)
    passed('N11', 'Missing pin/authority and modified scratch bytes rejected, with no historical fallback', 4)

    audit_p4(copied, authority_root=root)
    protected = ['src/vde/storage.py', 'src/vde/execution/engine.py',
                 'src/vde/persistence/migrations/001_p1_baseline.sql',
                 'pecs/pilot_slice_v1/contracts/approval.schema.json',
                 'docs/p4/v1.0/P4_Implementation_Pack_v1.0_APPROVED.zip', 'uv.lock']
    for name in protected:
        file = copied / name
        previous = file.read_bytes()
        file.write_bytes(previous + b'\n# unauthorized drift\n')
        rejected(lambda: audit_p4(copied, authority_root=root))
        file.write_bytes(previous)
    passed('N12', 'Frozen legacy/P4 sources, migration, P0 schema, pack and dependency lock all reject mutation; historical snippets also retained', len(protected))

    second = commit_document(original + '\n# Simulated approved G2 café in isolated test fixture only\n'.encode())
    rejected(lambda: scope.verify_governance_document(repo))
    passed('N13', 'New descendant document is rejected until explicitly repinned; only one active version')
    candidate = dict(pin, approval_commit=second,
                     decisions_blob=run(repo, 'rev-parse', 'HEAD:DECISIONS.md').decode().strip(),
                     decisions_sha256=digest(document.read_bytes()), decisions_size_bytes=document.stat().st_size)
    candidate_raw = (json.dumps(candidate, sort_keys=True, indent=2) + '\n').encode()
    pin_path.write_bytes(candidate_raw)
    policy = json.loads(POLICY.read_bytes())
    policy['governance_pin']['sha256'] = digest(candidate_raw)
    candidate_policy = tmp_path / 'simulated-repin-policy.json'
    candidate_policy.write_text(json.dumps(policy))
    import sys
    with monkeypatch.context() as patch:
        patch.setattr(scope, 'GOVERNANCE_PIN_SHA256', digest(candidate_raw))
        patch.setattr(sys.modules[__name__], 'POLICY', candidate_policy)
        scope.verify_governance_document(repo)
        audit_p4(repo)
        # The real approved document has no decomposable codepoints. Use the
        # scoped G2 fixture to prove equivalent Unicode spelling still fails.
        normalized = unicodedata.normalize('NFD', document.read_text()).encode()
        assert normalized != document.read_bytes()
        document.write_bytes(normalized)
        rejected(lambda: scope.verify_governance_document(repo))
        document.write_bytes(original)
        rejected(lambda: scope.verify_governance_document(repo))
    restore()
    passed('P05', 'Future-repin mechanics tested using isolated synthetic receipt/authority; real owner approval is not fabricated',
           enforcement='test-only simulation of the external approval boundary; real active pin unchanged')

    for name in ('tests/p2/test_p2.py', 'tests/p3/test_p3.py'):
        file = copied / name
        previous = file.read_bytes()
        file.write_bytes(previous + b'\n# unauthorized test change\n')
        rejected(lambda: frozen_baseline(copied, authority_root=root))
        file.write_bytes(previous)
    passed('N14', 'Both frozen historical test files reject any bytes beyond the exact approved amendment', 2)
    assert set(results) == {f'P{i:02}' for i in range(1, 6)} | {f'N{i:02}' for i in range(1, 15)}
    assert scope.verify_governance_document(root) == pin
    output = root / 'docs/p4/validation/cr-p4-005/governance-results.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'tested_commit': start, 'cases': results, 'commands': commands}, indent=2) + '\n')
