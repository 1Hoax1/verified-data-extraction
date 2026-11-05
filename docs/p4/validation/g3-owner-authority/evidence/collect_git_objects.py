"""Read remote immutable objects into a fresh, separate bare object database."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import subprocess

WORK = Path('/workspace/p4-g3-owner-authority-work')
BARE = WORK/'github-objects.git'
assert not BARE.exists(), 'Fresh verification object database required'
records = []


def run(argv, name):
    started = datetime.now(ZoneInfo('Europe/Moscow')).isoformat()
    result = subprocess.run(argv, cwd=WORK, capture_output=True)
    (WORK/(name+'.stdout.txt')).write_bytes(result.stdout)
    (WORK/(name+'.stderr.txt')).write_bytes(result.stderr)
    records.append({'argv':argv,'cwd':str(WORK),'started_at_moscow':started,
                    'exit_code':result.returncode,'stdout_file':name+'.stdout.txt','stderr_file':name+'.stderr.txt'})
    (WORK/'GIT_COLLECTION_COMMANDS.json').write_text(json.dumps(records,indent=2)+'\n')
    assert result.returncode == 0, name+' failed; see saved stderr'
    return result.stdout


run(['git','init','--bare',str(BARE)], 'git-init')
run(['git','-c','credential.helper=','-c','credential.helper=!gh auth git-credential',
     '-C',str(BARE),'fetch','--no-tags','https://github.com/1Hoax1/verified-data-extraction.git',
     'refs/heads/governance/p4-final-merge-reconciliation:refs/heads/verified-g3'], 'git-fetch')
sha = run(['git','--no-replace-objects','-C',str(BARE),'rev-parse','refs/heads/verified-g3'],'git-ref').decode().strip()
assert sha == 'd941714bc1d152d0a2189aa954e623460b4e6d03'
print(json.dumps({'status':'PASS','fresh_remote_object_database':str(BARE),'fetched_sha':sha,'remote_writes':False},indent=2))
