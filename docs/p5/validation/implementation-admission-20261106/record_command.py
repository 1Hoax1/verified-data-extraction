import argparse,subprocess,os,json,sys,platform,importlib.metadata,time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--cwd',type=Path,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False)
command=a.command[1:] if a.command[:1]==['--'] else a.command
meta={'command':command,'cwd':str(a.cwd),'started_at_moscow':datetime.now(ZoneInfo('Europe/Moscow')).isoformat(),
      'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
      'packages':{n:importlib.metadata.version(n) for n in ['pytest','jsonschema','referencing','rfc8785','openpyxl','streamlit']}}
try:
 meta.update(checkout_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.cwd,text=True,stderr=subprocess.DEVNULL).strip(),checkout_tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=a.cwd,text=True,stderr=subprocess.DEVNULL).strip())
except subprocess.CalledProcessError:pass
start=time.monotonic()
with (a.out/'stdout.txt').open('wb') as o,(a.out/'stderr.txt').open('wb') as e:
 r=subprocess.run(command,cwd=a.cwd,stdout=o,stderr=e)
meta.update(exit_code=r.returncode,elapsed_seconds=time.monotonic()-start,finished_at_moscow=datetime.now(ZoneInfo('Europe/Moscow')).isoformat())
(a.out/'command.json').write_text(json.dumps(meta,indent=2)+'\n');(a.out/'exit-code.txt').write_text(str(r.returncode)+'\n')
print(json.dumps(meta,indent=2));print((a.out/'stdout.txt').read_text()[-6000:]);print((a.out/'stderr.txt').read_text()[-3000:],file=sys.stderr)
sys.exit(0)
