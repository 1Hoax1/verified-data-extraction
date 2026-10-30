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


def frozen_baseline(root):
    policy = json.loads(POLICY.read_text())
    for path, expected in policy['frozen_sha256'].items():
        assert digest((root/path).read_bytes()) == expected, 'Unapproved frozen runtime/contract drift: '+path


def audit_p4(root):
    policy = json.loads(POLICY.read_text())
    frozen_baseline(root)
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
    audit_p4(scratch)
    for name, contents in [('src/vde/execution/worker.py','import celery'),
                           ('src/vde/p5.py','def export(): pass'),
                           ('src/vde/persistence/migrations/002_p4.sql','CREATE TABLE rows(id);')]:
        target = scratch/name
        target.write_text(contents)
        with pytest.raises(AssertionError):
            audit_p4(scratch)
        target.unlink()
    for name in ('src/vde/workflow/service.py','src/vde/storage.py',
                 'src/vde/persistence/migrations/001_p1_baseline.sql','src/vde/execution/engine.py'):
        target = scratch/name
        original = target.read_bytes()
        target.write_bytes(original+b'\n# unapproved drift\n')
        with pytest.raises(AssertionError):
            audit_p4(scratch)
        target.write_bytes(original)
    target = scratch/'pyproject.toml'
    original = target.read_text()
    target.write_text(original.replace('"openpyxl==3.1.5"','"openpyxl==3.1.5", "sqlalchemy==2.0.0"'))
    with pytest.raises(AssertionError):
        audit_p4(scratch)
    target.write_text(original)
