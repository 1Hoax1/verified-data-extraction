"""Verify fresh GitHub objects; prepare a review package outside the repository."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

WORK = Path('/workspace/p4-g3-owner-authority-work')
BARE = WORK/'github-objects.git'
SOURCE_REPO = Path('/workspace/p4-final-merge-reconciliation')
REVIEW = Path('/workspace/p4-g3-owner-authority-review')
V = Path('docs/p4/validation')
E = V/'g3-owner-authority'
RECEIPT = V/'P4_FINAL_MERGE_RECONCILIATION_G3_OWNER_AUTHORITY_RECEIPT.json'
G3 = 'd941714bc1d152d0a2189aa954e623460b4e6d03'
G2 = '27cdea7b204c36e839f1c3b1a8de387f64c0a91e'
PARENT = 'edc40399a4a5db448278edd098bff4307b308dbd'
EXPECTED_B = 'be002c5b196b3a374c39fe511d2e1c68477723ab'
EXPECTED_H = 'c76e162cca8e044dcc78d3f52a52b57fd230592b17249b6048f6f753618b6d18'
BRANCH = 'governance/p4-final-merge-reconciliation'
ROOT_API = 'https://api.github.com/repos/1Hoax1/verified-data-extraction/'
assert not REVIEW.exists(), 'Never overwrite an existing review package'


def api(name):
    return json.loads((WORK/'api'/(name+'.json')).read_bytes())


def git(*args):
    return subprocess.check_output(['git','--no-replace-objects','-C',str(BARE),*args])


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def object_hash(kind, raw):
    return hashlib.sha1(kind.encode()+b' '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def decode_blob(response):
    assert response['encoding'] == 'base64'
    raw = base64.b64decode(''.join(response['content'].split()),validate=True)
    assert response['size'] == len(raw)
    assert object_hash('blob',raw) == response['sha']
    return raw


g3, g2, parent = api('G3_COMMIT'), api('G2_COMMIT'), api('PARENT_COMMIT')
intermediate = api('INTERMEDIATE_COMMIT')
assert g3['sha'] == G3 and g2['sha'] == G2 and parent['sha'] == PARENT
assert [p['sha'] for p in g3['parents']] == [PARENT]
assert parent['parents'][0]['sha'] == intermediate['sha']
assert [p['sha'] for p in intermediate['parents']] == [G2]
assert len(g3['files']) == 1
change = g3['files'][0]
assert (change['filename'],change['status'],change['additions'],change['deletions']) == ('DECISIONS.md','modified',80,0)
assert change['sha'] == EXPECTED_B
for name in ['G3_BRANCH_REF','G3_BRANCH_REF_AFTER']:
    ref = api(name)
    assert ref['ref'] == 'refs/heads/'+BRANCH and ref['object']['sha'] == G3 and ref['object']['type'] == 'commit'
assert api('MAIN_REF_BEFORE')['object']['sha'] == api('MAIN_REF_AFTER')['object']['sha']
assert git('rev-parse','refs/heads/verified-g3').decode().strip() == G3
assert git('rev-parse','--is-shallow-repository').strip() == b'false'
assert not git('for-each-ref','refs/replace')
git('merge-base','--is-ancestor',G2,G3)
git('merge-base','--is-ancestor',PARENT,G3)
comparison, direct = api('COMPARE_G2_TO_G3'), api('COMPARE_PARENT_TO_G3')
assert comparison['status'] == 'ahead' and comparison['behind_by'] == 0
assert comparison['merge_base_commit']['sha'] == G2
assert direct['status'] == 'ahead' and direct['ahead_by'] == 1 and direct['total_commits'] == 1
assert direct['merge_base_commit']['sha'] == PARENT
assert len(direct['files']) == 1 and direct['files'][0]['filename'] == 'DECISIONS.md'

trees = {name:api(name+'_ROOT_TREE') for name in ['G3','G2','PARENT']}
for name, commit in [('G3',g3),('G2',g2),('PARENT',parent)]:
    assert not trees[name]['truncated']
    assert trees[name]['sha'] == commit['commit']['tree']['sha']
maps = {name:{x['path']:(x['mode'],x['type'],x['sha']) for x in response['tree']} for name,response in trees.items()}
assert maps['G3'].keys() == maps['PARENT'].keys()
different_roots = [p for p in maps['G3'] if maps['G3'][p] != maps['PARENT'][p]]
assert different_roots == ['DECISIONS.md']
assert maps['G3']['DECISIONS.md'] == ('100644','blob',EXPECTED_B)
assert maps['G2']['DECISIONS.md'] == maps['PARENT']['DECISIONS.md']
raw = decode_blob(api('G3_DECISIONS_BLOB'))
old = decode_blob(api('PARENT_DECISIONS_BLOB'))
assert len(raw) == 40572 and sha256(raw) == EXPECTED_H
assert api('G3_DECISIONS_BLOB')['sha'] == EXPECTED_B
assert api('PARENT_DECISIONS_BLOB')['sha'] == maps['PARENT']['DECISIONS.md'][2]
assert git('cat-file','blob',EXPECTED_B) == raw
assert git('show',G2+':DECISIONS.md') == git('show',PARENT+':DECISIONS.md') == old
source = Path('/workspace/p4-merge-reconciliation-review/APPROVED_RECORD.md').read_bytes()
assert len(source) == 3616 and sha256(source) == 'e07d23cd122202e2fec7d3032e2296804772c1d60a8d6f11ff56f9734a7eb607'
assert raw == old+b'\n'+source
assert b'**Decision status:** PROPOSED' in source
assert G3.encode() not in raw and EXPECTED_H.encode() not in raw
assert git('diff','--name-status','--no-renames',PARENT,G3).decode().splitlines() == ['M\tDECISIONS.md']
assert git('diff','--numstat',PARENT,G3).decode().strip() == '80\t0\tDECISIONS.md'
assert hashlib.sha256(b'abc').hexdigest() == 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'

REVIEW.mkdir()
(REVIEW/E/'evidence').mkdir(parents=True)
shutil.copytree(WORK/'api',REVIEW/E/'evidence/api')
for name in ['API_COLLECTION_COMMANDS.json','GIT_COLLECTION_COMMANDS.json','WORKTREE_BEFORE.json',
             'git-init.stdout.txt','git-init.stderr.txt','git-fetch.stdout.txt','git-fetch.stderr.txt','git-ref.stdout.txt','git-ref.stderr.txt']:
    shutil.copyfile(WORK/name,REVIEW/E/'evidence'/name)
shutil.copyfile(WORK/'fetch_objects.py',REVIEW/E/'evidence/collect_git_objects.py')
shutil.copyfile(Path(__file__),REVIEW/E/'evidence/prepare_review_package.py')

def save(name,data):
    path = REVIEW/E/'evidence'/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)

objects = []
def record_object(label,kind,sha):
    data = git('cat-file',kind,sha)
    assert object_hash(kind,data) == sha
    save('git/'+label+'.'+kind+'.raw',data)
    objects.append({'label':label,'type':kind,'git_sha1':sha,'payload_bytes':len(data),'payload_sha256':sha256(data)})
    return data

for name,response in [('G2',g2),('INTERMEDIATE',intermediate),('PARENT',parent),('G3',g3)]:
    data = record_object(name,'commit',response['sha'])
    headers = data.split(b'\n\n',1)[0].splitlines()
    parents = [x[7:].decode() for x in headers if x.startswith(b'parent ')]
    assert parents == [x['sha'] for x in response['parents']]
    assert next(x[5:].decode() for x in headers if x.startswith(b'tree ')) == response['commit']['tree']['sha']
for name,response in trees.items():record_object(name,'tree',response['sha'])
record_object('G3_DECISIONS','blob',EXPECTED_B)
record_object('G2_AND_PARENT_DECISIONS','blob',maps['PARENT']['DECISIONS.md'][2])
save('G3_DECISIONS.exact.md',raw)
save('G2_AND_PARENT_DECISIONS.exact.md',old)
save('APPROVED_RECONCILIATION_SOURCE.md',source)
save('G3_PARENT.diff',git('diff','--no-ext-diff','--no-color',PARENT,G3,'--','DECISIONS.md'))
save('G3_ROOT_TREE.txt',git('ls-tree',G3))
save('G2_TO_G3_ANCESTRY.txt',git('rev-list','--ancestry-path','--parents',G2+'..'+G3))
sum_command=['sha256sum',str(REVIEW/E/'evidence/G3_DECISIONS.exact.md')]
sum_result=subprocess.run(sum_command,capture_output=True)
assert sum_result.returncode == 0 and sum_result.stdout.decode().split()[0] == EXPECTED_H
save('sha256sum.stdout.txt',sum_result.stdout)
save('sha256sum.stderr.txt',sum_result.stderr)
save('sha256sum.command.json',(json.dumps({'argv':sum_command,'exit_code':sum_result.returncode},indent=2)+'\n').encode())
save('GIT_OBJECT_IDENTITIES.json',(json.dumps(objects,indent=2)+'\n').encode())

before = json.loads((WORK/'WORKTREE_BEFORE.json').read_bytes())
after={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE_REPO,text=True).strip(),
       'status':subprocess.check_output(['git','status','--porcelain'],cwd=SOURCE_REPO,text=True),
       'protected_worktree_sha256':{name:sha256((SOURCE_REPO/name).read_bytes()) for name in before['protected_worktree_sha256']}}
assert after['head'] == before['head'] and after['status'] == before['status'] == ''
assert after['protected_worktree_sha256'] == before['protected_worktree_sha256']
save('WORKTREE_AFTER.json',(json.dumps(after,indent=2)+'\n').encode())
verified_at=datetime.now(ZoneInfo('Europe/Moscow')).isoformat()
lineage=[G2,intermediate['sha'],PARENT,G3]
root_identity={path:{'parent':maps['PARENT'][path],'G3':maps['G3'][path],'unchanged':maps['PARENT'][path]==maps['G3'][path]}
               for path in maps['G3']}
technical={'status':'PASS','verified_at_moscow':verified_at,
    'method':'Fresh GitHub REST GET responses plus fresh full Git fetch into a separate bare repository; recompute exact canonical commit/tree/blob Git SHA-1 and document SHA-256.',
    'direct_parent':PARENT,'G2_to_G3_first_parent_lineage':lineage,
    'API_compare_G2_to_G3':{'status':comparison['status'],'merge_base':comparison['merge_base_commit']['sha'],'ahead_by':comparison['ahead_by'],'behind_by':comparison['behind_by']},
    'root_entry_comparison':root_identity,'different_root_paths':different_roots,
    'G3_change':{'path':'DECISIONS.md','added_lines':80,'removed_lines':0},
    'exact_approved_source':{'sha256':sha256(source),'size_bytes':len(source),'baseline_prefix_bytes_preserved':len(old),'separator_bytes':1,'entire_document_is_baseline_plus_exact_source':True},
    'canonical_Git_objects_rehashed':len(objects),'document_sha256_verified_by':['Python hashlib','sha256sum'],
    'publication_source_branch_unchanged':True,'observed_main_sha_unchanged':api('MAIN_REF_AFTER')['object']['sha'],
    'protected_worktree_unchanged':True,'new_212_test_regression':'NOT_RUN; no new runtime acceptance claimed',
    'independence_scope':'Independent fresh-object recomputation of previous claims; same Codex/execution environment, not a new independent human approval or second-host test run.'}
(REVIEW/E/'TECHNICAL_VERIFICATION.json').write_text(json.dumps(technical,ensure_ascii=False,indent=2)+'\n')
receipt={
    'status':'PREPARED_FOR_MAIN_MANAGING_CHAT_REVIEW; NOT_PUBLISHED',
    'record':'P4_FINAL_MERGE_RECONCILIATION_G3_OWNER_AUTHORITY_RECEIPT',
    'repository':'1Hoax1/verified-data-extraction','path':'DECISIONS.md',
    'implementation_baseline':'7685110506d115805c473b064752f86e9e5c045b',
    'previous_approval_commit':G2,'approval_commit':g3['sha'],
    'decisions_blob':api('G3_DECISIONS_BLOB')['sha'],'decisions_sha256':sha256(raw),
    'decisions_size_bytes':len(raw),'git_mode':maps['G3']['DECISIONS.md'][0],
    'governance_commit_branch':BRANCH,
    'owner_authority':{
        'existing_decision_status':'APPROVED','decision_date':'2026-11-02',
        'source':'Main Managing Chat — Part 2; explicit owner confirmation supplied by the user in this conversation',
        'approval_quote':'Утверждаю запись P4 Final Merge Reconciliation в предложенной редакции',
        'approved_text_sha256':sha256(source),'approved_text_size_bytes':len(source),
        'historical_PROPOSED_status_preserved':True,
        'status_explanation':'The supplied original proposal retained PROPOSED wording; its later actual approval is the accompanying owner confirmation. No source wording was changed.',
        'exact_G3_publication_separately_authorized':True,
        'publication_scope':'The prior owner authorization covered publication of the exact G3 commit in an isolated branch; it is not authorization to publish this prepared receipt or to merge.',
        'new_owner_decision_created_by_verification':False},
    'technical_verification':{
        'status':'PASS','verified_at_moscow':verified_at,'direct_parent':PARENT,
        'previous_G2_is_ancestor':True,'first_parent_lineage':lineage,
        'exact_Git_commit_tree_blob_identity_verified':True,'exact_document_sha256_size_mode_verified':True,
        'exact_approved_record_verified':True,'G3_changed_paths':['DECISIONS.md'],
        'unauthorized_production_contract_fixture_test_migration_dependency_changes':False,
        'report_path':str(E/'INDEPENDENT_VERIFICATION_REPORT.md'),
        'manifest_path':str(E/'MANIFEST.sha256'),
        'authority_distinction':'Git object verification confirms identity/content/ancestry; the existing owner decision is sourced from explicit owner instructions, not inferred from commit authorship or an APPROVED string.'},
    'preparation_scope':{
        'receipt_published':False,'new_repository_commit_created':False,'DECISIONS_modified':False,
        'active_G2_pin_or_test_policies_modified':False,'governance_repin_performed':False,
        'production_tests_contracts_fixtures_migrations_dependencies_modified':False,
        'main_merge_performed':False,'P5_started_or_authorized':False,
        'new_212_test_regression':'NOT_RUN'},
    'review_and_follow_up':{
        'destination':'Main Managing Chat — Part 2','receipt_publication':'PENDING_REVIEW; NOT_PERFORMED',
        'proposed_repository_path':str(RECEIPT),
        'procedure_path':str(E/'PUBLICATION_PROCEDURE.md'),
        'binding_procedure':'Existing approved CR-P4-005 limited governance repin procedure remains binding. No automatic repin or automatic latest-main trust.'}}
(REVIEW/RECEIPT).parent.mkdir(parents=True,exist_ok=True)
(REVIEW/RECEIPT).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')

report=f'''# G3 owner-authority receipt — independent technical verification

**Result: PASS. Receipt status: PREPARED FOR MAIN MANAGING CHAT REVIEW / NOT PUBLISHED.** Verification timestamp (Europe/Moscow): {verified_at}.

This report recomputes the expected identities from freshly retrieved immutable GitHub objects and a separate fresh bare Git object database. It does not reuse an earlier receipt as technical proof. It is performed in the same Codex environment: this is an independent data/method check, not a new independent human approval, second-host execution or application regression.

## Verified values

| Field | Verified value |
|---|---|
| G3 | `{G3}` |
| B3 | `{EXPECTED_B}` |
| H3 | `{EXPECTED_H}` |
| L3 | {len(raw)} bytes |
| M | `100644` |
| G3 tree | `{trees['G3']['sha']}` |
| Direct parent | `{PARENT}` |
| Previous G2 authority | `{G2}` |

All values match the task's expected values. The source branch `governance/p4-final-merge-reconciliation` resolved to G3 before and after collection. The observed main ref remained `{api('MAIN_REF_AFTER')['object']['sha']}`. These refs are observations, not moving sources of authority: the receipt is bound only to the immutable G3 object.

## Exact identity and ancestry evidence

GitHub REST responses are retained under `evidence/api/`; actual GET commands are in `evidence/API_COLLECTION_COMMANDS.json`. A fresh full `git fetch` into an isolated bare repository supplied canonical object payloads. Commands/stdout/stderr are retained; no existing project worktree/config was used as the object source or changed by the fetch.

The canonical Git headers and payloads for {len(objects)} commit/tree/blob objects were independently rehashed with Git SHA-1 framing, including G3, G2 and the complete short first-parent path. Their raw bytes and hash/size inventory are under `evidence/git/` and `evidence/GIT_OBJECT_IDENTITIES.json`. Git SHA-1 identities agree with both GitHub REST and the freshly fetched object database. The API-decoded exact B3 bytes match the fetched Git blob. H3 was recomputed by both Python hashlib and `sha256sum`, without Unicode, decoding or newline transformations. Git mode is independently confirmed in both GitHub root-tree data and the fetched tree.

The verified first-parent lineage is:

`{G2}` → `{intermediate['sha']}` → `{PARENT}` → `{G3}`.

GitHub compare reports G2 as the merge base, status `ahead`, ahead_by {comparison['ahead_by']}, behind_by 0; fresh Git `merge-base --is-ancestor` also passes. Parent→G3 compare reports exactly one commit. Merge-parent arrays are cross-checked against canonical commit headers; ancestry is preserved, not inferred from commit titles.

## Exact approved text and bounded change

The source is the owner-supplied reconciliation record from Main Managing Chat — Part 2, preserved as `evidence/APPROVED_RECONCILIATION_SOURCE.md`: {len(source)} bytes, SHA-256 `{sha256(source)}`. The G3 document is **exactly the entire {len(old)}-byte parent document + one separator newline + that exact approved record**. The parent's document is also exactly the G2-authorized document. No historical byte was rewritten. API and Git agree: `DECISIONS.md` only, +80/−0 lines.

The historical `Decision status: PROPOSED — pending explicit owner approval` is intentionally untouched. The owner later explicitly confirmed **«Утверждаю запись P4 Final Merge Reconciliation в предложенной редакции»** on 2026-11-02, as supplied in this conversation. The receipt records that already-existing APPROVED decision; it does not replace source wording or invent a new approval. Neither G3 nor H3 is written into DECISIONS.

## No unauthorized changes

Complete non-truncated parent/G3 root-tree inventories have the same paths. Every entry except DECISIONS has identical mode/type/Git SHA. Equal subtree hashes preserve all production, tests, fixtures, contracts, migrations, dependencies, approved packages and historical validation evidence recursively. The detailed comparison is in `TECHNICAL_VERIFICATION.json`; fresh Git's full-tree diff also confirms the singleton path.

This change-scope assertion is **G3 versus its direct parent**. The broader G2→G3 ancestry includes the previously performed P4 integration; those earlier authorized changes are not falsely attributed to the G3 reconciliation commit.

Existing project worktree HEAD/status and DECISIONS/active-pin/verifier/P4-policy hashes match the pre-task snapshot. No code/test/pin/policy/DECISIONS mutation, commit, push, PR merge or P5 action was performed. The only Git writes were fetching existing remote objects into the separate verification database. Raw GitHub reads were GET operations only.

## Authority distinction and limitations

GitHub objects establish document identity, content and history; they do not authenticate a private human approval message. Owner authority is the explicit instruction supplied by the user, separately recorded in the receipt. The prior authorization to publish G3 covered that exact isolated-branch commit; it does not authorize publishing this receipt, modifying main, performing repin or starting P5.

The active pin still points to G2 and does not cover the G3 document. This task prepares the authority data needed by the binding CR-P4-005 follow-up; no repin is claimed complete. No pytest or new 212-test regression was run. The original reconciliation's historical acceptance statements remain historical, not new runtime evidence.

## Review handoff

Prepared JSON: `{RECEIPT}`. Exact proposed evidence paths are listed in `PROPOSED_PUBLICATION_FILES.txt`; publication steps are in `PUBLICATION_PROCEDURE.md`. The SHA-256 manifest covers the JSON receipt and all package files except the manifest itself, using paths relative to the proposed repository root. No file contains its own checksum or its own future publication commit SHA.

**Return this package to Main Managing Chat — Part 2. Stop before publication, owner-authority receipt commit, governance repin, main merge or P5.**
'''
(REVIEW/E/'INDEPENDENT_VERIFICATION_REPORT.md').write_text(report)
procedure=f'''# Proposed paths and publication procedure — not executed

Status: **review package only**. Existing owner approval applies to the reconciliation and publication of G3. Publication of this prepared receipt/evidence is a later operation after Main Managing Chat — Part 2 review and an appropriate explicit instruction.

## Exact proposed paths

- JSON receipt: `{RECEIPT}`.
- Verification report: `{E}/INDEPENDENT_VERIFICATION_REPORT.md`.
- Technical results: `{E}/TECHNICAL_VERIFICATION.json`.
- This procedure: `{E}/PUBLICATION_PROCEDURE.md`.
- Complete file inventory: `{E}/PROPOSED_PUBLICATION_FILES.txt`.
- SHA-256 manifest: `{E}/MANIFEST.sha256`.
- Exact raw evidence and collection/verification scripts: the individually enumerated paths under `{E}/evidence/` in the complete file inventory. The inventory is exact; this description is not a wildcard authorization.

The supplied review archive mirrors those repository paths under `docs/`. Its complete file inventory includes every proposed artifact. No change belongs to DECISIONS, tests, pin/policies, runtime, contracts, old evidence, dependencies or migrations.

## Later publication, only after review/authorization

1. Reconfirm the immutable source G3 `{G3}` and its G2 ancestry. Do not amend, rebase, squash or recreate G3; do not substitute latest main or a newer DECISIONS version.
2. Create a **new isolated evidence-publication branch** `governance/p4-g3-owner-authority-receipt` from exact G3. Keep the existing source branch unchanged. The new branch name is proposed here; it has not been created.
3. Copy only the exact reviewed files from this package to their listed paths. From the repository root run `sha256sum -c {E}/MANIFEST.sha256`. Compare the staged file set with `PROPOSED_PUBLICATION_FILES.txt`; every path must be a new receipt/evidence artifact, with staged bytes matching the manifest. No source/governance document changes or pre-existing-file overwrites are allowed.
4. Create one separate **receipt/evidence-only commit R3**, direct child of G3. R3 adds the receipt and listed evidence only. Do not write R3's own SHA, the receipt's own hash, the manifest hash or any new authority value back into DECISIONS. The receipt and manifest contain no self-hashes; the manifest excludes itself.
5. Verify G3→R3 ancestry, unchanged G3/B3/H3/L3/M and an exact allowed-file diff. Independently verify committed Git blob bytes against the manifest and the owner's reviewed package.
6. If publication is authorized, push only that new isolated evidence branch. Verify R3 SHA/parent/paths and receipt bytes through GitHub API; verify main, the original G3 source branch and active G2 pin remain unchanged. Do not create or merge a PR automatically. Report R3 outside DECISIONS and outside the receipt; no self-reference is needed.
7. Return the published evidence identities to Main Managing Chat — Part 2. **Stop before governance repin.** A later separately instructed limited-repin task can consume the verified G3 tuple under approved CR-P4-005, update only the permitted active pin/references and perform the required regression. This receipt does not grant P5 authorization or merge permission.

No command in this proposed procedure has been executed as a publication operation during preparation. Current repository files and refs were not changed; a separate bare verification database was used solely to read remote objects.
'''
(REVIEW/E/'PUBLICATION_PROCEDURE.md').write_text(procedure)
files={p.relative_to(REVIEW).as_posix() for p in REVIEW.rglob('*') if p.is_file()}
inventory=(E/'PROPOSED_PUBLICATION_FILES.txt').as_posix()
manifest=(E/'MANIFEST.sha256').as_posix()
files|={inventory,manifest}
(REVIEW/inventory).write_text(''.join(name+'\n' for name in sorted(files)))
hash_names=sorted(files-{manifest})
(REVIEW/manifest).write_text(''.join(sha256((REVIEW/name).read_bytes())+'  '+name+'\n' for name in hash_names))
assert {p.relative_to(REVIEW).as_posix() for p in REVIEW.rglob('*') if p.is_file()} == files
for line in (REVIEW/manifest).read_text().splitlines():
    value,name=line.split('  ',1)
    assert sha256((REVIEW/name).read_bytes()) == value,name
archive=Path('/workspace/P4_G3_OWNER_AUTHORITY_REVIEW_d941714bc1d1.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name in sorted(files):z.write(REVIEW/name,arcname='p4-g3-owner-authority-review/'+name)
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(json.dumps({'status':'PREPARED_FOR_REVIEW; NOT_PUBLISHED','receipt':str(REVIEW/RECEIPT),
    'report':str(REVIEW/E/'INDEPENDENT_VERIFICATION_REPORT.md'),'G3':G3,'B3':EXPECTED_B,'H3':EXPECTED_H,'L3':len(raw),'M':'100644',
    'canonical_Git_objects_rehashed':len(objects),'package_files':len(files),'manifest_entries_verified':len(hash_names),
    'archive':str(archive),'archive_sha256':sha256(archive.read_bytes()),'repo_changes':0,'publication_or_repin_performed':False},indent=2))
