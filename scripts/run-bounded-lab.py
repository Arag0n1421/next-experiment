#!/usr/bin/env python3
"""Create one immutable scope and compile bound Omnigent specs before launch."""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import yaml
from integration import policy


def prepare(gene="UBA3", seconds=900, max_analyses=4, panel_priority=None, condition="without_il6"):
    preflight = None
    if panel_priority:
        from science.panel import build_panel
        panel = build_panel()
        gene = panel["rankings"][condition][panel_priority][0]
        preflight = {"selected_gene": gene, "priority": panel_priority, "condition": condition,
                     "selection_rule": panel["ranking_rules"][panel_priority], "input_hashes": panel["input_hashes"],
                     "panel": [{"gene": c["gene"], "score": c["conditions"][condition]["score"],
                                "eligible_guides": c["eligible_guides"],
                                "context": c["external_context"]["evidence"]["label"]} for c in panel["candidates"]]}
    run = policy.create_run(gene=gene, seconds=seconds, max_analyses=max_analyses, data_path=os.environ.get("NEXT_EXPERIMENT_DATA"))
    out = ROOT / "runs/bounded" / run["id"]
    agent_dir = out / "lab"
    shutil.copytree(ROOT / "agents/lab", agent_dir, ignore=shutil.ignore_patterns("__pycache__"))
    for file in agent_dir.rglob("config.yaml"):
        spec = yaml.safe_load(file.read_text())
        role = "planner" if file.parent == agent_dir else spec["name"]
        spec["guardrails"] = {"ask_timeout": 120, "policies": {"run_scope": {
            "type": "function", "function": {"path": "integration.policy.workflow_policy", "arguments": {"run_id": run["id"], "role": role}}}}}
        spec["prompt"] = (
            f"BOUND RUN: run_id={run['id']}; gene={gene}; maximum {max_analyses} scientific analysis attempts shared across all roles; tool-admission deadline={run['deadline']}. "
            "Include this exact run_id in every custom tool call. Use this exact gene. "
            "When sending a child, use its exact role name as title (scientist, experimentalist, critic). Never override the child's model. "
            "Successful record_decision closes scientific work. A proposal export requires a separate human approval; do not request it unless the user asks.\n\n"
        ) + spec["prompt"]
        if preflight and role == "planner":
            spec["prompt"] += "\nPANEL PREFLIGHT (computed rules, not a previous AI decision):\n" + json.dumps(preflight)
        file.write_text(yaml.safe_dump(spec, sort_keys=False, width=100))
    receipt = {**run, "agent_dir": str(agent_dir), "policy_handler": "integration.policy.workflow_policy", "model_cost_usd": None, "model_cost_note": "Subscription harness usage is unpriced; no dollar cap is claimed", "deadline_semantics": "Blocks new tool admissions after deadline; does not interrupt an already running model or scientific call"}
    if preflight:
        receipt["panel_preflight"] = preflight
    (out / "run.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gene", default="UBA3")
    parser.add_argument("--seconds", default=900, type=int)
    parser.add_argument("--max-analyses", default=4, type=int)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--panel-priority", choices=["resolve_uncertainty", "count_support"])
    parser.add_argument("--condition", choices=["without_il6", "with_il6"], default="without_il6")
    args, omni_args = parser.parse_known_args()
    run = prepare(args.gene, args.seconds, args.max_analyses, args.panel_priority, args.condition)
    print(json.dumps(run, indent=2), flush=True)
    if args.prepare_only:
        return
    os.environ["HARNESS_CODEX_DISABLE_NATIVE_TOOLS"] = "true"
    os.environ["HARNESS_CODEX_ENABLE_WEB_SEARCH"] = "false"
    os.environ["PATH"] = str(ROOT / ".venv/bin") + os.pathsep + os.environ.get("PATH", "")
    os.chdir(ROOT)
    executable = str(ROOT / ".venv/bin/omni")
    os.execv(executable, [executable, "run", run["agent_dir"], "--server", "local", *omni_args])


if __name__ == "__main__":
    main()
