"""Package the committed BLOCKED P6 report and separate publication proof."""
from pathlib import Path
import hashlib
import json
import zipfile

REPO = Path('/workspace/p6-streamlit-e2e')
WORK = Path('/workspace/p6-work')
EV = REPO / 'docs/p6/validation/runtime-20261107'
PUB = WORK / 'publication'


def main():
    publication = json.loads((PUB / 'PUBLICATION_VERIFICATION_REPORT.json').read_text())
    assert publication['result']=='PASS' and publication['main_unchanged']
    assert publication['validation_status']=='BLOCKED'
    summary = json.loads((EV / 'final-run/VALIDATION_SUMMARY.json').read_text())
    implementation = summary['tested_commit']; evidence = publication['evidence_commit']
    assert implementation == publication['tested_implementation_commit']
    contents = {}
    for p in EV.rglob('*'):
        if p.is_file(): contents[p.relative_to(REPO).as_posix()] = p.read_bytes()
    for p in PUB.rglob('*'):
        if p.is_file(): contents['post-publication/' + p.relative_to(PUB).as_posix()] = p.read_bytes()
    contents['README_REVIEW_PACKAGE.md'] = f'''# P6 implementation review package — BLOCKED

Branch: {publication['branch_url']}.
Tested implementation: `{implementation}`.
Tested tree: `{summary['tested_tree']}`.
Subsequent evidence-only commit / published HEAD: `{evidence}`.

Start with `docs/p6/validation/runtime-20261107/P6_VALIDATION_REPORT.md` and
`CR-P6-002_PROPOSED.md`. The proposal is not approved or implemented.

Actual P6 outcome: {summary['p6']['passed']} PASS / {summary['p6']['failed']} FAIL,
{summary['p6']['errors']} ERROR / {summary['p6']['skipped']} SKIP, all 20 IDs.
P-B's correctly identity-adapted UUID Brief exposes frozen P5's literal
brief-pb-v1 recognition restriction; failed DQ-010/NEEDS_FIX is retained.
Mac-host Docker execution is NOT RUN. Actual Linux native/container checks
do not replace Mac evidence or owner browser acceptance.

Historical approved P1-P4 212/212 and P5 76/76 remain tied to their original
tested refs. On the actual P6 tree, legacy failures remain genuine pytest
FAIL with independently proven EXPECTED_HISTORICAL_SCOPE_CONFLICT; no
combined all-green claim is made. Full raw commands, exits, stdout/stderr,
JUnit, protected-file hashes, HTTP/resource observations and proposal are
included. Thirteen original P-C files remain absent.

The evidence-only child has identical source/tests to the tested implementation;
its scope/hashes/published bytes were checked without claiming a full new
runtime regression. No P6 VALIDATED, Gate B closure, merge, governance repin,
Pilot release, next stage or live business Approval was performed.

The inner evidence manifest uses repository-relative paths and excludes itself.
The outer PACKAGE_MANIFEST.sha256 covers this package and post-publication
proof, excluding only its own checksum. Verify hashes after extraction. The
external ZIP SHA-256 sidecar covers the actual archive bytes.
'''.encode('utf-8')
    inventory = sorted([*contents, 'PACKAGE_FILES.txt', 'PACKAGE_MANIFEST.sha256'])
    contents['PACKAGE_FILES.txt'] = ''.join(p+'\n' for p in inventory).encode()
    manifest = ''.join(hashlib.sha256(contents[p]).hexdigest()+'  '+p+'\n' for p in sorted(contents)).encode()
    contents['PACKAGE_MANIFEST.sha256'] = manifest
    path = WORK / ('P6_IMPLEMENTATION_BLOCKED_' + implementation[:12] + '.zip')
    assert not path.exists()
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(contents): z.writestr(name, contents[name])
    with zipfile.ZipFile(path) as z:
        assert set(z.namelist()) == set(inventory)
        for row in z.read('PACKAGE_MANIFEST.sha256').decode().splitlines():
            checksum, name = row.split('  ',1)
            assert hashlib.sha256(z.read(name)).hexdigest()==checksum,name
    checksum=hashlib.sha256(path.read_bytes()).hexdigest()
    (WORK/(path.name+'.sha256')).write_text(checksum+'  '+path.name+'\n')
    (WORK/(path.stem+'.MANIFEST.sha256')).write_bytes(manifest)
    result=dict(status='BLOCKED',archive=str(path),archive_bytes=path.stat().st_size,
                archive_sha256=checksum,files=len(contents),manifest_passes=len(contents)-1,
                implementation_commit=implementation,evidence_commit=evidence)
    (WORK/'REVIEW_ARCHIVE_SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
