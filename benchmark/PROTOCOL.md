# Locked evaluation protocol v1

Declared before execution on 4 October 2026. No thresholds are tuned on results.

Question: can early-stop execution reduce computation while returning exactly the same binary checklist decisions as exhaustive execution?

Input: SHA256-identified GSE268569 count matrix. Population: every target gene with at least one guide passing D0 >=20 in both repeats, in each of the two IL6 conditions. Both methods see identical normalized counts. No random or favorable candidate subset is selected. This dataset has already been explored; it is not a held-out biological benchmark.

Comparator: eager evaluation of all six existing checklist rules (coverage >=3; both repeat medians >=0.5; repeat difference <=1; positive guide fraction >=0.6; all leave-one-guide-out medians >=0.5). The two repeat comparisons are counted separately. Proposed method evaluates identical rules in the same order and stops after the first failure. Eager and adaptive methods use the same implementation primitives. Independently check eager outputs against science.screen.summarize_condition.

Primary correctness gate: zero decision mismatches across the complete population. Primary work metric: number of individual leave-one-guide-out recomputations. Secondary metrics: rules evaluated and elapsed time. These work counts are operations, not model tokens, money or wet-lab savings.

Timing: parse, normalize, build grouped arrays and verify reference outputs once outside the timed region for both methods. Warm each method once; then five paired passes with alternating order. Report every timing, paired speedups and median total runtime ratio. A real end-to-end workflow may be dominated by file loading or model latency; this benchmark measures only the checklist kernel. Do not extrapolate the timing to end-to-end agent acceleration.

Acceptance: exact agreement is required. Any speed or operation reduction is reported at its measured value, including no gain. Stop reasons are computational routing diagnostics, not ground-truth biological labels. No claim of better hypothesis selection, rejuvenation or LLM superiority follows from this evaluation. Agreement concerns binary checklist verdicts; early-stopped failures do not return all diagnostic details that eager execution computes.
