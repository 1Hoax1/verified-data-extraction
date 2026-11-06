import hashlib
import json
from pathlib import Path
import zipfile
import pytest

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture(scope='session')
def design(tmp_path_factory):
    archive=ROOT/'docs/p5/handoff/P5_Codex_Implementation_Handoff_2026-11-05.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()=='3e3a2f6a8e65f500fe5bd281ef805d9229d50b96c50433cdda52cbb4fd6d63e4'
    target=tmp_path_factory.mktemp('p5-design')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        z.extractall(target)
    handoff=target/'P5_Codex_Implementation_Handoff_2026-11-05'
    for row in (handoff/'HANDOFF_MANIFEST.sha256').read_text().splitlines():
        digest,name=row.split('  ',1)
        assert hashlib.sha256((handoff/name).read_bytes()).hexdigest()==digest
    roots={}
    for key,name in [('base','P5_Implementation_Design_Pack_v0.2a_candidate'),('pb','P5_Gate_A_PB_Supplement_v0.2b_candidate')]:
        with zipfile.ZipFile(handoff/'sources'/(name+'.zip')) as z:
            assert z.testzip() is None
            z.extractall(target)
        root=target/name
        for f in json.loads((root/'PACK_MANIFEST.json').read_text())['files']:
            assert hashlib.sha256((root/f['path']).read_bytes()).hexdigest()==f['sha256']
        roots[key]=root
    roots['handoff']=handoff
    return roots


def pytest_collection_modifyitems(items):
    for item in items:
        if '/p5/' in str(item.path):
            import re
            match=re.search(r'T(\d{2})',item.name)
            if match:
                item.user_properties.append(('p5_id','P5-T'+match[1]))
