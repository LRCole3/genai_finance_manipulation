"""Export generated drafts with canonical metadata, preserving raw agent shards."""
import hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'data/paper1';O=D/'exports';O.mkdir(exist_ok=True)
f=json.loads((D/'generation_facts.json').read_text());genres={x['genre_id']:x['name'] for x in f['genres']}
streams={r:(O/f'{r.lower()}_drafts.jsonl').open('w') for r in ['CT','IT']}
status={r['item_id']:r['status'] for r in map(json.loads,(D/'record_manifest.jsonl').read_text().splitlines())}
quarantine=(O/'quarantined_drafts.jsonl').open('w')
changes=[];n=0;q=0
for p in sorted((D/'shards').glob('*.jsonl')):
 for line,l in enumerate(p.read_text().splitlines(),1):
  if not l.strip():continue
  row=json.loads(l);rid=row['item_id'];match=re.fullmatch(r'P1-(CT|IT)-T(\d\d)-G(\d\d)-P(\d\d)-R(\d\d)-([IN])',rid)
  if match:
   regime,t,g,prop,real,arm=match.groups()
   canonical={'pair_id':rid[:-2],'target_id':f['target_ids'][int(t)-1],'genre_id':'G'+g,'genre':genres['G'+g],'proposition_id':'P'+prop,'realization_id':'R'+real}
   for k,v in canonical.items():
    if row.get(k)!=v:changes.append({'item_id':rid,'field':k,'before':row.get(k),'after':v})
    row[k]=v
  row['source']={'path':str(p.relative_to(R)),'line':line,'raw_sha256':hashlib.sha256(l.encode()).hexdigest()}
  row['review_status']='draft_pending_validation';row['research_ready']=False;row['token_count']=None
  if status.get(rid) in ['duplicate','invalid']:
   row['quarantine_reason']=status[rid];quarantine.write(json.dumps(row,ensure_ascii=False)+'\n');q+=1
  else:
   streams[row['regime']].write(json.dumps(row,ensure_ascii=False)+'\n');n+=1
for s in streams.values():s.close()
quarantine.close()
(O/'metadata_normalizations.json').write_text(json.dumps(changes,indent=2)+'\n')
print(n,'distinct drafts exported;',q,'quarantined; raw shards preserved;',len(changes),'metadata normalizations')
