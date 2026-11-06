"""Version 2: CR-P6-001 plus the exact CR-P6-002 QA/source exception.

The original V1 policy/audit remain immutable at PREDECESSOR and in its
published evidence. They are historical evidence, never this active policy.
"""
import ast
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile

BASELINE = '0af4a1ff49ccf8fa59c39780d749e15cb5042fc3'
START = 'b93e0ef4ed69343968ff7ae4188d586c0d1485a5'
CORRECTION_START = '66c2b4f97e2b4dbe4e7a01696c89ae5fd0431981'
PREDECESSOR = 'deddc2799464076227173bd2e4890f552ffe64bf'
OWNER_RECORD = 'docs/p6/decisions/CR-P6-002_OWNER_DECISION_2026-11-07.md'
OWNER_SHA256 = 'ad91837ed5b9b45c6dfe24c9783089e19d7d2c14fc0f67fb766229e9be5d9339'
P5_QA = 'src/vde/p5/qa.py'
P5_QA_SHA256 = '8caee87fce7a0c748e2333b8fe3b1b3333fee3548ee78111516a8eac541d8a52'
EVIDENCE_ROOT = 'docs/p6/validation/runtime-20261107-cr-p6-002/'
RETIRED = {
    'tests/p6/scope_policy_v1.json': '0b90083e30783bed6a5420dc7faed7127071b0c2d0023073bf8bb87bbad08207',
    'tests/p6/scope_audit.py': 'a682ed6e27ea901495ca782d7ff7cb0ddb025f16b3f1da20914a717b39d1d050',
    'tests/p6/run_validation.py': '3c74becbb6090a1c59844fe25d047bf4194a25368cd2975d0e3a4553b9d484ad',
}
SOURCES = tuple('src/vde/p6/' + p for p in ('__init__.py', 'orders.py', 'delivery.py', 'ui.py'))
TESTS = tuple('tests/p6/' + p for p in ('__init__.py', 'conftest.py', 'test_acceptance.py', 'scope_audit.py', 'scope_policy_v1.json', 'run_validation.py'))
DOCS = ('docs/p6/README_PILOT.md', 'docs/p6/RELEASE_CHECKLIST.md')
BEFORE = b'from vde.p6.ui import order_panel\norder_panel(result)\n'
AFTER = b'from vde.p6.ui import delivery_panel\ndelivery_panel(result)\n'
AMENDED = (P5_QA, 'tests/p6/test_acceptance.py', 'tests/p6/scope_audit.py',
           'tests/p6/scope_policy_v1.json', 'tests/p6/run_validation.py', *DOCS)
POLICY = dict(format='P6_SCOPE_POLICY_V2_CR_P6_002', baseline=BASELINE, implementation_start=START,
              source_paths=list(SOURCES), test_paths=list(TESTS), release_paths=list(DOCS),
              app_insert_before_ingestion=BEFORE.decode(), app_append=AFTER.decode(),
              correction_start=CORRECTION_START, owner_record=OWNER_RECORD, owner_sha256=OWNER_SHA256,
              amended_paths=list(AMENDED), p5_qa_path=P5_QA, p5_qa_sha256=P5_QA_SHA256,
              predecessor_commit=PREDECESSOR, retired_policy_audit_sha256=RETIRED,
              evidence_root=EVIDENCE_ROOT)


def git(root, *args):
    return subprocess.check_output(['git', '--no-replace-objects', '-C', str(root), *args], stderr=subprocess.PIPE)


@lru_cache(maxsize=4)
def frozen(root, ref):
    result = {}
    for item in git(root, 'ls-tree', '-rz', '--full-tree', ref).split(b'\0'):
        if not item:
            continue
        header, path = item.decode().split('\t'); mode, kind, blob = header.split()
        assert kind == 'blob'
        result[path] = (mode, blob, git(root, 'cat-file', 'blob', blob))
    return result


def regular(path, mode='100644'):
    found = path.lstat().st_mode
    assert stat.S_ISREG(found), 'File type changed: ' + str(path)
    assert bool(found & 0o111) == (mode == '100755'), 'File mode changed: ' + str(path)
    return path.read_bytes()


def expected_app(raw):
    needle = b'from vde.ingestion.ui import panel\n'
    assert raw.count(needle) == 1 and raw.endswith(b'export_qa_panel(result)\n')
    return raw.replace(needle, BEFORE + needle, 1) + AFTER


