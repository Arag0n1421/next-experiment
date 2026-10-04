"""Evidence-responsiveness invariants for the verdict-dependence tool on the real GEO matrix."""
import json
from pathlib import Path

import numpy as np
import pytest

from integration import policy, tools
from science import dependence
from science.panel import build_panel
from science.screen import Screen, run_tool

ROOT = Path(__file__).resolve().parents[1]
DISCORDANT = "UBA3_-_69129128"   # depleted without IL6 (305/254 -> 6/8 reads), positive with IL6
ENRICHED = ("UBA3_-_69129084", "UBA3_+_69129500")
INELIGIBLE = "UBA3_+_69129471"   # strongly positive but 13/3 starting reads


@pytest.fixture(scope="module")
def screen():
    return Screen.load()


def variant(screen, edit):
    counts = screen.counts.copy()
    edit(counts, {str(g): i for i, g in enumerate(screen.guides)}, screen)
    return Screen(counts, screen.guides, screen.genes, screen.path, screen.digest, screen.mapping_notes)


def statuses(dep):
    return {condition: block["status"] for condition, block in dep["conditions"].items()}


def test_unchanged_input_reproduces_saved_panel_verdicts(screen):
    saved = json.loads((ROOT / "demo/evidence/panel.json").read_text())
    panel = build_panel(screen=screen)
    assert panel["input_hashes"]["countmatrix.xlsx"] == saved["input_hashes"]["countmatrix.xlsx"] == screen.digest
    for fresh, old in zip(panel["candidates"], saved["candidates"]):
        assert fresh["gene"] == old["gene"]
        for condition in ("without_il6", "with_il6"):
            assert fresh["next_experiments"][condition]["status"] == old["next_experiments"][condition]["status"]
            assert fresh["decision_dependence"][condition]["status"] == fresh["next_experiments"][condition]["count_status"]
            assert fresh["decision_dependence"][condition]["score"] == pytest.approx(old["conditions"][condition]["score"])
        assert set(fresh["next_experiments"]["without_il6"]["decision_rule"]) == {"retain", "reject", "more_evidence"}


def test_uba3_dependence_names_the_real_guide_split(screen):
    block = dependence.decision_dependence(screen, "UBA3")["conditions"]["without_il6"]
    assert block["status"] == dependence.STATUS_CONFLICT
    assert [d["sgRNA"] for d in block["discordant_guides"]] == [DISCORDANT]
    assert block["discordant_guides"][0]["effect"] < -4
    assert sorted(block["decisive_guides"]) == sorted(ENRICHED)
    by_guide = {row["omitted_guide"]: row for row in block["omit_one_guide"]}
    assert by_guide[DISCORDANT]["crosses_threshold"] is False and by_guide[DISCORDANT]["score"] > 4
    assert all(by_guide[g]["score"] < 0.5 for g in ENRICHED)
    probes = {p["probe"]: p for p in block["hypothetical_probes"]}
    assert probes["add_one_concordant_guide"]["status"] == dependence.STATUS_PASS
    assert probes["add_one_null_guide"]["status"] == dependence.STATUS_CONFLICT
    assert all(p["observed"] is False and p["evidence_type"] == dependence.HYPOTHETICAL for p in probes.values())
    assert "2-vs-1" in block["summary"] and "hypothetical" in block["summary"]
    filters = {f["min_each_repeat"]: f for f in block["baseline_filter"]}
    assert filters[20]["is_default"] and filters[50]["status"] == dependence.STATUS_COVERAGE


def test_decisive_evidence_change_flips_only_the_targeted_condition(screen):
    def make_concordant(counts, index, _):
        counts[index[DISCORDANT], 2:4] = counts[index[DISCORDANT], 0:2] * 16   # 6/8 reads -> about +4 log2, like the other two guides
    before = statuses(dependence.decision_dependence(screen, "UBA3"))
    after = dependence.decision_dependence(variant(screen, make_concordant), "UBA3")
    assert before["without_il6"] == dependence.STATUS_CONFLICT
    assert after["conditions"]["without_il6"]["status"] == dependence.STATUS_PASS
    assert after["conditions"]["without_il6"]["discordant_guides"] == []
    assert after["conditions"]["with_il6"]["status"] == before["with_il6"]


