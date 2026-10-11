import hashlib
import json
from pathlib import Path
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='session')
def p3_pack(tmp_path_factory):
    archive = ROOT / 'docs/p3/v1.0/P3_Implementation_Pack_v1.0_APPROVED.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == '8a77848419161a5f784b61e7302a058e5c23e2ff5925e88a643c350e80930bc7'
    root = tmp_path_factory.mktemp('p3-approved')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        z.extractall(root)
    root /= 'P3_Implementation_Pack_v1.0_APPROVED'
    manifest = json.loads((root / 'PACK_MANIFEST.json').read_text())
    assert len(manifest['files']) == 64
    for item in manifest['files']:
        data = (root / item['path']).read_bytes()
        assert len(data) == item['size_bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
    (ROOT / 'docs/p3/validation/scenario-results.json').write_text('{}\n')
    return root


def pytest_collection_modifyitems(items):
    for item in items:
        if '/p3/' in str(item.path) and item.name.startswith('test_T'):
            item.user_properties.append(('p3_id', 'P3-T' + item.name.split('_')[1][1:]))
