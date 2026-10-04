"""Build an allowlisted review package; no credentials or local session exports."""
from __future__ import annotations
import hashlib
import json
import re
import shutil
import zipfile
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'dist/next-experiment-source'
if DEST.exists():
 DEST.rename(ROOT/'dist'/('source-previous-'+uuid.uuid4().hex[:8]))
DEST.mkdir(parents=True,exist_ok=True)
patterns=['science/*.py','integration/*.py','benchmark/*.py','benchmark/*.md','tests/test_*.py','agents/lab/**/*.yaml','agents/lab/**/*.py','demo/index.html','demo/app.js','demo/style.css','demo/styles.css','demo/evidence/*.json','demo/*.md','scripts/download-data.py','scripts/run-lab.sh','scripts/run-bounded-lab.py','scripts/build-demo.py','scripts/serve-demo.py','scripts/export-run.py','pyproject.toml','POLICY.md','SCIENCE.md','SUBMISSION.md','runs/benchmark/report.json','runs/benchmark/REPORT.md','runs/benchmark/protocol-lock.json','setup/apply-compatibility-patch.py','BRIEF-COMPLIANCE.md','DELIVERY.md','runs/BOUNDED-VERIFICATION.json']
patterns += ['runs/live/'+record+'.json' for record in ['452fda4c1e084b9d9b1ae4fea2e1e39f','d8edc9f95f0c4934ae9b4358fd89e98f','9640dbe6abbb44d7b72e9141e4c1f1ac']]
patterns += ['scripts/package-source.py','reviews/JURY-REVIEW-MAP.md','reviews/JURY-UI-DELIVERY.md','runs/counterfactual/POST-RUN-REVIEW.md','runs/counterfactual/PROTOCOL.md','runs/counterfactual/PROMPT.txt','runs/counterfactual/EVALUATION.json','runs/counterfactual/MATCHING.json','tests/panel_render_check.js','scripts/counterfactual-harness.py','demo/panel.html','demo/panel.css','demo/panel.js','scripts/build-panel.py','data/biological-context.json']
# Preserve the exact scientific records backing the public evidence-response check.
evaluation_file = ROOT / 'runs/counterfactual/EVALUATION.json'
if evaluation_file.exists():
 evaluation = json.loads(evaluation_file.read_text())
 if evaluation.get('status') == 'completed':
  for arm in evaluation['rows']:
   patterns += ['runs/live/'+arm['decision_id']+'.json']
   patterns += ['runs/live/'+item['record_id']+'.json' for item in arm['evidence']]
  patterns += ['runs/counterfactual/COUNTERFACTUAL-*-manifest.json']
for pattern in patterns:
 for p in ROOT.glob(pattern):
  if p.is_file() and p.name != 'test_review_identity.py':
   rel=p.relative_to(ROOT); out=DEST/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out)
# Only the version and hashes are necessary to reproduce the narrow compatibility fix.
receipt=json.loads((ROOT/'setup/CODEX-COMPATIBILITY.json').read_text())
public_receipt={k:v for k,v in receipt.items() if k in ['version','omnigent_version','original_sha256','patched_sha256']}
(DEST/'setup/CODEX-COMPATIBILITY.json').write_text(json.dumps(public_receipt,indent=2)+'\n')
shutil.copy2(ROOT / 'README.md', DEST / 'README.md')
(DEST/'.gitignore').write_text('.venv/\n__pycache__/\n.pytest_cache/\n*.egg-info/\n.env*\ndata/*.xlsx\nruns/policy.sqlite3*\nruns/bounded/\nruns/live/*\n!runs/live/452fda4c1e084b9d9b1ae4fea2e1e39f.json\n!runs/live/d8edc9f95f0c4934ae9b4358fd89e98f.json\n!runs/live/9640dbe6abbb44d7b72e9141e4c1f1ac.json\nruns/generated-agents/\n')
with (DEST/'.gitignore').open('a') as ignored:
 ignored.write('runs/counterfactual/*.xlsx\n')
 if evaluation_file.exists() and evaluation.get('status') == 'completed':
  for arm in evaluation['rows']:
   for record_id in [arm['decision_id'], *[item['record_id'] for item in arm['evidence']]]:
    ignored.write('!runs/live/'+record_id+'.json\n')
files=sorted(p for p in DEST.rglob('*') if p.is_file() and '.git' not in p.parts and p.name!='MANIFEST.json')
for p in files:
 if p.suffix in ['.py','.md','.json','.yaml','.html','.js','.css','.toml','.sh']:
  text=p.read_text()
  # Generic redaction markers and the synthetic /Users/private/ test fixture are safe.
  if re.search(r'/(?:Users/(?!private/)|Volumes/)[A-Za-z0-9._-]+', text) or re.search(r'\b[A-Za-z0-9._%+-]+@(?:gmail|icloud|outlook)\.com\b', text):
   raise SystemExit(f'Local identity/path in package: {p.relative_to(DEST)}')
manifest={str(p.relative_to(DEST)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(DEST/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=ROOT/'dist/next-experiment-source.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(DEST.rglob('*')):
  if p.is_file() and '.git' not in p.parts:z.write(p,Path('next-experiment-source')/p.relative_to(DEST))
print(json.dumps({'archive':str(archive),'files':len(manifest),'archive_bytes':archive.stat().st_size}))
