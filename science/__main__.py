"""Allowlisted CLI: python -m science qc|candidate|guide-check|context|baseline."""
import argparse
import datetime as dt
import json
import time
from pathlib import Path

import numpy as np

from .screen import DEFAULT_DATA, ROOT, LIMITATIONS, PARAMETERS, Screen


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def save(path, value):
    path.write_text(json.dumps(clean(value), indent=2, allow_nan=False) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, default=DEFAULT_DATA)
    p.add_argument("--output-dir", type=Path, default=ROOT / "runs/baseline")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("qc")
    sub.add_parser("baseline")
    for command in ("candidate", "guide-check", "context"):
        sub.add_parser(command).add_argument("gene")
    args = p.parse_args()
    started = time.perf_counter()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        screen = Screen.load(args.data)
        observations, artifacts = None, []
        if args.command == "qc":
            observations = screen.qc()
        elif args.command == "baseline":
            table = screen.table()
            csv = args.output_dir / "gene-scores.csv"
            table.to_csv(csv, index=False, float_format="%.6f")
            qc = args.output_dir / "qc.json"
            save(qc, screen.qc())
            artifacts.extend([str(csv.resolve()), str(qc.resolve())])
            top = {}
            for short, label in (("m", "without_il6"), ("p", "with_il6")):
                effect = table.loc[table.eligible_guides >= PARAMETERS["min_eligible_guides"]].sort_values(f"{short}_mean", ascending=False)
                robust = table.loc[table[f"{short}_fixed_checklist_pass"]].sort_values(f"{short}_mean", ascending=False)
                top[label] = {"effect_only_top_10": clean(effect.head(10).to_dict("records")), "fixed_checklist_top_10": clean(robust.head(10).to_dict("records")), "fixed_checklist_count": len(robust), "eligible_candidate_count": len(effect)}
            observations = {"guide_rows": len(screen.genes), "scored_gene_count": len(table), "scope": "exploratory_full_dataset_both_repeats", "rankings": top, "comparison_status": "No independent confirmation benchmark or method advantage measured"}
        else:
            candidate = screen.candidate(args.gene)
            if args.command == "candidate":
                observations = candidate
            elif args.command == "guide-check":
                observations = {"gene": args.gene, "eligible_guides": candidate["eligible_guides"], "conditions": {k: {"score": v["score"], "leave_one_out": v["leave_one_out"], "fixed_checklist_pass": v["fixed_checklist_pass"]} for k,v in candidate["conditions"].items()}, "baseline_count_sensitivity": candidate["baseline_count_sensitivity"]}
            else:
                observations = {"gene": args.gene, **candidate["context"]}
        name = args.command + ("-" + args.gene if hasattr(args, "gene") else "") + ".json"
        if not all(c.isalnum() or c in "._-" for c in name):
            raise ValueError("Gene output identifier must contain only letters, digits, dot, underscore or hyphen")
        output = args.output_dir / name
        artifacts.append(str(output.resolve()))
        result = {"status": "computed", "tool": args.command, "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "evidence_type": "computed_from_observed_counts", "input_hashes": {str(screen.path): screen.digest}, "parameters": PARAMETERS, "artifact_paths": artifacts, "observations": observations, "limitations": LIMITATIONS, "duration_seconds": round(time.perf_counter() - started, 4), "resource_use": {"model_calls": 0, "api_cost_usd": 0, "external_compute": False}}
        save(output, result)
        print(json.dumps(clean(result), allow_nan=False))
    except (ValueError, OSError) as e:
        print(json.dumps({"status": "failed", "tool": args.command, "error": str(e), "duration_seconds": round(time.perf_counter()-started, 4)}))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
