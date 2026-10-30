"""Build a reviewable exact P4 test inventory; never part of application code."""
import hashlib
import json
from pathlib import Path
import subprocess
import tomllib

from scope_policy import surface

ROOT = Path(__file__).resolve().parents[2]
BASE = '7685110506d115805c473b064752f86e9e5c045b'
INTEGRATION = 'from vde.execution.ui import panel as execution_panel\nexecution_panel(result)\n'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build():
    names = subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True).splitlines()
    frozen = {}
    for name in names:
        protected = (name.startswith(('src/', 'pecs/pilot_slice_v1/', 'docs/p1/v1.0/', 'docs/p2/v1.0/',
                     'docs/p3/v1.0/', 'docs/p4/v1.0/', 'tests/p1/', 'tests/p2/', 'tests/p3/'))
                     or name == 'DECISIONS.md')
        if not protected or name == 'src/vde/app.py':
            continue
        expected = subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT)
        if name == 'tests/p2/test_p2.py':
            expected = expected.replace(b"    changed = subprocess.check_output(['git', 'diff', '--name-only', 'ba73d05d2294dfb7e51b9c3c758e63c6065286d6']",
                b"    # CR-P4-003: exclude governance already present at owner-authorized P4 start.\n    changed = subprocess.check_output(['git', 'diff', '--name-only', '7685110506d115805c473b064752f86e9e5c045b']")
        if name == 'tests/p3/test_p3.py':
            expected = expected.replace(b"    changed = subprocess.check_output(['git', 'diff', '--name-only', 'ba73d05']",
                b"    # CR-P4-003: exclude governance already present at owner-authorized P4 start.\n    changed = subprocess.check_output(['git', 'diff', '--name-only', '7685110506d115805c473b064752f86e9e5c045b']")
        assert (ROOT/name).read_bytes() == expected, 'Protected source/test/pack drift: '+name
        frozen[name] = digest(expected)
    original_app = subprocess.check_output(['git','show',BASE+':src/vde/app.py'],cwd=ROOT)
    assert (ROOT/'src/vde/app.py').read_bytes() == original_app+INTEGRATION.encode()
    source_paths = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'src').rglob('*') if p.is_file()
                          and '__pycache__' not in p.parts and not any(n.endswith('.egg-info') for n in p.parts))
    p4_paths = ['src/vde/execution/'+name+'.py' for name in ('__init__','budget','commit','engine','errors','operations',
                 'preflight','provenance','service','source_adapter','spill','ui','wire')]
    assert set(p4_paths) == {p for p in source_paths if p.startswith('src/vde/execution/')}
    test_paths = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'tests/p4').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    test_paths = sorted(set(test_paths)|{'tests/p4/scope_allowlist_v1.json'})
    policy = {'authority':'P4 approved implementation start; CR-P4-001; owner-approved CR-P4-003', 'baseline':BASE,
              'p4_source_paths':p4_paths,'app_integration':INTEGRATION,
              'source_sha256':{p:digest((ROOT/p).read_bytes()) for p in source_paths},
              'python_surfaces':{p:surface((ROOT/p).read_text()) for p in source_paths if p.endswith('.py')},
              'frozen_sha256':frozen, 'lock_sha256':digest((ROOT/'uv.lock').read_bytes()),
              'pyproject':tomllib.loads((ROOT/'pyproject.toml').read_text()),'test_paths':test_paths,
              'amendment_paths':['docs/change_requests/CR-P4-002.md','docs/change_requests/CR-P4-003.md','docs/change_requests/CR-P4-004.md',
                  'docs/p4/amendments/v1.1/P4_TEST_PLAN_AMENDMENT.md',
                  'docs/p4/amendments/v1.2/P4_DECIMAL_WIRE_AMENDMENT.md',
                  'docs/p4/implementation/README.md',
                  'docs/p3/amendments/v1.1/P3_TEST_PLAN_AMENDMENT.md',
                  'docs/p3/amendments/v1.1/TRACEABILITY_AMENDMENT.md',
                  'docs/p2/amendments/v1.2/P2_TEST_PLAN_AMENDMENT.md',
                  'docs/p2/amendments/v1.2/TRACEABILITY_AMENDMENT.md']}
    (ROOT/'tests/p4/scope_allowlist_v1.json').write_text(json.dumps(policy,indent=2,sort_keys=True)+'\n')
    print('Exact scope inventory:',len(source_paths),'source files;',len(frozen),'frozen inputs')


if __name__ == '__main__':
    build()
