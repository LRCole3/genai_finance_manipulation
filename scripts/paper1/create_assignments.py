"""Create disjoint work assignments; never imply assigned records exist."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'data/paper1/assignments'
D.mkdir(parents=True,exist_ok=True)
assignments=[]
for regime in ['CT','IT']:
 for t in range(1,5):
  for g in range(1,6):
   ids=[f'P1-{regime}-T{t:02}-G{g:02}-P{p:02}-R{r:02}-{arm}' for r in range(1,21) for p in range(1,11) for arm in ['I','N']]
   assignments.append(dict(kind='paired',regime=regime,target_number=t,genre_number=g,item_ids=ids))
for regime,size in [('CT',350),('IT',360)]:
 for first in range(1,9001,size):
  assignments.append(dict(kind='background',regime=regime,item_ids=[f'P1-{regime}-BG-{n:05}' for n in range(first,min(first+size,9001))]))
for regime in ['CT','IT']:
 assignments.append(dict(kind='warmup',regime=regime,item_ids=[f'P1-{regime}-WU-{n:03}' for n in range(1,101)]))
for start in range(1,41,10):
 assignments.append(dict(kind='familiarization',regime='IT',item_ids=[f'P1-FAM-E{e:03}-{i:02}' for e in range(start,start+10) for i in range(1,11)]))
assert len(assignments)==97
ids=[x for a in assignments for x in a['item_ids']]
assert len(ids)==len(set(ids))==34600
for i,a in enumerate(assignments,4):
 a.update(worker_id=f'worker_{i:03}',status='assigned_not_started',requested_model='gpt-6-luna',requested_effort='high',output=f'data/paper1/shards/worker_{i:03}.jsonl')
 (D/f'worker_{i:03}.json').write_text(json.dumps(a,indent=2)+'\n')
print(f'{len(assignments)} assignments; {len(ids)} unique planned records')
