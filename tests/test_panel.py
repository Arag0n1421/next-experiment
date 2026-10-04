import copy
import json
from pathlib import Path

import pytest
from science.panel import build_panel, external_context, next_experiment
from science.screen import Screen


@pytest.fixture(scope="module")
def computed():
    return build_panel(screen=Screen.load())


def test_actual_guide_conflict_and_published_context(computed):
    c = next(c for c in computed["candidates"] if c["gene"] == "UBA3")
    s = c["conditions"]["without_il6"]
    assert s["score"] == pytest.approx(4.1740042212)
    assert s["leave_one_out"]["score_min"] < 0
    assert c["next_experiments"]["without_il6"]["status"] == "Resolve conflicting evidence"
    assert c["external_context"]["evidence"]["published_screen_statistics"]["IL6m|FDR"] == .02


def test_essentiality_is_not_veto_and_unknown_is_unknown(computed):
    c = next(c for c in computed["candidates"] if c["gene"] == "SAMM50")
    assert c["external_context"]["evidence"]["essentiality"]["isEssential"] is True
    assert c["next_experiments"]["without_il6"]["status"] == "Insufficient guide coverage"
    assert external_context("NOT_CURATED")["evidence"]["label"] == "Context not curated"


def test_decisive_change_updates_rule_but_metadata_does_not(computed):
    c = copy.deepcopy(next(c for c in computed["candidates"] if c["gene"] == "UBA3"))
    context = c["external_context"]
    before = next_experiment(c, context, "without_il6")
    c["gene"] = "MASKED"
    assert next_experiment(c, context, "without_il6") == before
    c["eligible_guides"] = 1
    assert next_experiment(c, context, "without_il6")["status"] == "Insufficient guide coverage"
    # This checks deterministic decision-support behavior, not LLM responsiveness.


def test_priorities_are_disclosed_and_change_order(computed):
    r = computed["rankings"]["without_il6"]
    assert r["resolve_uncertainty"][0] == "UBA3"
    assert r["count_support"][0] == "TP53"
    assert set(r["count_support"]) == set(r["resolve_uncertainty"])
    tp53 = next(c for c in computed["candidates"] if c["gene"] == "TP53")
    assert tp53["conditions"]["without_il6"]["fixed_checklist_pass"]
    assert tp53["next_experiments"]["without_il6"]["status"] == "Published cell-identity concern"
    json.dumps(computed, allow_nan=False)


@pytest.mark.parametrize("genes", [["UBA3"], ["UBA3", "UBA3"], list(map(str, range(13)))])
def test_scope_is_bounded(genes):
    with pytest.raises(ValueError):
        build_panel(genes)
