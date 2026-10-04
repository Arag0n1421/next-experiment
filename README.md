# Next Experiment

**Better next experiments for longevity research.**

Next Experiment helps longevity researchers decide which gene-screen findings deserve follow-up—and what evidence would change their minds.

A promising score is only the start. Researchers still need to check whether independent measurements agree and whether a candidate's apparent benefit comes with changes in cell identity or fitness. Next Experiment brings those questions into one reviewable workflow, so the next experiment targets the uncertainty that matters. Its intended benefit is better use of follow-up effort; reduced research cost or time has not yet been measured.

The prototype investigates public [aging-related CRISPRi screening data](https://pmc.ncbi.nlm.nih.gov/articles/PMC12326738/). Different targeting sequences, called guides, provide measurements for each gene. A strong combined score can hide disagreement between those guides. An Omnigent lab compares possible checks, executes a computational test and records what the result changes about the next decision.

In the completed UBA3 investigation, a strong aggregate count signal became unstable when a guide was removed. The lab requested more guide-resolved evidence before immediate prioritization. That is the current research contribution: a traceable path from promising signal to a justified next test. The data measure relative guide persistence or expansion; they do not establish rejuvenation or longer life.

## What the project does

| Part | What happens | What to review |
| --- | --- | --- |
| Six-gene evidence panel | Fixed rules compare saved count analyses for UBA3, SAMM50, AK2, TP53, CDKN1A and GABRR2, in both IL6 conditions. Curated, source-linked biological context accompanies the counts. | `/panel`: compare the same gene across conditions; inspect guide disagreement, source context and proposed follow-up. |
| Omnigent investigation | When the launcher runs, a Planner, Scientist, Experimentalist and Critic exchange evidence, compare two tests, execute the selected computational analysis and save an updated decision. | [Agent specifications](agents/lab/config.yaml), [execution policies](POLICY.md), and the saved records. |
| Saved-run replay | The browser reconstructs an actual completed UBA3 investigation. Navigation displays saved evidence; it does not start model inference. | `/`: follow question → hypotheses → test choice → result → changed decision. |

Panel ordering is a disclosed deterministic heuristic. Its literature and essentiality context is a curated snapshot, not live literature retrieval or a model-generated ranking. Both browser pages display saved results. Proposed biological experiments and hypothetical added-guide examples are labelled separately from observations.

## Try it in two minutes

Open [the public demo](https://arag0n1421.github.io/next-experiment/panel/) or inspect [the public repository](https://github.com/Arag0n1421/next-experiment). The browser review requires no sign-in and displays saved calculations and recorded agent results. The local setup below provides the same review path.

1. **Inspect UBA3.** Open the panel at `/panel`, choose **Without IL6** and **UBA3**, then select **Inspect the guides**. The aggregate signal is about **+4.174**; leaving one guide out produces **−0.055**. This is a sensitivity check on existing data, and explains why the next step requests more guide-resolved evidence.
2. **Compare the same gene across conditions.** Change **Screen condition** to **With IL6**. UBA3 remains selected, so its measurements can be compared directly. Changing the research priority is a separate action that selects the first gene in its newly ordered shortlist.
3. **Look beyond a high score.** Choose **TP53** and read **What the published evidence adds**. The source paper's cell-identity concern remains visible even when count support is strong. Count support alone is not an aging benefit.
4. **Follow the executed investigation.** Select **Follow the executed agent run**. Review the competing explanations, two possible tests, selected guide-sensitivity analysis, observed result and updated decision. The next biological experiment remains proposed.
5. **Inspect the implementation.** Use [the jury review map](reviews/JURY-REVIEW-MAP.md), [agent specifications](agents/lab/config.yaml), [scientific tools](science/screen.py) and [permissions](POLICY.md) to trace the claims to code and records. [BRIEF-COMPLIANCE.md](BRIEF-COMPLIANCE.md) maps the challenge requirements.

Starting a new Omnigent investigation is a separate action using the launcher below and requires your own supported model-provider login. Browser navigation does not run agents or spend model credits.

## What we observed

UBA3's approximate no-IL6 count-enrichment score is **4.174**. Removing one eligible guide changes it to **−0.055**. The completed investigation requests more guide-resolved evidence before immediate prioritization; it does not reject the gene. The proposed next experiment measures target suppression, senescence, cell identity and fitness. That experiment has not been performed.

The matched computational benchmark compares early-stop and exhaustive execution of identical checklist rules. Across **36,862 gene-condition decisions**, every binary verdict was preserved and **89.45%** of guide-removal recomputations were avoided. Five paired timing passes gave a **4.068×** median checklist-kernel speedup. Loading, normalization, model inference and orchestration are excluded. See [the measured result](runs/benchmark/REPORT.md) and [locked protocol](benchmark/PROTOCOL.md).

Three separately executed Omnigent investigations assessed original UBA3 data as **fragile**, a decisive synthetic change as **supported**, and an excluded-guide synthetic change as **still fragile**. This is one development case, one completed run per variant, using tool-supplied rule verdicts. A source-attribution error in one explanation was corrected in the current context snapshot after those runs; the saved evaluation predates that correction. See [the full evaluation](runs/counterfactual/EVALUATION.json) and [post-run review](runs/counterfactual/POST-RUN-REVIEW.md).

## Run the browser review locally

No model login is needed to inspect saved results. Use the existing `.venv`, or create a fresh Python 3.12+ environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e . pytest
.venv/bin/python scripts/download-data.py
.venv/bin/python scripts/build-demo.py
.venv/bin/python scripts/build-panel.py
.venv/bin/python scripts/serve-demo.py
```

Open <http://127.0.0.1:6768/panel> for the comparison or <http://127.0.0.1:6768/> for the agent replay. The server uses a file allowlist and binds to the local loopback interface.

## Execute a new Omnigent investigation

This step starts actual agents and requires your own supported provider login. Model-dollar and token costs are unmeasured; there is no claimed monetary cap.

```sh
.venv/bin/python -m pip install 'omnigent==0.16.0'
.venv/bin/omni setup
.venv/bin/python setup/apply-compatibility-patch.py
HARNESS_CODEX_DISABLE_NATIVE_TOOLS=true HARNESS_CODEX_ENABLE_WEB_SEARCH=false .venv/bin/omni server --background --no-open
./scripts/run-lab.sh --gene UBA3 --seconds 900 -p "Check UBA3, compare guide-check and context, execute one and record the next decision."
```

The narrow compatibility patch accepts only the inspected Omnigent 0.16.0 source version. No credentials are bundled. Native-tool settings must apply when the server starts; an existing server must already have the required settings.

Alternatively, `./scripts/run-lab.sh --panel-priority resolve_uncertainty -p "Run the bound discovery loop and save the evidence-based next experiment."` binds the rule-selected candidate before running the same workflow. `--prepare-only` prepares the bound agent bundle without invoking a model.

Each new run binds one gene and exact source hash, shares **at most four analysis attempts** across all roles and enforces a tool-admission deadline. Roles have explicit tool permissions. The optional proposal export requests human approval through Omnigent; approval only exports a local proposed experiment, and does not authorize performing it. See [POLICY.md](POLICY.md) for the enforced boundary and verification.

## Verify and package

Full policy and runner-gate tests require the pinned Omnigent installation, without provider login or new model inference.

```sh
.venv/bin/python -m pip install 'omnigent==0.16.0'
.venv/bin/python -m pytest -q
.venv/bin/python -m benchmark.run
.venv/bin/python scripts/package-source.py
```

[SCIENCE.md](SCIENCE.md) documents the estimator, sources, controls and assumptions. The GEO matrix and publisher supplement differ; published beta/FDR values are external context, not ground truth for our approximate estimator. No statistical reproduction, new biological discovery, preserved cell identity, rejuvenation, longevity benefit or agent-selection advantage is established.

[DELIVERY.md](DELIVERY.md) records implementation verification. [SUBMISSION.md](SUBMISSION.md) lists the artifacts and submission steps. The source repository and saved-evidence browser demo are public. The existing 119.8-second narrated walkthrough documents an earlier local interface. Preparing the three submission videos (each no longer than 60 seconds) and completing final submissions are separate steps.

## License

The project's original software and documentation are available under the [MIT License](LICENSE). External research data, publications and third-party source materials retain their own terms; see the [license scope notes](LICENSE-NOTES.md).
