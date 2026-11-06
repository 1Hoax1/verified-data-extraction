import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path('/workspace/p6-streamlit-e2e')
WORK = Path('/workspace/p6-work/docker-smoke')
OUT = WORK / os.environ.get('P6_DOCKER_SMOKE_LABEL', 'diagnostic-20261106')
OUT.mkdir(exist_ok=True)
DATA = OUT / 'workspace'
DATA.mkdir(mode=0o700, exist_ok=True)
EVIDENCE = OUT / 'evidence'
EVIDENCE.mkdir(exist_ok=True)
ENV = os.environ.copy()
for key in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'):
    ENV.pop(key, None)
DOCKER = ['docker', '--host=unix:///var/run/docker.sock']
IMAGE = 'python:3.12.14-slim-bookworm'
NAME = 'vde-pilot'


def command(name, args, timeout=600, check=True):
    start = time.monotonic()
    (OUT / (name + '.command.json')).write_text(json.dumps({'argv':args, 'cwd':str(ROOT), 'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2)+'\n')
    process = subprocess.run(args, cwd=ROOT, env=ENV, capture_output=True, timeout=timeout)
    (OUT / (name + '.stdout.txt')).write_bytes(process.stdout)
    (OUT / (name + '.stderr.txt')).write_bytes(process.stderr)
    (OUT / (name + '.result.json')).write_text(json.dumps({'returncode':process.returncode,'elapsed_seconds':time.monotonic()-start}, indent=2)+'\n')
    print(json.dumps({'step':name, 'returncode':process.returncode, 'elapsed_seconds':round(time.monotonic()-start,2)}), flush=True)
    if check and process.returncode:
        print(process.stdout.decode(errors='replace')[-4000:], flush=True)
        print(process.stderr.decode(errors='replace')[-4000:], flush=True)
        raise RuntimeError(name)
    return process


def health(label):
    observations = []
    for attempt in range(180):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=2) as response:
                item = {'attempt':attempt, 'status':response.status, 'body':response.read().decode()}
                observations.append(item)
                assert item['status'] == 200 and item['body'] == 'ok'
                (OUT / (label + '.http-health.json')).write_text(json.dumps(observations, indent=2)+'\n')
                print(json.dumps({'step':label, **item}), flush=True)
                return
        except Exception as exc:
            observations.append({'attempt':attempt,'error':str(exc)})
            if attempt % 20 == 0:
                print(json.dumps({'step':label,'waiting_seconds':attempt}), flush=True)
            time.sleep(1)
    (OUT / (label + '.http-health.json')).write_text(json.dumps(observations, indent=2)+'\n')
    command(label+'-failure-logs', DOCKER+['logs', NAME], check=False)
    raise RuntimeError('Server failed to become healthy')


def wait_removed():
    # `docker stop` can return just before --rm finishes daemon-side cleanup.
    for attempt in range(100):
        response = subprocess.run(DOCKER+['container','inspect',NAME], env=ENV,
                                  capture_output=True)
        if response.returncode != 0:
            return
        time.sleep(0.1)
    raise RuntimeError('Stopped smoke container name has not been removed')


manifest = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(ROOT.rglob('*')) if p.is_file() and
            not any(x in p.parts for x in ('__pycache__', '.pytest_cache')) and
            not str(p).endswith('.pyc')}
(OUT / 'development-source-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
if os.environ.get('P6_SMOKE_FORMAL') == '1':
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip()
command('source-commit', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}'])
command('source-status', ['git', 'status', '--short'])
command('docker-version', DOCKER+['version'])
command('docker-info', DOCKER+['info','--format','Server={{.ServerVersion}} OS={{.OSType}} Arch={{.Architecture}} Driver={{.Driver}}'])
command('pull', DOCKER+['pull', IMAGE])
command('image-inspect', DOCKER+['image','inspect',IMAGE,'--format','{{json .RepoDigests}}'])

startup = r'''
python -c "import sys; assert sys.version_info[:3] == (3, 12, 14)"
python -m venv /tmp/vde-tools
/tmp/vde-tools/bin/python -m pip install "uv==0.12.19"
python -c "import shutil; shutil.copytree(\"/source\", \"/tmp/code\", ignore=shutil.ignore_patterns(\".git\", \".venv\", \".workspace\", \"__pycache__\", \"*.egg-info\"))"
cd /tmp/code
/tmp/vde-tools/bin/uv sync --frozen --python /usr/local/bin/python3.12 --extra test
/tmp/vde-tools/bin/uv --version
/tmp/vde-tools/bin/uv pip freeze --python /tmp/vde-venv/bin/python
exec /tmp/vde-venv/bin/python -m streamlit run src/vde/app.py \
  --server.address=0.0.0.0 --server.port=8501 \
  --server.headless=true --browser.gatherUsageStats=false
'''

run = DOCKER+['run','--detach','--rm','--init','--name',NAME,
              '--user',f'{os.getuid()}:{os.getgid()}',
              '--publish','127.0.0.1:8501:8501',
              '--mount',f'type=bind,source={ROOT},target=/source,readonly',
              '--mount',f'type=bind,source={DATA},target=/data',
              '--mount',f'type=bind,source={WORK},target=/smoke,readonly',
              '--mount',f'type=bind,source={EVIDENCE},target=/evidence',
              '--mount','type=bind,source=/etc/ssl/certs/ca-certificates.crt,target=/run/combined-ca.pem,readonly',
              '--env','SSL_CERT_FILE=/run/combined-ca.pem',
              '--env','PIP_CERT=/run/combined-ca.pem',
              '--env','VDE_WORKSPACE=/data',
              '--env','P6_RESULTS_DIR=/evidence/ui-actions',
              '--env','UV_CACHE_DIR=/tmp/uv-cache',
              '--env','UV_PROJECT_ENVIRONMENT=/tmp/vde-venv',
              '--env','UV_PYTHON_DOWNLOADS=never',
              '--workdir','/tmp',IMAGE,'sh','-eu','-c',startup]
(OUT / 'managed-environment-adaptations.txt').write_text(
    'Same README image, UID/GID, read-only source and writable persistent data; detached execution for probing.\n'
    'Managed HTTPS trust: read-only combined host CA at /run/combined-ca.pem, SSL_CERT_FILE and PIP_CERT.\n'
    'Docker configured proxy and registry credentials preserved without modification or disclosure.\n'
    'Additional /smoke readonly driver and /evidence writable mounts are test support only.\n'
    'Linux-host Docker execution only; actual Mac-host execution NOT_RUN.\n')

try:
    command('first-launch', run)
    health('first-launch')
    command('first-runtime-versions', DOCKER+['exec',NAME,'/tmp/vde-venv/bin/python','-c',
        'import platform,sys,importlib.metadata,json; print(json.dumps(dict(platform=platform.platform(),python=sys.version,packages={n:importlib.metadata.version(n) for n in ["streamlit","pytest","jsonschema","referencing","rfc8785","openpyxl"]}),indent=2))'])
    command('first-workflow', DOCKER+['exec',NAME,'/tmp/vde-venv/bin/python','/smoke/driver.py','create'])
    command('first-server-logs', DOCKER+['logs',NAME])
    command('first-stop', DOCKER+['stop','--time','10',NAME])
    wait_removed()
    command('second-launch', run)
    health('second-launch')
    command('restart-inspection', DOCKER+['exec',NAME,'/tmp/vde-venv/bin/python','/smoke/driver.py','restart'])
    command('second-server-logs', DOCKER+['logs',NAME])
finally:
    command('final-server-logs', DOCKER+['logs',NAME], check=False)
    command('final-stop', DOCKER+['stop','--time','10',NAME], check=False)

(OUT / 'diagnostic-summary.json').write_text(json.dumps({
    'status':'LINUX_DOCKER_PASSED' if os.environ.get('P6_SMOKE_FORMAL') == '1' else 'LINUX_DOCKER_DIAGNOSTIC_PASSED',
    'source_state':'Clean committed implementation tree' if os.environ.get('P6_SMOKE_FORMAL') == '1' else 'Development tree; formal final source commit smoke still required',
    'actual_mac_host_execution':'NOT_RUN',
    'read_only_repository_mount':True,
    'persistent_disposable_workspace_mount':True,
    'source_commit':(OUT/'source-commit.stdout.txt').read_text().splitlines()[0],
    'image':IMAGE,
    'image_digests':json.loads((OUT/'image-inspect.stdout.txt').read_text()),
},indent=2)+'\n')
print('LINUX_DOCKER_DIAGNOSTIC_PASSED',flush=True)
