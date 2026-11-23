"""Refresh progress from durable files; launch IDs are recorded by coordinator."""
import argparse, json
from datetime import datetime,timezone
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'data/paper1'
p=argparse.ArgumentParser();p.add_argument('--launched',nargs='*',type=int,default=[]);a=p.parse_args()
f=D/'work_registry.json';r=json.loads(f.read_text())
for w in r['workers']:
 n=int(w['worker_id'][-3:])
 if n in a.launched:
  w['status']='launched';w['launched_at']=datetime.now(timezone.utc).isoformat()
  w['agent_task']=f'/root/worker_{n:03}' if n>3 else ['/root/worker_001_catalogue','/root/worker_002_tracking','/root/worker_003_validation'][n-1]
 if n<=3 and w['status']=='launched':w['status']='completed_infrastructure'
 progress=D/'assignments'/f"{w['worker_id']}_progress.json"
 if progress.exists():
  x=json.loads(progress.read_text());w['status']=x.get('status','partial');w['created_count']=x.get('created_count');w['progress_path']=str(progress.relative_to(R))
 actual=D/'shards'/f"{w['worker_id']}.jsonl"
 if actual.exists():w['saved_line_count']=sum(bool(l.strip()) for l in actual.read_text().splitlines())
r['updated_at']=datetime.now(timezone.utc).isoformat();r['launched_count']=sum('agent_task' in w for w in r['workers']);r['completed_or_partial_count']=sum(w['status'] in ['completed_infrastructure','partial','generated_draft'] for w in r['workers'])
f.write_text(json.dumps(r,indent=2)+'\n');print(r['launched_count'], 'agents launched;',r['completed_or_partial_count'],'with completion/partial records')
