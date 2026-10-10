"""CR-P2-001 test boundaries. No application/runtime dependency on this module."""
import ast
import hashlib
import json
from pathlib import Path
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


def audit_application(root, baseline_pyproject, baseline_lock):
    """Fail closed on new paths/imports/calls/workflows/deps/migrations.

    This is a static regression gate and reviewed source boundary, not a proof
    against deliberately obfuscated semantics inside an already permitted call.
    """
    root = Path(root)
    policy = json.loads(POLICY.read_text())
    actual_paths = {p.relative_to(root).as_posix() for p in (root / 'src').rglob('*')
                    if p.is_file() and '__pycache__' not in p.parts and not any(part.endswith('.egg-info') for part in p.parts)}
    assert actual_paths == set(policy['source_paths']), 'Unapproved application source/module/migration'
    for path, digest in policy['frozen_p1_sha256'].items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, 'P1 runtime or migration drift: ' + path
    for path, expected in policy['python_surfaces'].items():
        actual = surface((root / path).read_text())
        # Additions AND removals require an explicit reviewed boundary update.
        for field in ('imports', 'calls', 'definitions'):
            assert actual[field] == expected[field], 'Unapproved ' + field + ': ' + path
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


def audit_repository_paths(paths):
    """Every changed/untracked repository path must belong to this P2/CR work."""
    source_paths = set(json.loads(POLICY.read_text())['source_paths']) - set(P1_MODULES) - {'src/vde/persistence/migrations/001_p1_baseline.sql'}
    allowed = source_paths | {
        'pyproject.toml', 'uv.lock', 'tests/scope_policy.py', 'tests/p1/test_p1.py',
        'tests/p2/test_p2.py', 'tests/p2/conftest.py', 'tests/p2/rss_probe.py', 'tests/p2/scope_allowlist_v1.json',
        'docs/p1/amendments/v1.1/P1_TEST_PLAN_AMENDMENT.md',
        'docs/p1/amendments/v1.1/TRACEABILITY_AMENDMENT.md',
    }
    for path in paths:
        assert path in allowed or path.startswith('docs/p2/validation/'), 'Unapproved repository change: ' + path