def test_irrelevant_changes_do_not_move_the_verdict(screen):
    base = dependence.decision_dependence(screen, "UBA3")

    def other_gene(counts, index, s):
        rows = np.flatnonzero(s.genes == "GABRR2")
        counts[rows, 2:] = counts[rows, 2:] * 3

    def excluded_guide(counts, index, _):
        counts[index[INELIGIBLE], 2:] = counts[index[INELIGIBLE], 2:] * 5

    for edit in (other_gene, excluded_guide):
        changed = dependence.decision_dependence(variant(screen, edit), "UBA3")
        assert statuses(changed) == statuses(base)
        for condition in ("without_il6", "with_il6"):
            assert changed["conditions"][condition]["score"] == pytest.approx(base["conditions"][condition]["score"], abs=0.05)
            assert changed["conditions"][condition]["decisive_guides"] == base["conditions"][condition]["decisive_guides"]


def test_coverage_shortfall_is_reported_not_scored(screen):
    block = dependence.decision_dependence(screen, "SAMM50")["conditions"]["without_il6"]
    assert block["status"] == dependence.STATUS_COVERAGE and block["coverage_shortfall"] == 2
    assert all(f["eligible_guides"] == 1 for f in block["baseline_filter"])   # relaxing to 10 reads changes nothing
    assert "not a negative result" in block["summary"]


def test_tool_output_marks_probes_and_rejects_bad_input():
    result = run_tool("dependence", gene="UBA3")
    assert result["status"] == "computed" and result["evidence_type"] == "computed_from_observed_counts"
    assert result["observations"]["contains_hypothetical_probes"] is True
    assert any("observed=false" in line for line in result["limitations"])
    for block in result["observations"]["conditions"].values():
        assert all(p["observed"] is False for p in block["hypothetical_probes"])
    assert run_tool("dependence", gene="NOT_A_GENE")["status"] == "failed"
    assert run_tool("dependence", gene="non-targeting")["status"] == "failed"
    assert run_tool("dependence")["status"] == "failed"


def test_dependence_shares_the_bounded_budget_and_cannot_stand_in_for_the_selected_test(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LIVE", tmp_path / "live")
    monkeypatch.setattr(policy, "DB_PATH", tmp_path / "policy.sqlite3")
    run_id = policy.create_run("UBA3")["id"]
    assert policy.workflow_policy(run_id, "experimentalist")({"type": "tool_call", "target": "screen_analysis", "data": {"name": "screen_analysis", "arguments": {"run_id": run_id, "gene": "UBA3", "operation": "dependence"}}})["result"] == "ALLOW"
    with pytest.raises(policy.PolicyDenied):
        tools.analyze("dependence", "TP53", run_id)
    dep = tools.analyze("dependence", "UBA3", run_id)
    assert dep["status"] == "computed" and dep["observations"]["conditions"]["without_il6"]["decisive_guides"]
    decision = {"question": "Follow up?", "gene": "UBA3", "candidate_tests": [
        {"operation": "guide-check", "expected_learning": "Single-guide dependence", "feasibility": "Counts available", "cost": "One CPU analysis"},
        {"operation": "context", "expected_learning": "IL6 dependence", "feasibility": "Both conditions available", "cost": "One CPU analysis"}],
        "selected_test": "guide-check", "selection_reason": "Guide disagreement is the first uncertainty", "measured_evidence": [dep["saved_evidence"]["record_id"]],
        "previous_action": "retain", "updated_action": "request_additional_evidence", "reason": "Sensitivity", "next_test": "Arrayed guides", "limitations": ["Exploratory"]}
    with pytest.raises(ValueError, match="selected test"):
        tools.decision_record(json.dumps(decision), run_id)
    check = tools.analyze("guide-check", "UBA3", run_id)
    decision["measured_evidence"].append(check["saved_evidence"]["record_id"])
    assert tools.decision_record(json.dumps(decision), run_id)["status"] == "recorded"
    run = policy.inspect_run(run_id)
    # The wrong-gene request was denied before reservation, so it did not spend an attempt.
    assert run["attempts"] == 2 and run["status"] == "completed"
    assert [a["operation"] for a in run["attempt_records"]] == ["dependence", "guide-check"]
