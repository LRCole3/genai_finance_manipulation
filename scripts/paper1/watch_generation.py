"""Refresh durable generation evidence while independent authoring workers run."""
import argparse,json,subprocess,sys,time,os
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];DATA=ROOT/'data/paper1'
def atomic(path,obj):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(obj,indent=2)+'\n');tmp.replace(path)
def main():
 p=argparse.ArgumentParser();p.add_argument('--interval',type=int,default=60);p.add_argument('--once',action='store_true');a=p.parse_args()
 pidfile=DATA/'generation_monitor.json';old_count=None;last_change=time.time()
 while True:
  state={'pid':os.getpid(),'updated_utc':datetime.now(timezone.utc).isoformat(),'status':'refreshing','scope':'File-derived progress only; does not assert agents are alive or research validation has passed.'}
  try:
   outputs={}
   for script in ['track_records.py','export_drafts.py','update_worker_status.py','summarize_generation.py']:
    r=subprocess.run([sys.executable,str(ROOT/'scripts/paper1'/script)],cwd=ROOT,capture_output=True,text=True,timeout=120)
    if r.returncode:raise RuntimeError(script+': '+r.stderr[-1000:])
    outputs[script]=r.stdout.strip()
   summary=json.loads((DATA/'generation_summary.json').read_text());counts=summary['status_counts'];n=summary['observed_shard_records']
   if n!=old_count:last_change=time.time();old_count=n
   done=counts['missing']==0 and counts['invalid']==0 and counts['duplicate']==0 and not summary['shard_parse_errors'] and not summary['unknown_item_ids']
   state.update(status='draft_generation_complete' if done else 'monitoring',status_counts=counts,observed_rows=n,seconds_since_new_saved_count=round(time.time()-last_change),research_ready=False)
   atomic(pidfile,state);print(json.dumps(state),flush=True)
   if done or a.once:return
  except Exception as e:
   state.update(status='refresh_failed_will_retry',error=str(e));atomic(pidfile,state);print(json.dumps(state),flush=True)
   if a.once:raise
  time.sleep(max(5,a.interval))
if __name__=='__main__':main()