def audit(root, *, authority_root=None):
    root = Path(root).resolve(); authority = Path(authority_root).resolve() if authority_root else root
    assert json.loads(regular(root / 'tests/p6/scope_policy_v1.json')) == POLICY, 'P6 policy changed'
    git(authority, 'merge-base', '--is-ancestor', BASELINE, 'HEAD')
    git(authority, 'merge-base', '--is-ancestor', START, 'HEAD')
    git(authority, 'merge-base', '--is-ancestor', CORRECTION_START, 'HEAD')
    git(authority, 'merge-base', '--is-ancestor', PREDECESSOR, CORRECTION_START)
    base = frozen(str(authority), START)
    main = frozen(str(authority), BASELINE)
    correction = frozen(str(authority), CORRECTION_START)
    predecessor = frozen(str(authority), PREDECESSOR)
    for path, digest in RETIRED.items():
        assert hashlib.sha256(predecessor[path][2]).hexdigest() == digest, 'Retired policy provenance differs'
    assert hashlib.sha256(regular(root / OWNER_RECORD)).hexdigest() == OWNER_SHA256, 'CR-P6-002 owner decision differs'
    assert all(path in base and base[path] == record for path, record in main.items()), 'Start differs from approved main'
    from scope_policy import verify_governance_document
    verify_governance_document(root, authority_root=authority if authority != root else None)
    owned = set(SOURCES) | set(TESTS) | set(DOCS)
    for path, (mode, blob, raw) in base.items():
        wanted = expected_app(raw) if path == 'src/vde/app.py' else raw
        if path == P5_QA:
            wanted = regular(root / path, mode)
            assert hashlib.sha256(wanted).hexdigest() == P5_QA_SHA256, 'Unapproved P5 QA bytes'
        assert regular(root / path, mode) == wanted, 'Protected file changed: ' + path
        if root == authority:
            expected = hashlib.sha1(b'blob ' + str(len(wanted)).encode() + b'\0' + wanted).hexdigest()
            assert git(root, 'ls-tree', 'HEAD', '--', path) == f'{mode} blob {expected}\t{path}\n'.encode(), 'HEAD differs: ' + path
            assert git(root, 'ls-files', '--stage', '--', path) == f'{mode} {expected} 0\t{path}\n'.encode(), 'Index differs: ' + path
    # CR-P6-002 adds a separately named authority; it never changes the old
    # implementation baseline. Preserve every already-published P6 runtime,
    # test helper, authority record and FAILED evidence outside seven paths.
    for path, (mode, blob, raw) in correction.items():
        if path in AMENDED:
            continue
        assert regular(root / path, mode) == raw, 'Correction protected file changed: ' + path
        if root == authority:
            assert git(root, 'ls-tree', 'HEAD', '--', path) == f'{mode} blob {blob}\t{path}\n'.encode(), 'Correction HEAD differs: ' + path
            assert git(root, 'ls-files', '--stage', '--', path) == f'{mode} {blob} 0\t{path}\n'.encode(), 'Correction index differs: ' + path
    for path in owned:
        raw = regular(root / path)
        assert raw == git(authority, 'show', 'HEAD:' + path), 'Owned file differs from committed tree: ' + path
        if root == authority:
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            assert git(root, 'ls-files', '--stage', '--', path) == f'100644 {blob} 0\t{path}\n'.encode(), 'Owned index differs: ' + path
    source_inventory = {p.relative_to(root).as_posix() for p in (root / 'src').rglob('*')
                        if p.is_file() and '__pycache__' not in p.parts
                        and not any(part.endswith('.egg-info') for part in p.parts)}
    assert source_inventory == {p for p in base if p.startswith('src/')} | set(SOURCES), 'Application inventory differs'
    for path in SOURCES:
        for node in ast.walk(ast.parse(regular(root / path))):
            if isinstance(node, ast.Import):
                assert all(n.name.split('.')[0] not in {'subprocess', 'socket', 'requests', 'sqlite3'} for n in node.names), 'Forbidden runtime backend import'
            if isinstance(node, ast.ImportFrom) and not node.level:
                assert node.module.split('.')[0] not in {'subprocess', 'socket', 'requests', 'sqlite3'}, 'Forbidden runtime backend import'
            if isinstance(node, ast.Call):
                name = ast.unparse(node.func)
                assert name not in ('eval', 'exec', 'compile', '__import__'), 'Generated execution forbidden'
                assert not name.endswith(('.approve_brief', '.approve_spec_and_finish', '.complete')), 'P6 cannot auto-approve or execute'
                if name.endswith('.execute'):
                    assert (name.endswith('.connection.execute') and node.args
                            and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
                            and node.args[0].value.lstrip().upper().startswith('SELECT ')), 'P6 cannot execute business code or mutate SQL'
    if root == authority:
        inventory = set(git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z').decode().rstrip('\0').split('\0'))
    else:
        inventory = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    allowed = set(correction) | owned
    evidence = {p for p in inventory if p.startswith(EVIDENCE_ROOT)}
    groups = {p.split('/')[3] for p in evidence}
    for group in groups:
        prefix = 'docs/p6/validation/' + group + '/'
        manifest = prefix + 'MANIFEST.sha256'; entries = {}
        for row in regular(root / manifest).decode().splitlines():
            digest, path = row.split('  ', 1)
            assert path.startswith(prefix) and '..' not in Path(path).parts and path != manifest and path not in entries
            assert hashlib.sha256(regular(root / path)).hexdigest() == digest, 'Evidence checksum differs'
            entries[path] = digest
        assert {p for p in evidence if p.startswith(prefix)} == set(entries) | {manifest}, 'Evidence inventory differs'
    allowed |= evidence
    assert inventory <= allowed, 'Unapproved files: ' + str(sorted(inventory - allowed))
    return dict(result='PASS', policy_format=POLICY['format'], baseline=BASELINE, implementation_start=START,
                correction_start=CORRECTION_START, p5_qa_sha256=P5_QA_SHA256,
                predecessor_policy_commit=PREDECESSOR, retired_policy_provenance='PASS',
                protected_main_files=len(main), protected_start_files=len(base),
                protected_correction_files=len(correction), authorized_amended_paths=list(AMENDED),
                new_runtime_files=len(SOURCES), exact_app_additions=4,
                historical_tests_policies_governance_unchanged=True)


def negative_probes(root, directory):
    root = Path(root); directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    archive = git(root, 'archive', 'HEAD')
    clean = directory / 'clean-control'
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(clean, filter='data')
    assert audit(clean, authority_root=root)['result'] == 'PASS', 'Clean extracted control failed'
    shutil.rmtree(clean)
    probes = [
        ('P1_source', 'src/vde/storage.py'), ('P2_source', 'src/vde/ingestion/local.py'),
        ('P3_source', 'src/vde/workflow/service.py'), ('P4_source', 'src/vde/execution/service.py'),
        ('P5_source', 'src/vde/p5/service.py'), ('old_test', 'tests/p5/test_acceptance.py'),
        ('old_policy', 'tests/p5/scope_policy_v1.json'), ('old_audit', 'tests/p5/scope_audit.py'),
        ('P0_schema', 'pecs/pilot_slice_v1/contracts/qa_report.schema.json'),
        ('P0_fixture', 'pecs/pilot_slice_v1/fixtures/P-A_dirty_csv/expected_result.csv'),
        ('dependency', 'pyproject.toml'), ('lock', 'uv.lock'), ('governance', 'DECISIONS.md'),
        ('active_pin', 'tests/p4/approved_governance_pin_v1.json'),
        ('migration', 'src/vde/persistence/migrations/999_p6.sql'),
        ('extra_source', 'src/vde/p6/extra.py'), ('app_extra', 'src/vde/app.py'),
        ('authority_doc', 'docs/p6/decisions/CR-P6-001_OWNER_DECISION_2026-11-06.md'),
        ('historical_evidence', 'docs/p5/validation/runtime-20261106/final-run/p5-runtime/results.xml'),
        ('file_mode', 'src/vde/storage.py'),
        ('unknown_file', 'p6-unapproved.txt'), ('owned_source', 'src/vde/p6/delivery.py'),
        ('new_policy', 'tests/p6/scope_policy_v1.json'),
        ('retired_policy', 'tests/p6/scope_policy_v1.json'),
        ('qa_guard_relaxation', P5_QA), ('qa_other_function', P5_QA),
        ('qa_file_mode', P5_QA),
        ('correction_owner_record', OWNER_RECORD),
        ('old_failed_evidence', 'docs/p6/validation/runtime-20261107/final-run/p6-runtime/results.xml'),
        ('unapproved_evidence_root', 'docs/p6/validation/runtime-unapproved/extra.txt'),
    ]
    results = []
    for label, path in probes:
        scratch = directory / label
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(scratch, filter='data')
        target = scratch / path; target.parent.mkdir(parents=True, exist_ok=True)
        if label in ('file_mode', 'qa_file_mode'):
            target.chmod(0o755)
        elif label == 'retired_policy':
            target.write_bytes(git(root, 'show', PREDECESSOR + ':' + path))
        elif label == 'qa_guard_relaxation':
            raw = target.read_bytes()
            mutant = raw.replace(b"c['operator'] == 'sequence_equals'", b"c['operator'] == 'not_equals'")
            assert mutant != raw
            target.write_bytes(mutant)
        else:
            target.write_bytes((target.read_bytes() if target.exists() else b'') + b'\n# unapproved mutation\n')
        try:
            audit(scratch, authority_root=root)
        except (AssertionError, OSError, subprocess.SubprocessError, ValueError) as exc:
            results.append(dict(probe=label, result='REJECTED', reason=str(exc)[:500]))
        else:
            raise AssertionError('Scope mutation accepted: ' + label)
        finally:
            shutil.rmtree(scratch)
    return results
