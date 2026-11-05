"""CR-P2-001 test boundaries. No application/runtime dependency on this module."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tomllib

# Explicit validated P1 inventory, excluding the permitted app.py integration.
P1_MODULES = (
    'src/vde/__init__.py', 'src/vde/bootstrap.py', 'src/vde/config.py',
    'src/vde/contracts.py', 'src/vde/errors.py', 'src/vde/models.py',
    'src/vde/recovery.py', 'src/vde/storage.py', 'src/vde/workspace.py',
    'src/vde/persistence/__init__.py', 'src/vde/persistence/database.py',
    'src/vde/persistence/repositories.py', 'src/vde/persistence/uow.py',
)
POLICY = Path(__file__).with_name('p2') / 'scope_allowlist_v1.json'
P3_POLICY = Path(__file__).with_name('p3') / 'scope_allowlist_v1.json'
P4_POLICY = Path(__file__).with_name('p4') / 'scope_allowlist_v1.json'
GOVERNANCE_PIN = 'tests/p4/approved_governance_pin_v1.json'
GOVERNANCE_BASELINE = '7685110506d115805c473b064752f86e9e5c045b'
PRIOR_OWNER_APPROVAL = '89d8e590d528cce58b5476a41ca5cc482e59be3e'
# CR-P4-005: computed after immutable Stage A, never from DECISIONS at runtime.
GOVERNANCE_PIN_SHA256 = '95b7c92a417ec06a80f3d4e839e136e00100e4313d1bee021c94f5beda1f0df7'


def _governance_require(condition, reason):
    assert condition, 'Unapproved governance document: ' + reason


def _regular_bytes(path):
    try:
        mode = path.lstat().st_mode
        _governance_require(stat.S_ISREG(mode) and not mode & 0o111, 'file mode/type: ' + str(path))
        return path.read_bytes()
    except OSError as error:
        raise AssertionError('Unapproved governance document: missing/unreadable ' + str(path)) from error


def _governance_git(root, *args):
    # Neither a caller's index/worktree override nor replace refs confer authority.
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    try:
        return subprocess.check_output(['git', '--no-replace-objects', '-C', str(root), *args],
                                       env=env, stderr=subprocess.PIPE, timeout=10)
    except (OSError, subprocess.SubprocessError) as error:
        raise AssertionError('Unapproved governance document: Git check failed: ' + ' '.join(args)) from error


def load_governance_pin(root):
    raw = _regular_bytes(Path(root) / GOVERNANCE_PIN)
    _governance_require(hashlib.sha256(raw).hexdigest() == GOVERNANCE_PIN_SHA256, 'pin SHA-256')

    def unique(pairs):
        result = {}
        for key, value in pairs:
            _governance_require(key not in result, 'duplicate pin key')
            result[key] = value
        return result

    try:
        pin = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError) as error:
        raise AssertionError('Unapproved governance document: malformed pin') from error
    keys = {'format', 'repository', 'path', 'implementation_baseline', 'approval_commit',
            'decisions_blob', 'decisions_sha256', 'decisions_size_bytes', 'git_mode'}
    _governance_require(type(pin) is dict and set(pin) == keys, 'closed pin fields')
    _governance_require(pin['format'] == 'P4_GOVERNANCE_PIN_V1'
                        and pin['repository'] == '1Hoax1/verified-data-extraction'
                        and pin['path'] == 'DECISIONS.md'
                        and pin['implementation_baseline'] == GOVERNANCE_BASELINE
                        and pin['git_mode'] == '100644', 'pin scope')
    for key, length in [('approval_commit', 40), ('decisions_blob', 40), ('decisions_sha256', 64)]:
        _governance_require(type(pin[key]) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', pin[key]), 'pin ' + key)
    _governance_require(type(pin['decisions_size_bytes']) is int and pin['decisions_size_bytes'] > 0, 'pin size')
    _governance_require(raw == (json.dumps(pin, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode(), 'pin serialization')
    return pin


def verify_governance_document(root, *, authority_root=None):
    """Exact CR-P4-005 authority; explicit real repo required for scratch audits."""
    root = Path(root).resolve()
    authority = root if authority_root is None else Path(authority_root).resolve()
    pin = load_governance_pin(authority)
    top = _governance_git(authority, 'rev-parse', '--show-toplevel').decode().strip()
    _governance_require(Path(top).resolve() == authority, 'repository root')
    _governance_require(not _governance_git(authority, 'for-each-ref', 'refs/replace'), 'replace refs')
    _governance_require(_governance_git(authority, 'rev-parse', '--is-shallow-repository').strip() == b'false', 'shallow history')
    grafts = Path(os.fsdecode(_governance_git(authority, 'rev-parse', '--git-path', 'info/grafts').strip()))
    if not grafts.is_absolute():
        grafts = authority / grafts
    _governance_require(not grafts.exists() or not grafts.read_bytes(), 'grafted history')
    for earlier, later in [(GOVERNANCE_BASELINE, PRIOR_OWNER_APPROVAL),
                           (PRIOR_OWNER_APPROVAL, pin['approval_commit']),
                           (pin['approval_commit'], 'HEAD')]:
        _governance_git(authority, 'merge-base', '--is-ancestor', earlier, later)
    tree_entry = f"100644 blob {pin['decisions_blob']}\tDECISIONS.md\0".encode()
    for revision in (pin['approval_commit'], 'HEAD'):
        _governance_require(_governance_git(authority, 'ls-tree', '-z', revision, '--', 'DECISIONS.md') == tree_entry, 'Git tree blob/mode: ' + revision)
    index_entry = f"100644 {pin['decisions_blob']} 0\tDECISIONS.md\0".encode()
    _governance_require(_governance_git(authority, 'ls-files', '--stage', '-z', '--', 'DECISIONS.md') == index_entry, 'index blob/mode/stage')
    raw = _governance_git(authority, 'cat-file', 'blob', pin['decisions_blob'])
    _governance_require(len(raw) == pin['decisions_size_bytes']
                        and hashlib.sha256(raw).hexdigest() == pin['decisions_sha256'], 'approval blob bytes/size')
    _governance_require(_regular_bytes(authority / 'DECISIONS.md') == raw, 'working document bytes')
    if root != authority:
        _governance_require(not (root / '.git').exists(), 'scratch cannot substitute another repository')
        _governance_require(_regular_bytes(root / 'DECISIONS.md') == raw, 'copied document bytes')
    return pin


def surface(text):
    tree = ast.parse(text)
    imports, calls, definitions = set(), set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update('import ' + alias.name + ' as ' + str(alias.asname) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.update('from ' + '.' * node.level + (node.module or '') + ' import ' + alias.name + ' as ' + str(alias.asname) for alias in node.names)
        elif isinstance(node, ast.Call):
            calls.add(ast.unparse(node.func))
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            definitions.add(node.name)
    return {'imports': sorted(imports), 'calls': sorted(calls), 'definitions': sorted(definitions)}


def audit_application(root, baseline_pyproject, baseline_lock, *, phase='p2'):
    """Fail closed on new paths/imports/calls/workflows/deps/migrations.

    This is a static regression gate and reviewed source boundary, not a proof
    against deliberately obfuscated semantics inside an already permitted call.
    """
    root = Path(root)
    policy = json.loads(POLICY.read_text())
    approved_p3 = json.loads(P3_POLICY.read_text())
    approved_p4 = json.loads(P4_POLICY.read_text())
    actual_paths = {p.relative_to(root).as_posix() for p in (root / 'src').rglob('*')
                    if p.is_file() and '__pycache__' not in p.parts and not any(part.endswith('.egg-info') for part in p.parts)}
    # CR-P4-001: only enumerated P4-owned files are admitted; P4-T62 audits
    # their complete contents. Historical source and negative checks remain.
    assert actual_paths == set(approved_p3['source_paths']) | set(approved_p4['p4_source_paths']), 'Unapproved application source/module/migration'
    for path, digest in policy['frozen_p1_sha256'].items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, 'P1 runtime or migration drift: ' + path
    for path, expected in policy['python_surfaces'].items():
        if path == 'src/vde/app.py':
            expected = approved_p4['python_surfaces'][path]
        actual = surface((root / path).read_text())
        # Additions AND removals require an explicit reviewed boundary update.
        for field in ('imports', 'calls', 'definitions'):
            assert actual[field] == expected[field], 'Unapproved ' + field + ': ' + path
    # CR-P3-002: historical P2 runtime is explicitly frozen. P3-T51 alone owns
    # the new workflow modules' complete source hashes and reviewed surfaces.
    for path, digest in approved_p3['frozen_p2_sha256'].items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, 'P2 runtime drift: ' + path
    if phase == 'p3':
        for path, digest in approved_p3['reviewed_p3_sha256'].items():
            data = (root / path).read_bytes()
            if path == 'src/vde/app.py':
                integration = approved_p4['app_integration'].encode('utf-8')
                assert data.endswith(integration), 'Unapproved P4 app integration'
                data = data[:-len(integration)]
            assert hashlib.sha256(data).hexdigest() == digest, 'Unapproved P3 source drift: ' + path
        for path, expected in approved_p3['python_surfaces'].items():
            if path == 'src/vde/app.py':
                expected = approved_p4['python_surfaces'][path]
            assert surface((root / path).read_text()) == expected, 'Unapproved application surface: ' + path
    project = tomllib.loads((root / 'pyproject.toml').read_text())
    base = tomllib.loads(baseline_pyproject)
    assert project['project']['dependencies'] == base['project']['dependencies'] + ['openpyxl==3.1.5'], 'Unapproved reader/application dependency'
    assert project['project'].get('optional-dependencies') == base['project'].get('optional-dependencies'), 'Unapproved optional dependency'
    assert project['build-system'] == base['build-system'], 'Unapproved build dependency'
    assert project['project'].get('scripts') == base['project'].get('scripts'), 'Unapproved service/entry point'
    lock = tomllib.loads((root / 'uv.lock').read_text())
    old_lock = tomllib.loads(baseline_lock)
    versions = lambda value: {p['name']: p['version'] for p in value['package']}
    assert versions(lock) == versions(old_lock) | {'openpyxl': '3.1.5', 'et-xmlfile': '2.0.0'}, 'Unapproved locked dependency/version'
    editable = next(p for p in lock['package'] if p['name'] == 'verified-data-extraction')
    old_editable = next(p for p in old_lock['package'] if p['name'] == 'verified-data-extraction')
    expected = sorted(old_editable['dependencies'] + [{'name': 'openpyxl'}], key=lambda p: p['name'])
    assert editable['dependencies'] == expected, 'Unapproved locked direct dependency'
    metadata = editable['metadata']['requires-dist']
    old_metadata = old_editable['metadata']['requires-dist']
    expected_metadata = sorted(old_metadata + [{'name': 'openpyxl', 'specifier': '==3.1.5'}], key=lambda p: p['name'])
    assert metadata == expected_metadata, 'Unapproved dependency metadata'
    # uv can lock multiple platform/Python versions for the same name (numpy).
    # Compare full records as a multiset, preserving each resolution branch.
    original_records = sorted(json.dumps(p, sort_keys=True) for p in old_lock['package'] if p['name'] != 'verified-data-extraction')
    existing_records = sorted(json.dumps(p, sort_keys=True) for p in lock['package'] if p['name'] not in {'verified-data-extraction', 'openpyxl', 'et-xmlfile'})
    assert existing_records == original_records, 'Unapproved transitive dependency/graph drift'
    for name in ['verified-data-extraction', 'openpyxl', 'et-xmlfile']:
        assert sum(p['name'] == name for p in lock['package']) == 1, 'Unapproved duplicate dependency record'
    for package in lock['package']:
        if package['name'] != 'verified-data-extraction':
            assert package.get('source') == {'registry': 'https://pypi.org/simple'}, 'Unapproved dependency source'


def audit_repository_paths(paths, *, root=None):
    """Every changed/untracked repository path must belong to this P2/CR work."""
    source_paths = set(json.loads(POLICY.read_text())['source_paths']) - set(P1_MODULES) - {'src/vde/persistence/migrations/001_p1_baseline.sql'}
    allowed = source_paths | {
        'pyproject.toml', 'uv.lock', 'tests/scope_policy.py', 'tests/p1/test_p1.py',
        'tests/p2/test_p2.py', 'tests/p2/conftest.py', 'tests/p2/rss_probe.py', 'tests/p2/scope_allowlist_v1.json',
        'docs/p1/amendments/v1.1/P1_TEST_PLAN_AMENDMENT.md',
        'docs/p1/amendments/v1.1/TRACEABILITY_AMENDMENT.md',
    }
    approved_p3 = json.loads(P3_POLICY.read_text())
    allowed |= set(approved_p3['source_paths']) - set(P1_MODULES) - {'src/vde/persistence/migrations/001_p1_baseline.sql'}
    allowed |= set(approved_p3['test_paths'])
    approved_p4 = json.loads(P4_POLICY.read_text())
    allowed |= set(approved_p4['p4_source_paths']) | set(approved_p4['test_paths'])
    allowed |= set(approved_p4['amendment_paths'])
    for path in paths:
        if path == 'DECISIONS.md' and root is not None:
            verify_governance_document(root)
            continue
        assert path in allowed or path.startswith(('docs/p2/validation/', 'docs/p3/validation/',
               'docs/p2/amendments/v1.1/', 'docs/p4/validation/')), 'Unapproved repository change: ' + path
