# Bounded scientific runs and human review

Start a new scoped session with `./scripts/run-lab.sh --gene UBA3 -p "Check this candidate and choose the next test."`, or omit `-p` to use the interactive REPL. The launcher creates a fresh run, binds the selected gene and the current count-matrix SHA256, and inserts the same run ID into the planner and all three specialists. `--prepare-only` writes the receipt and agent bundle without invoking a model. Existing historical run records remain unchanged.

## Enforced boundaries

| Boundary | Enforcement |
|---|---|
| At most four scientific analysis attempts across the whole run | A SQLite `BEGIN IMMEDIATE` transaction reserves an attempt before calculation. All worker processes use the same ledger. Exceptions, changed source input and unsuccessful calculations still spend their reserved attempt. Concurrent requests cannot each see and spend the same final slot. |
| One exact gene and input file | Each calculation validates the launch-bound gene and source SHA256. Every saved scientific record carries the run ID and the source hash. |
| Default 15-minute admission window | Policy and tools reject new calls after the deadline. The launcher accepts a shorter window or a maximum of one hour. This is an admission limit, not a guarantee that an already running model or calculation is interrupted at that second. |
| Bounded child session names | Only the planner can call `sys_session_send`; only scientist, experimentalist and critic are allowed, each with its exact role as its stable title. Omnigent reuses the same `(agent, title)` child. Arbitrary session IDs, `sys_session_create`, model overrides and harness overrides are denied. Repeated messages to an existing child are possible within the deadline; there is no hard model-turn cap. |
| Role capability allowlist | Planner: measured analysis, final decision, proposal export, named child dispatch and inbox/status. Experimentalist: measured analysis and inbox/status. Scientist and critic: inbox/status only. Other tools are denied by the function policy. Native Codex tools and web search must also remain disabled on the actual Omnigent server. The launcher sets the relevant server environment variables; an already running server must have been started with those settings. |
| Structured choice between tests | A final decision must compare distinct `guide-check` and `context` tests. Each needs explicit expected learning, feasibility and cost reasoning, plus a selection reason. The record must cite at least one actual execution of the selected operation. These are qualitative cost estimates, not measured model prices. The optional `dependence` and `triage` operations spend the same shared attempts and may be cited as supporting evidence, but neither can replace the executed selected test (tested in `tests/test_dependence.py`). |
| Evidence cannot be borrowed from another run | Final decisions require successful reserved calculations with matching run ID, input SHA256, exact gene and operation. Old unbounded records, failed results, unrelated genes and mismatched source versions are rejected. |
| Scientific loop closes on a final decision | Saving a valid final decision changes the ledger state to completed. Further scientific calculations and child dispatches are denied. |

The function guardrail is `integration.policy.workflow_policy`, loaded by Omnigent's installed function-policy API. The source specs intentionally contain an unbound run and fail closed if invoked directly. The launcher writes bound copies under `runs/bounded/<run-id>/lab/`. That bundle is the runnable submission artifact for a specific session. The central ledger is `runs/policy.sqlite3`; a launch receipt is `runs/bounded/<run-id>/run.json`.

## Human approval

The optional `export_proposal` tool is available only to the planner after a complete final decision. Before dispatch, the Omnigent function policy returns **ASK**, including the exact proposed next test and the decision ID. Omnigent owns the human approval interaction, with a 120-second timeout. Declining or timing out does not produce an approved export.

If a human approves through Omnigent, the tool saves a separate local `reviewed_proposal` record. The tool cannot send, publish, purchase, deploy, modify a scientific result, or conduct a wet-lab experiment. The export marks the next test as proposed only. Export approval is not experiment authorization. The normal discovery loop does not automatically request this export.

The ASK boundary was verified through the actual installed `RunnerToolPolicyGate` in an integration test. This verifies policy resolution and the pre-dispatch ASK verdict; it does **not** claim a human approved anything or that a live UI approval was exercised. No approval was fabricated to produce a demo.

## Costs and limitations

The current model uses an authenticated subscription harness. Model-dollar cost is **unknown**, not zero, and no dollar/token cap is claimed. We enforce scientific calculation attempts and a tool-admission window. `resource_use.api_cost_usd=0` inside deterministic scientific-tool output refers only to that local calculation, not the surrounding LLM workflow.

The framework still runs trusted Python tools on the local host. This is a constrained research workflow, not an OS security sandbox against a malicious project maintainer. Local owners can edit files or the ledger; agents are not given those capabilities. Omnigent source specs and the policy package must travel together. Restarting the model server or modifying authentication is not part of this change.

## Verification

`python -m pytest tests/test_policy.py tests/test_integration.py -q` covers 24 tests, including cross-process contention (12 attempts, exactly four admitted), expiry, wrong-gene scope, failed-attempt accounting, changed data, structured test comparisons, successful finalization, old/cross-run evidence rejection, stable child names, string/object dispatch arguments, actual Omnigent ASK, disallowed shell tools and fail-closed unbound specs, and the real Omnigent startup gate for all four bound roles. The broader science/benchmark test suite is run separately by the main build verification.

## Runtime initialization correction

Omnigent evaluates an internal `sys_agent_start` lifecycle event before constructing a session inbox. The policy explicitly admits this event only for the bound role name, Codex harness and declared no-sandbox configuration. A regression calls the installed `_evaluate_agent_start_gate` for all four roles. Without this admission, initialization fails even though later fallback tool calls may run; the visible error is a missing parent inbox. This was diagnosed from the initialization code and actual runner logs, rather than attributed to terminal mode.

## Explicit evaluation inputs

When NEXT_EXPERIMENT_DATA is set, the launcher persists the exact resolved source path with its SHA256 in the run ledger. Workers load that bound file rather than relying on their inherited environment. A changed file is rejected and the attempt is recorded as failed. Existing default-data runs remain compatible. Files named COUNTERFACTUAL-* are labelled counterfactual_evaluation in scientific-tool and decision records; they are synthetic evaluation fixtures and are not served as observed screen data.

A structured optional count_assessment can report fragile, supported or insufficient evidence for a specified condition. It is distinct from the biological updated_action: count robustness cannot supply missing phenotype, cell identity or fitness measurements. This field is schema-checked; scientific correctness still requires inspecting the measured evidence.
