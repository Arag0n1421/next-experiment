"""Run the locally predeclared complete-population checklist comparison."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import statistics
import time
from collections import Counter
from pathlib import Path
import numpy as np
from science.screen import Screen, CONDITIONS, PARAMETERS, summarize_condition, DEFAULT_DATA
from benchmark.triage import evaluate

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/benchmark'

def run_pass(groups, adaptive):
    started=time.perf_counter()
    results=[evaluate(values, adaptive=adaptive) for _,_,values,_ in groups]
    return results, time.perf_counter()-started


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    protocol=Path(__file__).with_name('PROTOCOL.md')
    locked={'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(), 'protocol_sha256':hashlib.sha256(protocol.read_bytes()).hexdigest(), 'parameters':PARAMETERS, 'code_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['benchmark/triage.py','benchmark/run.py','science/screen.py']}}
    (OUT/'protocol-lock.json').write_text(json.dumps(locked,indent=2)+'\n')
    screen=Screen.load(DEFAULT_DATA)
    # Sort once and split instead of repeatedly scanning 100k guides per gene.
    ids=np.flatnonzero(screen.eligible & ~screen.controls)
    ids=ids[np.argsort(screen.genes[ids],kind='stable')]
    splits=np.split(ids,np.flatnonzero(screen.genes[ids][1:] != screen.genes[ids][:-1])+1)
    groups=[(str(screen.genes[idx[0]]),condition,screen.effects[idx][:,cols],screen.guides[idx].tolist()) for idx in splits for condition,cols in CONDITIONS.items()]
    setup_seconds=time.perf_counter()-started
    print(f'Evaluating {len(groups)} gene-condition decisions',flush=True)
    eager,_=run_pass(groups,False)
    adaptive,_=run_pass(groups,True)
    reference=[summarize_condition(v,g)['fixed_checklist_pass'] for _,_,v,g in groups]
    mismatch=sum(a['passed'] != b['passed'] for a,b in zip(eager,adaptive))
    reference_mismatch=sum(a['passed'] != b for a,b in zip(eager,reference))
    timings=[]
    for i in range(5):
        order=[False,True] if i%2==0 else [True,False]
        row={'pair':i+1,'order':['adaptive' if x else 'eager' for x in order]}
        for method in order:
            _,elapsed=run_pass(groups,method)
            row[('adaptive' if method else 'eager')+'_seconds']=elapsed
        row['speedup']=row['eager_seconds']/row['adaptive_seconds']
        timings.append(row)
        print(json.dumps(row),flush=True)
    eager_seconds=statistics.median(x['eager_seconds'] for x in timings)
    adaptive_seconds=statistics.median(x['adaptive_seconds'] for x in timings)
    eager_loo=sum(x['loo_omissions'] for x in eager)
    adaptive_loo=sum(x['loo_omissions'] for x in adaptive)
    reduction=100*(1-adaptive_loo/eager_loo) if eager_loo else 0
    metrics={'Gene-condition decisions':len(groups),'Decision mismatches':mismatch,'Reference mismatches':reference_mismatch,'Eager LOO recomputations':eager_loo,'Adaptive LOO recomputations':adaptive_loo,'LOO work reduction percent':round(reduction,2),'Eager rule evaluations':sum(x['check_count'] for x in eager),'Adaptive rule evaluations':sum(x['check_count'] for x in adaptive),'Eager median seconds':round(eager_seconds,4),'Adaptive median seconds':round(adaptive_seconds,4),'Checklist kernel speedup':round(eager_seconds/adaptive_seconds,3),'Shared setup seconds (excluded)':round(setup_seconds,4),'Passing decisions':sum(x['passed'] for x in eager)}
    report={'status':'passed' if not mismatch and not reference_mismatch else 'failed','evaluation_status':'Retrospective computational comparison; no held-out biological or LLM advantage measured','headline':f'{reduction:.1f}% fewer leave-one-out recomputations with {mismatch} changed checklist decisions.','metrics':metrics,'timing_pairs':timings,'input_sha256':screen.digest,'protocol':locked,'stop_reasons':dict(Counter(x['stop_reason'] for x in adaptive)),'limitations':['Same previously explored dataset, both repeats visible; not a held-out biological benchmark.','This is deterministic early-stop execution, not evidence that the language model makes better scientific choices.','Timing excludes shared loading, normalization, orchestration and model latency; no end-to-end agent speedup is claimed.','Rules and labels are development heuristics; agreement does not establish biological truth, significance or longevity benefit.','No API-dollar or wet-lab savings have been measured.','Agreement concerns binary checklist verdicts; early-stopped cases report the first decisive failure, not every diagnostic.']}
    (OUT/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    with (OUT/'decisions.jsonl').open('w') as f:
        for (gene,condition,_,_),a,b in zip(groups,eager,adaptive):f.write(json.dumps({'gene':gene,'condition':condition,'eager':a,'adaptive':b})+'\n')
    lines=['# Matched checklist benchmark','',report['headline'],'',report['evaluation_status'],'','| Metric | Observed |','| --- | --- |']+[f'| {k} | {v} |' for k,v in metrics.items()]+['','## Limits','']+['- '+x for x in report['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    if mismatch or reference_mismatch:raise SystemExit('Decision equivalence failed')

if __name__=='__main__':main()
