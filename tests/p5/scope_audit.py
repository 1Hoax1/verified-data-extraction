"""CR-P5-002 successor audit; historical policies and hashes stay untouched."""
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

BASELINE='820245fc544fc66c393db548151e6d281e03d414'
HISTORICAL='fd39aa1bed480313504ae8b1f76e77e170cb72ba'
ADDENDUM_COMMIT='20e78e55c8f461d01b9671c475ba7fa98ae0a745'
P5_SOURCE=tuple('src/vde/p5/'+n for n in (
    '__init__.py','budget.py','contract.py','errors.py','export.py','project.py',
    'qa.py','report.py','roundtrip.py','service.py','ui.py'))
P5_TESTS=tuple('tests/p5/'+n for n in (
    '__init__.py','conftest.py','support.py','test_acceptance.py','scope_audit.py',
    'scope_policy_v1.json','restart_probe.py','stress_probe.py','run_validation.py'))
P5_DOCS=(
    'docs/p5/design_addenda/P5_DESIGN_ADDENDUM_v0.2c_CR_P5_003.md',
    'docs/p5/implementation/README.md',
    'docs/p5/implementation/TEST_PLAN_TRACEABILITY.md',
)
APP_APPEND=b'from vde.p5.ui import panel as export_qa_panel\nexport_qa_panel(result)\n'
EVIDENCE_ROOT='docs/p5/validation/runtime-20261106/'
POLICY=dict(format='P5_SCOPE_POLICY_V1',implementation_start=BASELINE,historical_regression_base=HISTORICAL,
            addendum_commit=ADDENDUM_COMMIT,source_paths=list(P5_SOURCE),test_paths=list(P5_TESTS),document_paths=list(P5_DOCS),
            app_integration=APP_APPEND.decode(),evidence_root=EVIDENCE_ROOT,
            authority='Owner-approved P5 Gate A; CR-P5-001/002/003; no historical policy changes')


def git(root,*args):
    return subprocess.check_output(['git','--no-replace-objects','-C',str(root),*args],stderr=subprocess.PIPE)


@lru_cache(maxsize=4)
def frozen(root):
    root=Path(root)
    entries={}
    for line in git(root,'ls-tree','-r','--full-tree',BASELINE).decode().splitlines():
        obj,path=line.split('\t');mode,kind,blob=obj.split()
        assert kind=='blob'
        entries[path]=(mode,blob,git(root,'cat-file','blob',blob))
    return entries


def regular(path):
    mode=path.lstat().st_mode
    assert stat.S_ISREG(mode) and not mode&0o111,'File mode/type not approved: '+str(path)
    return path.read_bytes()


