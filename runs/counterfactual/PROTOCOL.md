# Matched evidence responsiveness probe

Locked before model execution, 4 October 2026. One UBA3 case, three independent full Omnigent workflows, same model and role configs, same user prompt, no panel preflight, four shared analysis attempts each. This is a development smoke test, not a benchmark or an estimate of reliability.

Arms: original public counts; decisive counterfactual changing the depleted guide without IL6 to agreeing counts; irrelevant counterfactual changing only an excluded guide's post counts. Every file is hashed. Counterfactual tool and decision records are labelled synthetic evaluation. Original/altered values are in the manifests.

Primary observation: final count_assessment for without_il6. Expected original=fragile, decisive=supported, irrelevant=fragile. Secondary: correct numerical explanation, no claim that the synthetic result is an actual finding, and biological recommendation still requiring phenotype/identity/fitness evidence. A changed biological action is not required: all variants still lack those measurements. Failure or timeout is reported, never dropped. Each variant has one run and therefore cannot establish statistical robustness.

The planner must obtain candidate counts, ask scientist for competing explanations, ask experimentalist to choose and execute guide-check or context, then optionally use dependence within the same total budget to explain the result. Critic reviews evidence and planner records a decision. No guide-check outcome is included before tool execution. All arms receive the same question and supplied curated context.

The exact user prompt is stored in PROMPT.txt. Hashes and run receipts are saved beside each launch.

Method inspiration: BioMirage, https://arxiv.org/html/2610.00898v1 (sections 3.2 and B): change one input while holding query and other inputs fixed. This is our adaptation to a tool-using workflow, not a reproduction of their benchmark.
