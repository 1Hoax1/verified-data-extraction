"""Independent receipt review after attempted replacement of pin and P."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path('/workspace/p4-g3-limited-repin')
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'src')]
import scope_policy as scope
from p4.scope_audit import frozen_baseline

commands = []


def git(root, *args):
    argv = ['git', '-c', 'user.name=P4 isolated reviewer probe', '-c', 'user.email=p4-review@example.invalid', *args]
    p = subprocess.run(argv, cwd=root, capture_output=True)
    commands.append({'argv':argv,'cwd':str(root),'exit_code':p.returncode,
                     'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')})
    assert p.returncode == 0, p.stderr
    return p.stdout


def rejected(action):
    try:
        action()
    except AssertionError:
        return True
    raise AssertionError('Expected rejection was not observed')


head = git(ROOT,'rev-parse','HEAD').decode().strip()
tree = git(ROOT,'rev-parse','HEAD^{tree}').decode().strip()
receipt = json.loads((ROOT/'docs/p4/validation/P4_FINAL_MERGE_RECONCILIATION_G3_OWNER_AUTHORITY_RECEIPT.json').read_bytes())
before = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
          ('DECISIONS.md',scope.GOVERNANCE_PIN,'tests/scope_policy.py','tests/p4/scope_allowlist_v1.json')}

# Exercise the actual G2 -> G3 transition in scratch data only.
active = scope.verify_governance_document(ROOT)
assert all(active[key] == receipt[key] for key in ('approval_commit','decisions_blob','decisions_sha256','decisions_size_bytes','git_mode'))
with tempfile.TemporaryDirectory(prefix='p4-g3-transition-', dir='/tmp') as folder:
    scratch = Path(folder)
    copied = scratch/'DECISIONS.md'
    copied.write_bytes((ROOT/'DECISIONS.md').read_bytes())
    scope.verify_governance_document(scratch, authority_root=ROOT)
    copied.write_bytes(git(ROOT,'cat-file','blob',receipt['previous_approval_commit']+':DECISIONS.md'))
    assert rejected(lambda:scope.verify_governance_document(scratch, authority_root=ROOT))
    previous_pin = git(ROOT,'cat-file','blob','2ec6a895362f0b1b3a0d81a4930d623e00349441:'+scope.GOVERNANCE_PIN)
    target = scratch/scope.GOVERNANCE_PIN
    target.parent.mkdir(parents=True)
    target.write_bytes(previous_pin)
    assert rejected(lambda:scope.load_governance_pin(scratch))
transition = {'active_G3_matches_owner_receipt':'PASS','approved_G3_copy':'PASS','obsolete_G2_document':'REJECTED','obsolete_G2_pin':'REJECTED'}

with tempfile.TemporaryDirectory(prefix='p4-cr005-n09-',dir='/tmp') as folder:
    repo = Path(folder)/'disposable-git'
    git(Path(folder),'clone','--shared','--no-checkout','--quiet',str(ROOT),str(repo))
    git(repo,'switch','--detach','--quiet',head)
    document = repo/'DECISIONS.md'
    document.write_bytes(document.read_bytes()+b'\n# Unapproved isolated N09 fixture\n')
    git(repo,'add','--','DECISIONS.md')
    git(repo,'commit','--quiet','-m','Synthetic N09 document, not owner authorization')
    candidate = scope.load_governance_pin(ROOT)
    candidate.update(approval_commit=git(repo,'rev-parse','HEAD').decode().strip(),
        decisions_blob=git(repo,'rev-parse','HEAD:DECISIONS.md').decode().strip(),
        decisions_sha256=hashlib.sha256(document.read_bytes()).hexdigest(),
        decisions_size_bytes=document.stat().st_size)
    raw=(json.dumps(candidate,sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode()
    (repo/scope.GOVERNANCE_PIN).write_bytes(raw)
    assert rejected(lambda:scope.verify_governance_document(repo))
    with patch.object(scope,'GOVERNANCE_PIN_SHA256',hashlib.sha256(raw).hexdigest()):
        scope.verify_governance_document(repo)
        # P4's separate policy anchor still rejects the rewritten verifier P.
        assert rejected(lambda:frozen_baseline(repo))
        mismatch=[key for key in ('approval_commit','decisions_blob','decisions_sha256','decisions_size_bytes','git_mode')
                  if candidate[key]!=receipt[key]]
        assert mismatch
        assert rejected(lambda:scope._governance_require(not mismatch,'independent owner receipt mismatch'))
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected for name,expected in before.items())
assert git(ROOT,'rev-parse','HEAD').decode().strip()==head
assert not git(ROOT,'status','--porcelain').strip()
print(json.dumps({'case':'N09','result':'PASS','tested_commit':head,'tested_tree':tree,
    'without_rewritten_P':'REJECTED', 'isolated_verifier_after_rewriting_P':'MECHANICALLY_ACCEPTED; NOT_OWNER_APPROVAL',
    'independent_p4_policy':'REJECTED','independent_owner_receipt_comparison':'REJECTED',
    'mismatching_receipt_fields':mismatch,'real_inputs_unchanged':True,'G2_to_G3_transition':transition,'commands':commands},indent=2))
