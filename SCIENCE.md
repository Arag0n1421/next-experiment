# Deterministic scientific tools: executed development slice

This implementation runs on the real GSE268569 guide count matrix. It is a transparent **approximate count enrichment analysis**, not a MAGeCK reproduction, an independent benchmark, a gene-level FDR analysis or proof of rejuvenation. Both repeats are visible to these exploratory tools. Final held-out selection requires a separate restricted interface.

## Run

From the project root, with its installed environment:

```sh
./.venv/bin/python -m science baseline
./.venv/bin/python -m science qc
./.venv/bin/python -m science candidate TP53
./.venv/bin/python -m science guide-check UBA3
./.venv/bin/python -m science context GABRR2
./.venv/bin/python -m unittest discover -s tests -p test_science.py -v
```

Optional global arguments precede the operation, e.g. `python -m science --output-dir runs/baseline candidate TP53`. Exact gene symbols are required; no fuzzy resolution or automatic modernization of historical symbols. Dependencies: numpy, pandas, openpyxl. The unittest checks need only the same environment, no provider credentials.

Import boundary for Omnigent custom tools:

```python
from science.screen import run_tool
result = run_tool("guide-check", gene="UBA3")
```

Allowlisted operations: `qc`, `baseline`, `candidate`, `guide-check`, `context`, `triage`, `dependence`. The `dependence` operation (`science/dependence.py`) answers "what evidence would change the verdict" from the same fixed estimator and checklist: observed checklist values, per-guide effects, omit-one-guide effects (a guide is *decisive* when the aggregate crosses the 0.5 log₂ threshold without it), starting-count filter variants (10/20/50), and two probes marked `observed: false` that show how the fixed rule would respond to one added agreeing or null guide. Those probes are hypothetical rule probes, not measurements, and are labelled as such in every output. `run_tool` returns `status`, `tool`, `evidence_type`, `input_hashes`, `parameters`, `observations`, `artifact_paths`, `limitations`, `duration_seconds`, `resource_use`. Import calls return in-memory evidence with empty artifact paths; the caller must persist that record in its run ledger. CLI calls persist JSON in the output directory. No arbitrary execution, remote compute or model call occurs inside these functions. Baseline CLI also writes the compact full gene table and complete QC/correction ledger. Matrix parse is cached per import process and file modification timestamp.

## Inputs and important QC

Source: [NCBI GSE268569 CountMatrix](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE268nnn/GSE268569/suppl/GSE268569_CountMatrix.xlsx). The six integer count columns comprise two D0 baselines and two repeats per final condition, with and without IL6. [GEO sample descriptions](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE268569) identify the conditions. The input SHA256 is recorded with each result. Full schema, finite/integer/nonnegative counts, unique sgRNA IDs and all positive library totals are enforced.

The actual input contains 103,073 guides. Its Gene column has Excel-date conversion corruption: 164 date-typed cells are recovered from the exact retained gene prefix in their sgRNA IDs. This preserves DEC1, MARC1/MARC2, MARCH and SEPT historical labels rather than merging all March dates into one gene. Nine valid text labels differ from the guide locus prefix; their explicit Gene cells are preserved (e.g. C4B_2 locus assigned to C4B). Every repair/preserved discrepancy is recorded in `runs/baseline/qc.json`. No genomic alias is inferred without evidence.

Controls are **exactly** Gene=`non-targeting`, with guide ID `non-targeting_<digits>`. There are 1,895, matching the paper's declared inventory. CTRL is a real locus; NONO and KNTC1 are also real genes. Substring matching would incorrectly count them as controls. Label/ID contradictions fail rather than silently passing.

## Approximation and direction

For each library, normalize read counts to the geometric mean of its six library totals:

`normalized_count = observed_count × geometric_mean(library_totals) / library_total`

For each corresponding repeat and final condition:

`raw_guide_effect = log2((normalized_final + 1) / (normalized_D0 + 1))`

