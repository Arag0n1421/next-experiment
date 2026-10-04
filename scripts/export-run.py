"""Save a specific local Omnigent run and its child handoffs for review."""
import argparse
import json
import re
import urllib.request
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('session_id');p.add_argument('--output-dir', type=Path);args=p.parse_args()
if not re.fullmatch(r'[a-f0-9]{32}',args.session_id):raise SystemExit('Use the recorded session ID')
root=Path(__file__).resolve().parents[1]
out=args.output_dir or root/'runs/verified'/args.session_id;out.mkdir(parents=True,exist_ok=True)
base='http://127.0.0.1:6767/v1/sessions/'

def save(session_id,suffix,name):
    data=json.load(urllib.request.urlopen(base+session_id+suffix,timeout=10))
    (out/name).write_text(json.dumps(data,indent=2)+'\n')
    return data

session=save(args.session_id,'','session.json')
save(args.session_id,'/items','planner-items.json')
children=save(args.session_id,'/child_sessions','children.json')
for child in children.get('data',[]):
    cid=child['id'];save(cid,'',cid+'-session.json');save(cid,'/items',cid+'-items.json')
print(json.dumps({'session_id':args.session_id,'status':session.get('status'),'child_sessions':len(children.get('data',[])),'saved_to':str(out)}))
