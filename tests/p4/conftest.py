import hashlib
import json
from pathlib import Path
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='session')
def p4_pack(tmp_path_factory):
    archive = ROOT/'docs/p4/v1.0/P4_Implementation_Pack_v1.0_APPROVED.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == 'e3c686f81e3ba0d63874420d0f67f7585b9861826fdbc8a76dfb6a5d8f2aa5aa'
    target = tmp_path_factory.mktemp('p4-approved')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        z.extractall(target)
    pack = target/'P4_Implementation_Pack_v1.0_APPROVED'
    manifest = json.loads((pack/'PACK_MANIFEST.json').read_text())
    assert len(manifest['files']) == 53
    for entry in manifest['files']:
        data = (pack/entry['path']).read_bytes()
        assert len(data) == entry['size_bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256']
    return pack


def pytest_collection_modifyitems(items):
    for item in items:
        if '/p4/' in str(item.path) and item.name.startswith('test_T'):
            item.user_properties.append(('p4_id', 'P4-T'+item.name.split('_')[1][1:]))
