#!/usr/bin/env python3
"""Paired evidence-responsiveness probe: real matrix versus one labelled counterfactual matrix.

Deterministic layer (run here): the fixed verdict flips when the decisive evidence changes and
stays when an irrelevant row changes. Agent layer (NOT run here): prints the two launcher commands
that would bind separate Omnigent runs to each file by SHA256. No model call is made by this script;
the agent-level outcome is UNMEASURED until the operator runs both commands and compares decisions.

The counterfactual file is synthetic by construction, lives only under runs/counterfactual/, carries a
COUNTERFACTUAL- prefix and a manifest listing every edited cell. It is never served by the demo.
"""
import argparse
import datetime
import hashlib
import json
import sys
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from openpyxl import Workbook, load_workbook

from science.dependence import decision_dependence
from science.screen import COLUMNS, DEFAULT_DATA, Screen

OUT = ROOT / "runs/counterfactual"
EDITS = {
    "decisive": {"description": "UBA3_-_69129128 without-IL6 counts set to 16x its D0 counts (6/8 reads -> 4880/4064), making the depleted guide concordant.",
                 "cells": {"UBA3_-_69129128": {"IL6m_rep1": 4880, "IL6m_rep2": 4064}}},
    "irrelevant": {"description": "Excluded guide UBA3_+_69129471 post counts tripled; it fails the starting-count filter so the eligible-guide verdict should not move.",
                   "cells": {"UBA3_+_69129471": {"IL6m_rep1": 576, "IL6m_rep2": 471, "IL6p_rep1": 582, "IL6p_rep2": 552}}},
}


def write_counterfactual(name: str, source: Path) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"COUNTERFACTUAL-{name}-countmatrix.xlsx"
    edits = EDITS[name]["cells"]
    wb_in = load_workbook(source, read_only=True, data_only=True)
    rows = wb_in.active.iter_rows(values_only=True)
    header = list(next(rows))
    wb = Workbook()
    ws = wb.active
    ws.title = "CountMatrix"
    ws.append(header)
    changed = []
    for row in rows:
        row = list(row)
        if row[0] in edits:
            for column, value in edits[row[0]].items():
                i = header.index(column)
                changed.append({"sgRNA": row[0], "column": column, "before": row[i], "after": value})
                row[i] = value
        ws.append(row)
    wb_in.close()
    wb.save(target)
    manifest = {"synthetic": True, "name": name, "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "description": EDITS[name]["description"], "source": str(source.name), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "counterfactual_file": str(target.name), "counterfactual_sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "edited_cells": changed}
    (OUT / f"COUNTERFACTUAL-{name}-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def deterministic_probe(real: Path, counterfactual: Path, gene: str = "UBA3") -> dict:
    before = decision_dependence(Screen.load(real), gene)["conditions"]
    after = decision_dependence(Screen.load(counterfactual), gene)["conditions"]
    return {condition: {"before": before[condition]["status"], "after": after[condition]["status"], "changed": before[condition]["status"] != after[condition]["status"]} for condition in before}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--edit", choices=sorted(EDITS), default="decisive")
    parser.add_argument("--gene", default="UBA3", choices=["UBA3"])
    args = parser.parse_args()
    if len(EDITS[args.edit]["cells"]) != 1 or not all(c in COLUMNS for cells in EDITS[args.edit]["cells"].values() for c in cells):
        raise SystemExit("Harness edits must touch exactly one guide row and known columns")
    manifest = write_counterfactual(args.edit, DEFAULT_DATA)
    probe = deterministic_probe(DEFAULT_DATA, OUT / manifest["counterfactual_file"], args.gene)
    report = {"deterministic_layer": {"status": "measured", "verdicts": probe}, "manifest": manifest,
              "agent_layer": {"status": "UNMEASURED: no Omnigent run launched by this script",
                              "paired_commands": [
                                  f".venv/bin/python scripts/run-bounded-lab.py --gene {args.gene} --prepare-only",
                                  f"NEXT_EXPERIMENT_DATA={shlex.quote(str(OUT / manifest['counterfactual_file']))} .venv/bin/python scripts/run-bounded-lab.py --gene {args.gene} --prepare-only"],
                              "comparison": "Run both without --prepare-only and with the identical -p prompt from runs/counterfactual/PROTOCOL.md. Compare count_assessment separately from updated_action and next_test. No panel preflight is supplied to either arm. Each run is bound to its own input SHA256, so the records cannot be confused.",
                              "stability_control": "Repeat with --edit irrelevant; a justified unchanged decision is the expected result."}}
    (OUT / f"COUNTERFACTUAL-{args.edit}-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["deterministic_layer"], indent=2))
    print("Agent layer:", report["agent_layer"]["status"])


if __name__ == "__main__":
    main()
