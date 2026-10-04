# Next Experiment: jury review and submission artifacts

**Pitch:** Check a promising gene-screen result. Use the evidence to choose the next experiment.

Next Experiment investigates one specific scientific question: does a promising count-enrichment signal justify biological follow-up, and which analysis best resolves the uncertainty? Omnigent coordinates a Planner, Scientist, Experimentalist and Critic to compare tests, execute an analysis and record a changed decision.

## Recommended review path

```sh
./.venv/bin/python scripts/serve-demo.py
```

Start at <http://127.0.0.1:6768/panel>, then follow the saved Omnigent investigation at <http://127.0.0.1:6768/>. The server binds only to the local loopback interface and serves allowlisted assets and sanitized evidence.

| Surface | What a reviewer can inspect | Execution status |
| --- | --- | --- |
| Six-gene panel | Two IL6 conditions, guide-level support, fixed ranking rules, curated publications and proposed next tests. | Saved deterministic analyses and a source snapshot. Dropdowns explore results. |
| UBA3 investigation | Four specialist jobs, two candidate analyses, selected guide-sensitivity test, measured result and updated decision. | Replay of a real completed Omnigent run. |
| Source and records | Agent specifications, permissions, estimator, protocols, hashes and recorded results. | Reproducible code and local audit artifacts. |

The launcher executes actual agents when run with a supported provider login. The browser does not launch agents. Panel ordering is a fixed heuristic; no AI ranking advantage is claimed. Use [the jury review map](reviews/JURY-REVIEW-MAP.md) for the five judging criteria and [BRIEF-COMPLIANCE.md](BRIEF-COMPLIANCE.md) for the requirement audit.

## The complete discovery loop

1. **Question:** should UBA3 receive follow-up based on its promising aggregate count signal?
2. **Hypotheses:** a reproducible context-associated effect, or guide-specific/pooled-count instability.
3. **Choice:** compare removing each guide with comparing the two IL6 conditions. Guide sensitivity was chosen to resolve the immediate uncertainty, using existing data at low computational cost.
4. **Executed test:** approximate no-IL6 enrichment was **4.174**, but an eligible-guide omission changed it to **−0.055**. All three omissions are available.
5. **Updated decision:** collect more guide-resolved evidence before immediate prioritization. The evidence does not establish that UBA3 is an artifact.
6. **Proposed next experiment:** independent guides with target-suppression checks, biological repeats, senescence readouts, MSC identity and fitness measurements. This has not been performed or authorized by the demo.

## Evidence inventory

- [Agent specifications](agents/lab/config.yaml) and [role-specific tools/policies](POLICY.md).
- [Initial measurement](runs/live/452fda4c1e084b9d9b1ae4fea2e1e39f.json), [executed sensitivity test](runs/live/d8edc9f95f0c4934ae9b4358fd89e98f.json), and [test comparison / updated decision](runs/live/9640dbe6abbb44d7b72e9141e4c1f1ac.json).
- [Sanitized browser evidence and source hashes](demo/evidence/manifest.json).
- [Separate bounded runtime verification](runs/BOUNDED-VERIFICATION.json): completed specialists, three of four shared analysis attempts used, and closed-run rejection. The browser replays the earlier scientific run.
- [Scientific implementation and assumptions](SCIENCE.md), [curated biological context](data/biological-context.json), and [six-gene saved analysis](demo/evidence/panel.json).
- [Matched computational comparison](runs/benchmark/REPORT.md) and [predeclared protocol](benchmark/PROTOCOL.md).
- [Three-arm evidence-response evaluation](runs/counterfactual/EVALUATION.json), [its protocol](runs/counterfactual/PROTOCOL.md), and [the recorded attribution limitation](runs/counterfactual/POST-RUN-REVIEW.md).

Original sources: [GEO dataset](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE268569), [count matrix](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE268nnn/GSE268569/suppl/GSE268569_CountMatrix.xlsx), and [publication / methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC12326738/). The curated context links published claims separately from editorial interpretations. GEO counts and the publisher supplement differ, so published beta/FDR values are contextual evidence rather than benchmark answers for this estimator.

## Observed improvement and limits

The checklist benchmark preserved all **36,862** binary decisions, avoided **89.45%** of leave-one-out recomputations, and measured a **4.068×** median checking-kernel speedup across five paired passes. It excludes shared setup, normalization, models and orchestration. This demonstrates one computational bottleneck improvement, not 4× faster scientific discovery or an advantage of agents over fixed rules.

The evidence-response evaluation completed one UBA3 run for each of three inputs. Recorded assessments were fragile → supported → fragile for original, decisively changed and excluded-guide-changed data. Two arms are synthetic. The tool supplies checklist verdicts, and a curator-label attribution error was corrected only after those runs. Reliability, generalization and the corrected attribution behavior remain unmeasured.

Each new workflow binds one gene/source hash, allows at most four shared scientific analysis attempts, and enforces a tool-admission deadline. Model-dollar/token costs remain unknown and uncapped. Optional proposal export has an Omnigent ASK approval boundary; policy tests do not establish a live human approval or wet-lab authorization.

## Submission state

The allowlisted source ZIP is prepared at `dist/next-experiment-source.zip`. It excludes credentials and raw account-linked sessions; the public matrix is downloaded separately with exact hash verification.

The existing `demo/video/next-experiment-demo.mp4` is a locally recorded **119.8-second walkthrough of the earlier saved-run interface**, using browser screenshots and synthetic macOS narration. It predates the current panel and UI improvements; it should be reviewed or refreshed before submission. [NARRATION.md](demo/NARRATION.md) describes that recording sequence.

Code, UI, records, package and video are **local**. Verify final HackOS fields, repository visibility and source/data licensing before publishing, then attach the intended artifacts through the authorized submission workflow. No hosted deployment, public repository or hackathon submission is implied.
