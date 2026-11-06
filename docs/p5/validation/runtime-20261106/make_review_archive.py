"""Package immutable committed P5 evidence plus separate post-publication checks."""
from pathlib import Path
import hashlib
import json
import zipfile

repo = Path('/workspace/p5-export-deterministic-qa')
work = Path('/workspace/p5-resume-work')
evidence = repo / 'docs/p5/validation/runtime-20261106'
publication = work / 'publication'
report = json.loads((publication / 'PUBLICATION_VERIFICATION_REPORT.json').read_text())
assert report['result'] == 'PASS' and report['main_unchanged']
implementation = report['tested_implementation_commit']
head = report['evidence_commit']
members = {}
for path in evidence.rglob('*'):
    if path.is_file():
        members[path.relative_to(repo).as_posix()] = path.read_bytes()
for path in publication.rglob('*'):
    if path.is_file():
        members['post-publication/' + path.relative_to(publication).as_posix()] = path.read_bytes()
members['REVIEW_PACKAGE_README.md'] = f'''# P5 technical validation review package

Tested implementation: `{implementation}`.
Tested tree: `{report['tested_implementation_tree']}`.
Subsequent evidence-only commit / published branch HEAD: `{head}`.
Branch: {report['branch_url']}.

Read `docs/p5/validation/runtime-20261106/P5_VALIDATION_REPORT.md` first.
Its MANIFEST.sha256 uses repository-relative paths and excludes only itself.
The package-level manifest covers the new evidence and separate post-publication
GitHub/API/bare-fetch checks; it excludes only its own checksum.

There are three deliberately separate result families: 212/212 historical tests
at the approved frozen base, 206 PASS plus six actual pytest scope failures on
P5 classified EXPECTED_HISTORICAL_SCOPE_CONFLICT, and all 76 P5 runtime IDs PASS.
CSV/XLSX stress both actually completed 100000x200 with every cell independently
checked and sampled P5 incremental RSS within 512 MiB. The evidence-only child
was checked for byte identity, scope and hashes; its full runtime suite was not
rerun. Do not attribute the implementation runtime run to that child.

Original approved source ZIPs and P0-P4 contracts/tests remain unchanged.
Thirteen certified historical P-C originals remain missing and are not claimed
as tested. P-B v2 mechanics use isolated simulated workflow actions; a live
business operation still needs its own exact real Approval. Earlier failed
attempts and dirty development diagnostics are preserved with their real status.

Technical result only: no owner acceptance or Gate B closure. No merge into main,
governance repin, P6 design or implementation was performed. Remote main remained
`{report['remote_main_after']}`.
'''.encode()
inventory = sorted([*members, 'REVIEW_PACKAGE_FILES.txt', 'REVIEW_PACKAGE_MANIFEST.sha256'])
members['REVIEW_PACKAGE_FILES.txt'] = ''.join(p + '\n' for p in inventory).encode()
manifest = ''.join(hashlib.sha256(members[p]).hexdigest() + '  ' + p + '\n'
                   for p in sorted(members)).encode()
members['REVIEW_PACKAGE_MANIFEST.sha256'] = manifest
archive = work / ('P5_VALIDATION_REVIEW_' + implementation[:12] + '.zip')
assert not archive.exists()
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for path in sorted(members):
        z.writestr(path, members[path])
with zipfile.ZipFile(archive) as z:
    assert set(z.namelist()) == set(inventory)
    for line in z.read('REVIEW_PACKAGE_MANIFEST.sha256').decode().splitlines():
        digest, path = line.split('  ', 1)
        assert hashlib.sha256(z.read(path)).hexdigest() == digest, path
archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
(work / (archive.name + '.sha256')).write_text(archive_hash + '  ' + archive.name + '\n')
(work / (archive.stem + '.MANIFEST.sha256')).write_bytes(manifest)
summary = dict(archive=str(archive), archive_sha256=archive_hash,
    archive_members=len(members), package_manifest_passes=len(members)-1,
    package_manifest_sha256=hashlib.sha256(manifest).hexdigest(),
    implementation_commit=implementation, evidence_commit=head)
(work / 'REVIEW_ARCHIVE_SUMMARY.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
