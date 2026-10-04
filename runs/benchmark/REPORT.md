# Matched checklist benchmark

89.5% fewer leave-one-out recomputations with 0 changed checklist decisions.

Retrospective computational comparison; no held-out biological or LLM advantage measured

| Metric | Observed |
| --- | --- |
| Gene-condition decisions | 36862 |
| Decision mismatches | 0 |
| Reference mismatches | 0 |
| Eager LOO recomputations | 111274 |
| Adaptive LOO recomputations | 11739 |
| LOO work reduction percent | 89.45 |
| Eager rule evaluations | 221172 |
| Adaptive rule evaluations | 79347 |
| Eager median seconds | 2.6311 |
| Adaptive median seconds | 0.6468 |
| Checklist kernel speedup | 4.068 |
| Shared setup seconds (excluded) | 5.131 |
| Passing decisions | 1770 |

## Limits

- Same previously explored dataset, both repeats visible; not a held-out biological benchmark.
- This is deterministic early-stop execution, not evidence that the language model makes better scientific choices.
- Timing excludes shared loading, normalization, orchestration and model latency; no end-to-end agent speedup is claimed.
- Rules and labels are development heuristics; agreement does not establish biological truth, significance or longevity benefit.
- No API-dollar or wet-lab savings have been measured.
- Agreement concerns binary checklist verdicts; early-stopped cases report the first decisive failure, not every diagnostic.