Subtract the median raw effect of all verified non-targeting guides for that contrast. The pseudocount is one **normalized read**, not one CPM. Total-depth scaling can be affected by compositional changes; control centering provides a reference but cannot settle all biological confounding. Non-targeting guide distributions are reported, not converted to gene p-values.

Guide eligibility requires at least **20 observed D0 counts in both repeats**. This keeps identical guides across the two repeat summaries. Main gene score is the median across eligible guides of their mean two-repeat effect. Per-repeat scores are separate guide medians; their average need not equal the median-of-mean main score. Do not silently substitute one estimator for the other.

The [paper's methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC12326738/) define positive MAGeCK beta as enrichment of a targeted gene's guides, interpreted as gene activity positively contributing to senescence. Our positive quantity is **relative guide enrichment**, not a MAGeCK beta or proof of the same mechanistic conclusion. Depletion can indicate cell-fitness essentiality and is not uniquely an anti-senescence effect.

## Checks and all assumptions

- Gene summaries report eligible and total guides. Zero eligible guides yields missing measurements, not zero biological effect.
- Leave-one-out removes each eligible guide and recomputes the identical gene estimator. Outputs include omitted IDs, full score, range, sign reversal and crossing the operational 0.5 threshold. A single guide cannot provide a LOO check. This is sensitivity analysis, not new biological replication.
- Repeat agreement reports scores, difference and sign agreement. Two repeats cannot estimate rich biological variance or generalization across donors.
- IL6 context contrast is computed **within guide and repeat before gene aggregation** as `with_IL6_effect − without_IL6_effect`; shared D0 cancels algebraically. Positive means greater enrichment with IL6. Condition contrasts are not independent samples. A context-specific effect need not be rejected.
- `candidate` and `guide-check` report all three predeclared D0 thresholds: 10, 20, 50. These vary filtering only, keeping normalization and pseudocount fixed. They can expose count sensitivity; the system must not silently choose the favorable variant.
- Fixed checklist requires ≥3 eligible guides, each repeat score ≥0.5 log2, every LOO aggregate ≥0.5, repeat difference ≤1 log2, and ≥60% guides with positive mean effect. These are development heuristics, not calibrated error rates. Every value is included in result parameters.
- No statistical count robustness test proves retained cell identity, reduced senescence markers, human safety or longevity. Those endpoints remain visibly missing.

## Actually executed

Full baseline completed in approximately 15 seconds on the local Mac. Output files:

- `runs/baseline/baseline.json`: effect-only and fixed-checklist rankings, scope and limitations.
- `runs/baseline/gene-scores.csv`: 18,431 genes with ≥1 eligible guide, including scores/repeats/context/LOO/checklist flags. Target genes with no eligible guides are absent from this score table and remain part of the QC denominator.
- `runs/baseline/qc.json`: full schema/read-depth/control/mapping details.

After date recovery there are 18,788 target gene labels and one non-targeting group. 58,645 guide rows pass the count filter (including 1,044 controls); 12,064 target genes have ≥3 eligible guides. The fixed checklist passes 548 genes without IL6 and 1,222 with IL6. **These are heuristic filter pass counts, not validated hit counts.**

TP53 is the strongest approximate positive signal in both conditions (main scores about 10.3465 and 8.9819 log2) and passes these statistical heuristics. That does not establish the intended phenotype. The paper already reports changed identity markers following TP53 suppression: that published distinction is literature evidence, not discovered by this count analysis. UBA3 ranks third in the no-IL6 effect-only list but fails the fixed checklist; inspect its real repeat and guide checks rather than scripting a reversal. SAMM50 has only one eligible guide at the main count threshold, so a LOO conclusion is unavailable even though the paper contains separate validation experiments.

Eight invariant tests passed: library scaling invariance; invalid-count rejection; exact controls; source-bound date repair; LOO reversal/single-guide limits; repeat disagreement; within-guide shared-baseline cancellation; operation allowlisting. No final-panel performance comparison, agent superiority, wet-lab savings or new biological discovery has been measured.
