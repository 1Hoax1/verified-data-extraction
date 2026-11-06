"""Read-only check of the original approved handoff bytes and 10 manifest entries."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys
import zipfile

repo = Path('/workspace/p5-export-deterministic-qa')
path = repo / 'docs/p5/handoff/P5_Codex_Implementation_Handoff_2026-11-05.zip'
raw = path.read_bytes()
digest = hashlib.sha256(raw).hexdigest()
assert digest == '3e3a2f6a8e65f500fe5bd281ef805d9229d50b96c50433cdda52cbb4fd6d63e4'
records = []
with zipfile.ZipFile(path) as z:
    manifest = 'P5_Codex_Implementation_Handoff_2026-11-05/HANDOFF_MANIFEST.sha256'
    root = PurePosixPath(manifest).parent
    manifest_raw = z.read(manifest)
    for line in manifest_raw.decode().splitlines():
        if not line:
            continue
        expected, rel = line.split('  ', 1)
        data = z.read(str(root / rel))
        actual = hashlib.sha256(data).hexdigest()
        assert actual == expected, rel
        records.append(dict(path=rel, sha256=actual, size=len(data), result='PASS'))
    assert len(records) == 10
print(json.dumps(dict(result='PASS', archive_sha256=digest, entries=10,
      manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
      tested_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
      observed_at_utc=datetime.now(timezone.utc).isoformat(), python=sys.version,
      note='The packaged old summary says 9; the actual complete manifest has 10 entries.', records=records), indent=2))
