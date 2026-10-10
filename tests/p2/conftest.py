"""Extract the approved archive into pytest temp storage; never mutate it."""
import hashlib
import json
from pathlib import Path
import zipfile
import pytest
from vde.bootstrap import bootstrap
from vde.config import Config
from vde.models import OrderRecord
from vde.persistence.uow import UnitOfWork
from vde.ingestion.local import LocalIngestion

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='session')
def pack(tmp_path_factory):
    archive = ROOT / 'docs/p2/v1.0/P2_Implementation_Pack_v1.0_APPROVED.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == '1fed602bcea695be892150581b9cbcb00807681f0a389f598bd54fac9e504d84'
    directory = tmp_path_factory.mktemp('approved-pack')
    with zipfile.ZipFile(archive) as z:
        z.extractall(directory)
    directory /= 'P2_Implementation_Pack_v1.0_APPROVED'
    manifest = json.loads((directory / 'PACK_MANIFEST.json').read_text())
    assert len(manifest['files']) == 57
    for record in manifest['files']:
        data = (directory / record['path']).read_bytes()
        assert len(data) == record['size_bytes']
        assert hashlib.sha256(data).hexdigest() == record['sha256'], record['path']
    return directory


@pytest.fixture
def env(tmp_path):
    result = bootstrap(Config(tmp_path / 'workspace'))
    assert result.health == 'ready'
    with UnitOfWork(result.database, result.workspace) as uow:
        for identity in ['order-p2', 'order-other']:
            uow.orders.add(OrderRecord(identity, identity, 'local test input', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z'))
    return result


@pytest.fixture
def service(env):
    return LocalIngestion(env)


def pytest_collection_modifyitems(items):
    for item in items:
        if '/p2/' in str(item.path) and item.name.startswith('test_T'):
            item.user_properties.append(('p2_id', 'P2-T' + item.name.split('_')[1][1:]))
