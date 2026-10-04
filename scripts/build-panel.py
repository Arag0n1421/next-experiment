#!/usr/bin/env python3
"""Recompute the bounded panel from the packaged observed count matrix."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from science.panel import build_panel

if __name__ == "__main__":
    result = build_panel()
    evaluation = ROOT / "runs/counterfactual/EVALUATION.json"
    if evaluation.exists():
        report = json.loads(evaluation.read_text())
        if report.get("status") == "completed":
            result["agent_evaluation"] = report
    output = ROOT / "demo/evidence/panel.json"
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(output)
    for row in result["candidates"]:
        print(row["gene"], row["next_experiments"]["without_il6"]["status"])