def audit(root,*,authority_root=None):
    root=Path(root).resolve();authority=root if authority_root is None else Path(authority_root).resolve()
    assert json.loads(regular(root/'tests/p5/scope_policy_v1.json'))==POLICY,'P5 policy closed contents differ'
    from scope_policy import verify_governance_document
    verify_governance_document(root,authority_root=authority if root!=authority else None)
    git(authority,'merge-base','--is-ancestor',BASELINE,'HEAD')
    git(authority,'merge-base','--is-ancestor',ADDENDUM_COMMIT,'HEAD')
    assert regular(root/P5_DOCS[0])==git(authority,'show',ADDENDUM_COMMIT+':'+P5_DOCS[0]),'Approved numeric addendum changed'
    base=frozen(str(authority))
    for path,(mode,blob,raw) in base.items():
        actual=regular(root/path)
        wanted=raw+APP_APPEND if path=='src/vde/app.py' else raw
        assert actual==wanted,'Protected file changed: '+path
        if root==authority:
            expected_blob=hashlib.sha1(b'blob '+str(len(wanted)).encode()+b'\0'+wanted).hexdigest()
            assert git(authority,'ls-tree','HEAD','--',path)==f'{mode} blob {expected_blob}\t{path}\n'.encode(),'HEAD differs: '+path
            assert git(authority,'ls-files','--stage','--',path)==f'{mode} {expected_blob} 0\t{path}\n'.encode(),'Index differs: '+path
    sources={p.relative_to(root).as_posix() for p in (root/'src').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert sources=={p for p in base if p.startswith('src/')}|set(P5_SOURCE),'Application source inventory differs'
    imports={'collections','csv','dataclasses','datetime','decimal','fractions','hashlib','itertools','math',
             'pathlib','tempfile','threading','time','types','unicodedata','uuid','xml','zipfile',
             'vde','jsonschema','openpyxl','streamlit'}
    for path in P5_SOURCE:
        raw=regular(root/path);tree=ast.parse(raw)
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                assert all(a.name.split('.')[0] in imports for a in node.names),'Forbidden P5 import: '+path
            if isinstance(node,ast.ImportFrom) and not node.level:
                assert node.module.split('.')[0] in imports,'Forbidden P5 import: '+path
            if isinstance(node,ast.Call):
                name=ast.unparse(node.func)
                assert name not in ('eval','exec','compile','__import__','getattr','setattr'),'Dynamic execution forbidden'
                assert not name.startswith(('OPERATIONS.','subprocess.','os.system','sqlite3.')),'Unapproved execution/operation/schema change'
        # New owned sources must also equal the exact committed review tree.
        expected=git(authority,'show','HEAD:'+path)
        assert raw==expected,'P5 source differs from committed tree: '+path
        if root==authority:
            blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            assert git(authority,'ls-files','--stage','--',path)==f'100644 {blob} 0\t{path}\n'.encode(),'P5 index differs'
    for path in (*P5_TESTS,*P5_DOCS):
        raw=regular(root/path)
        assert raw==git(authority,'show','HEAD:'+path),'New owned test/document differs from committed tree: '+path
        if root==authority:
            blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            assert git(authority,'ls-files','--stage','--',path)==f'100644 {blob} 0\t{path}\n'.encode(),'Owned test/document index differs'
    if root==authority:
        inventory=set(git(authority,'ls-files','--cached','--others','--exclude-standard','-z').decode().rstrip('\0').split('\0'))
    else:
        inventory={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    allowed=set(base)|set(P5_SOURCE)|set(P5_TESTS)|set(P5_DOCS)
    evidence={p for p in inventory if p.startswith(EVIDENCE_ROOT)}
    if evidence:
        manifest=EVIDENCE_ROOT+'MANIFEST.sha256'
        entries={}
        for row in regular(root/manifest).decode().splitlines():
            digest,path=row.split('  ',1)
            assert path.startswith(EVIDENCE_ROOT) and '..' not in Path(path).parts and path!=manifest
            assert path not in entries
            assert hashlib.sha256(regular(root/path)).hexdigest()==digest,'Evidence hash differs'
            entries[path]=digest
        assert evidence==set(entries)|{manifest},'Finite evidence manifest inventory differs'
        allowed|=evidence
    assert inventory<=allowed,'Unapproved repository files: '+str(sorted(inventory-allowed))
    return {'result':'PASS','protected_start_files':len(base),'P5_sources':len(P5_SOURCE),
            'historical_tests_and_policies_unchanged':True,'governance_pin_unchanged':True}


def negative_probes(root,directory):
    root=Path(root);directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    raw=git(root,'archive','HEAD')
    probes=[
        ('protected_runtime','src/vde/storage.py',lambda b:b+b'\n# forbidden change\n'),
        ('historical_test','tests/p2/test_p2.py',lambda b:b+b'\n# forbidden change\n'),
        ('P0_schema','pecs/pilot_slice_v1/contracts/qa_report.schema.json',lambda b:b+b'\n'),
        ('P0_fixture','pecs/pilot_slice_v1/fixtures/P-A_dirty_csv/expected_result.csv',lambda b:b+b'\n'),
        ('migration','src/vde/persistence/migrations/999_p5.sql',lambda b:b'CREATE TABLE forbidden(x);'),
        ('dependency','pyproject.toml',lambda b:b+b'\n# dependency drift\n'),
        ('DECISIONS','DECISIONS.md',lambda b:b+b'\nUnapproved\n'),
        ('governance_pin','tests/p4/approved_governance_pin_v1.json',lambda b:b+b'\n'),
        ('old_policy','tests/p4/scope_allowlist_v1.json',lambda b:b+b'\n'),
        ('new_source','src/vde/p6.py',lambda b:b'# not approved\n'),
        ('unknown_P5_source','src/vde/p5/network.py',lambda b:b'import socket\n'),
        ('network_import','src/vde/p5/service.py',lambda b:b+b'\nimport socket\n'),
        ('arbitrary_execution','src/vde/p5/service.py',lambda b:b+b'\nexec("pass")\n'),
        ('new_operation','src/vde/p5/qa.py',lambda b:b+b'\nOPERATIONS.add("compute")\n'),
        ('app_auto_trigger','src/vde/app.py',lambda b:b+b'\nexport_qa_panel(result)\n'),
        ('policy_expansion','tests/p5/scope_policy_v1.json',lambda b:b.replace(b'"P5_SCOPE_POLICY_V1"',b'"UNAPPROVED"')),
        ('unapproved_file','unapproved-document.txt',lambda b:b'unknown\n'),
    ]
    result=[]
    for name,path,change in probes:
        scratch=directory/name
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:archive.extractall(scratch,filter='data')
        target=scratch/path;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(change(target.read_bytes() if target.exists() else b''))
        try:audit(scratch,authority_root=root)
        except (AssertionError,OSError,subprocess.SubprocessError) as error:
            result.append({'probe':name,'result':'REJECTED','reason':str(error)[:500]})
        else:raise AssertionError('Scope mutation accepted: '+name)
        shutil.rmtree(scratch)
    return result
