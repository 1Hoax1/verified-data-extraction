"""Package immutable corrected evidence and separate post-publication proof."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path('/workspace/p6-streamlit-e2e')
WORK = Path('/workspace/p6-cr2-work')
EVIDENCE = ROOT / 'docs/p6/validation/runtime-20261107-cr-p6-002'
PUBLICATION = WORK / 'publication'


def main():
    publication = json.loads((PUBLICATION/'PUBLICATION_VERIFICATION_REPORT.json').read_text())
    summary = json.loads((EVIDENCE/'final-run/VALIDATION_SUMMARY.json').read_text())
    assert publication['result']=='PASS' and publication['main_unchanged'] and publication['validation_status']=='BLOCKED'
    implementation = summary['tested_commit']; head = publication['evidence_commit']
    assert implementation == publication['tested_implementation_commit']
    contents = {p.relative_to(ROOT).as_posix():p.read_bytes() for p in EVIDENCE.rglob('*') if p.is_file()}
    contents.update({'post-publication/'+p.relative_to(PUBLICATION).as_posix():p.read_bytes()
                     for p in PUBLICATION.rglob('*') if p.is_file()})
    contents['README_REVIEW_PACKAGE.md'] = f'''# CR-P6-002 correction review — P6 BLOCKED

Branch: {publication['branch_url']}.
Exact tested implementation: `{implementation}`.
Exact tested tree: `{summary['tested_tree']}`.
Subsequent evidence-only commit / published HEAD: `{head}`.

Read docs/p6/validation/runtime-20261107-cr-p6-002/P6_CR_P6_002_VALIDATION_REPORT.md.
The owner approved only the finite CR-P6-002 correction, not Gate B or release.
Certified old-ID and actual fresh UUID UI P-B now pass their strict XLSX/QA
oracles, with no changed acceptance expectation or substituted Approval.
The original defect is independently reproduced on its frozen implementation,
and prior FAILED evidence remains unchanged and available by immutable Git ref.

Actual P6 result: {summary['p6']['passed']} PASS / {summary['p6']['failed']} FAIL,
{summary['p6']['errors']} ERROR / {summary['p6']['skipped']} SKIP. Required actual
Mac-host Docker T19 is NOT RUN; Linux native/container proof does not replace it.
Use the Mac handoff to obtain raw real host, workflow, download and restart proof,
then record a separate T19 rerun without rewriting the earlier failed run.

Legacy scope failures remain real pytest FAIL with exact assertion and child
JUnit classification. Historical 212/212 and 76/76 results belong to their own
tested refs; no mixed all-green claim exists. The original 13 P-C files remain
absent. All current raw commands/logs/JUnit, test identities, guarded source diff,
resources, negatives, retired-policy provenance and SHA manifests are preserved.

The evidence-only descendant was checked for source identity, scope and published
bytes without claiming a new full runtime regression. No merge, governance repin,
Gate B closure, Pilot release, next stage or live owner Approval was performed.

The inner and outer manifests each exclude their own checksum. The outer ZIP
sidecar hashes actual archive bytes. Verify finite inventory and checksums after
extraction. Post-publication proof is separate from the earlier evidence commit.
'''.encode()
    names=sorted([*contents,'PACKAGE_FILES.txt','PACKAGE_MANIFEST.sha256'])
    contents['PACKAGE_FILES.txt']=''.join(p+'\n' for p in names).encode()
    manifest=''.join(hashlib.sha256(contents[p]).hexdigest()+'  '+p+'\n' for p in sorted(contents)).encode()
    contents['PACKAGE_MANIFEST.sha256']=manifest
    path=WORK/('P6_CR_P6_002_BLOCKED_'+implementation[:12]+'.zip');assert not path.exists()
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in sorted(contents):z.writestr(name,contents[name])
    with zipfile.ZipFile(path) as z:
        assert set(z.namelist())==set(names)
        for row in z.read('PACKAGE_MANIFEST.sha256').decode().splitlines():
            digest,name=row.split('  ',1);assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    (WORK/(path.name+'.sha256')).write_text(digest+'  '+path.name+'\n')
    result=dict(status='BLOCKED',archive=str(path),archive_sha256=digest,archive_bytes=path.stat().st_size,
        files=len(contents),manifest_entries=len(contents)-1,implementation_commit=implementation,evidence_commit=head)
    (WORK/'REVIEW_ARCHIVE_SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
