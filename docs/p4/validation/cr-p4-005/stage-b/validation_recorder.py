"""External validation recorder; preserves every existing validation file."""
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = Path('/workspace/p4-cr005-integration')
BASE = Path('/workspace/p4-cr005-stageb-work/runs')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


phase = sys.argv[1]
out = BASE / phase
out.mkdir(parents=True, exist_ok=False)
selection = {
    'positive': ['tests/p2/test_p2.py::test_T40_scope_dependencies', 'tests/p3/test_p3.py::test_T51_whole_application_scope'],
    'scope': ['tests/p4/test_execution.py::test_T61_forbidden_scope',
              'tests/p4/test_execution.py::test_T62_whole_application_scope_CR_P4_001',
              'tests/p4/test_execution.py::test_T63_frozen_regression_evidence_and_p0'],
    'full': ['tests/p1', 'tests/p2', 'tests/p3', 'tests/p4'],
}[phase.split('-')[0]]
assert not git('status', '--porcelain'), 'Each phase must start at a clean committed tree'
sha, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
validation_roots = [ROOT / 'docs' / p / 'validation' for p in ('p1', 'p2', 'p3', 'p4')]
old = {p: p.read_bytes() for directory in validation_roots if directory.exists() for p in directory.rglob('*') if p.is_file()}
current_outputs = set()
initialized = []
if phase.startswith('full-'):
    # Empty test-output maps force proof of this run's complete fixture coverage.
    # Original evidence bytes are already snapshotted and are restored in finally.
    for group in ('f-fixture', 'x-fixture', 'w-fixture', 'golden', 'generator', 'p0-semantic'):
        p = ROOT / 'docs/p4/validation' / (group + '-results.json')
        p.write_text('{}\n')
        initialized.append(str(p.relative_to(ROOT)))
    current_outputs = {p for p in old if p.parent == ROOT / 'docs/p4/validation'
                       and (p.name.endswith('-results.json') or p.name.startswith(('stress.', 'fixture-verifier.', 'restart-', 'T63-')))}
tracked = git('ls-files').splitlines()
inputs = {p: digest((ROOT / p).read_bytes()) for p in tracked if ROOT / p not in old}
env = os.environ.copy()
env['PATH'] = '/workspace/verified-data-extraction/.venv/bin:' + env['PATH']
env['PYTHONPATH'] = str(ROOT / 'src') + os.pathsep + str(ROOT / 'tests')
env['PYTHONDONTWRITEBYTECODE'] = '1'
env['PYTEST_ADDOPTS'] = '--junitxml=' + str(out / 'results.xml')
command = ['python', '-m', 'pytest', *selection, '-q']
meta = {'command': command, 'shell_command': ' '.join(command), 'cwd': str(ROOT),
        'branch': git('branch', '--show-current'), 'tested_commit': sha, 'tested_tree': tree,
        'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
        'packages': {name: importlib.metadata.version(name) for name in ['pytest', 'jsonschema', 'referencing', 'rfc8785', 'openpyxl', 'streamlit']},
        'environment': {key: env.get(key) for key in ['PATH', 'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'PYTEST_ADDOPTS', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD', 'LANG', 'LC_ALL']},
        'started_at_moscow': datetime.now(ZoneInfo('Europe/Moscow')).isoformat(),
        'input_sha256': inputs,
        'previous_validation_sha256': {str(p.relative_to(ROOT)): digest(raw) for p, raw in old.items()}}
start = time.monotonic()
try:
    with (out / 'stdout.txt').open('wb') as stdout, (out / 'stderr.txt').open('wb') as stderr:
        run = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
finally:
    generated = {}
    for directory in validation_roots:
        if not directory.exists():
            continue
        for p in directory.rglob('*'):
            if not p.is_file():
                continue
            raw = p.read_bytes()
            if p not in old or old[p] != raw or p in current_outputs:
                relative = p.relative_to(ROOT)
                target = out / 'generated' / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                generated[str(relative)] = digest(raw)
            if p not in old:
                p.unlink()
    for p, raw in old.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
meta.update(finished_at_moscow=datetime.now(ZoneInfo('Europe/Moscow')).isoformat(),
            elapsed_seconds=time.monotonic() - start, exit_code=run.returncode,
            generated=generated, stdout_sha256=digest((out/'stdout.txt').read_bytes()),
            stderr_sha256=digest((out/'stderr.txt').read_bytes()))
meta['fixture_outputs_initialized_before_run'] = initialized
meta['old_validation_restored'] = all(p.read_bytes() == raw for p, raw in old.items())
meta['inputs_unchanged'] = all(digest((ROOT / p).read_bytes()) == value for p, value in inputs.items())
meta['final_status'] = git('status', '--porcelain')
meta['commit_unchanged'] = git('rev-parse', 'HEAD') == sha and git('rev-parse', 'HEAD^{tree}') == tree
if (out/'results.xml').exists():
    cases = list(ET.parse(out/'results.xml').getroot().iter('testcase'))
    meta['testcases'] = [{'classname': c.get('classname'), 'name': c.get('name'),
                         'outcome': next((key for key in ['failure', 'error', 'skipped'] if c.find(key) is not None), 'pass'),
                         'properties': {p.get('name'): p.get('value') for p in c.findall('./properties/property')}} for c in cases]
(out/'command-environment.json').write_text(json.dumps(meta, indent=2) + '\n')
(out/'exit-code.txt').write_text(str(run.returncode) + '\n')
assert meta['old_validation_restored'] and meta['inputs_unchanged'] and meta['commit_unchanged'] and not meta['final_status'], meta
print(json.dumps({key: meta[key] for key in ['tested_commit', 'tested_tree', 'exit_code', 'elapsed_seconds', 'old_validation_restored', 'inputs_unchanged', 'final_status']}, indent=2))
print((out/'stdout.txt').read_text()[-7000:])
print((out/'stderr.txt').read_text()[-2000:], file=sys.stderr)
sys.exit(run.returncode)
