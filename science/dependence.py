"""What would change our mind? Deterministic verdict-dependence analysis on observed counts.

Everything here is computed from the same fixed estimator and checklist as science.screen.
Observed items (checklist values, per-guide effects, omit-one-guide, starting-count filter)
are real measurements. Probes marked ``observed: False`` are hypothetical rule probes: they
show how the fixed rule WOULD respond to one additional guide; the data contain no such guide.
"""
from __future__ import annotations

import numpy as np

from science.screen import CONDITIONS, PARAMETERS, summarize_condition

STATUS_COVERAGE = "Insufficient guide coverage"
STATUS_CONFLICT = "Resolve conflicting evidence"
STATUS_WEAK = "Needs stronger support"
STATUS_PASS = "Count signal survives checklist"
FILTER_VARIANTS = (10, 20, 50)
HYPOTHETICAL = "hypothetical_rule_probe"


def verdict(summary: dict, eligible_guides: int) -> str:
    """Single source of truth for the four plain-language verdict labels used by the panel."""
    loo = summary.get("leave_one_out") or {}
    if eligible_guides < PARAMETERS["min_eligible_guides"]:
        return STATUS_COVERAGE
    if loo.get("threshold_reversal"):
        return STATUS_CONFLICT
    if not summary.get("fixed_checklist_pass"):
        return STATUS_WEAK
    return STATUS_PASS


def checklist(summary: dict, eligible_guides: int) -> list[dict]:
    """Each fixed-checklist criterion with its observed value, threshold and pass flag."""
    threshold = PARAMETERS["effect_threshold_log2"]
    repeats = summary.get("repeat_scores") or [None, None]
    loo = summary.get("leave_one_out") or {}
    rows = [
        {"criterion": "eligible_guides", "observed": eligible_guides, "rule": f">= {PARAMETERS['min_eligible_guides']}", "passes": eligible_guides >= PARAMETERS["min_eligible_guides"]},
        {"criterion": "repeat_1_median", "observed": repeats[0], "rule": f">= {threshold}", "passes": repeats[0] is not None and repeats[0] >= threshold},
        {"criterion": "repeat_2_median", "observed": repeats[1], "rule": f">= {threshold}", "passes": repeats[1] is not None and repeats[1] >= threshold},
        {"criterion": "leave_one_out_minimum", "observed": loo.get("score_min"), "rule": f">= {threshold}", "passes": loo.get("score_min") is not None and loo["score_min"] >= threshold},
        {"criterion": "repeat_difference", "observed": summary.get("repeat_difference"), "rule": f"|difference| <= {PARAMETERS['max_repeat_difference_log2']}", "passes": summary.get("repeat_difference") is not None and abs(summary["repeat_difference"]) <= PARAMETERS["max_repeat_difference_log2"]},
        {"criterion": "positive_guide_fraction", "observed": summary.get("positive_guide_fraction"), "rule": f">= {PARAMETERS['min_positive_guide_fraction']}", "passes": summary.get("positive_guide_fraction") is not None and summary["positive_guide_fraction"] >= PARAMETERS["min_positive_guide_fraction"]},
    ]
    for row in rows:
        row["passes"] = bool(row["passes"])
    return rows


def _condition(values: np.ndarray, guides: list[str]) -> tuple[dict, str]:
    summary = summarize_condition(values, guides)
    return summary, verdict(summary, len(values))


def _probe(name: str, values: np.ndarray, guides: list[str], added: np.ndarray, baseline_status: str, meaning: str) -> dict:
    augmented = np.vstack([values, added[None, :]]) if len(values) else added[None, :]
    summary, status = _condition(augmented, [*guides, f"hypothetical_{name}"])
    return {"probe": name, "observed": False, "evidence_type": HYPOTHETICAL, "meaning": meaning,
            "added_guide_repeat_effects": [float(x) for x in added], "eligible_guides_after": int(len(augmented)),
            "score": summary["score"], "status": status, "status_changes": status != baseline_status}


def condition_dependence(values: np.ndarray, guides: list[str], all_guides: list[dict]) -> dict:
    """values: eligible-guide centered log2 effects for one condition (n x 2 repeats)."""
    summary, status = _condition(values, guides)
    threshold = PARAMETERS["effect_threshold_log2"]
    means = values.mean(axis=1) if len(values) else np.array([])
    omit = []
    full_passes_threshold = summary["score"] is not None and summary["score"] >= threshold
    for i, guide in enumerate(guides):
        if len(values) < 2:
            break
        rest = np.delete(values, i, axis=0)
        rest_summary, rest_status = _condition(rest, [g for j, g in enumerate(guides) if j != i])
        omit.append({"omitted_guide": guide, "omitted_guide_effect": float(means[i]), "score": rest_summary["score"],
                     "crosses_threshold": bool((rest_summary["score"] >= threshold) != full_passes_threshold),
                     "status": rest_status, "status_changes": rest_status != status,
                     "note": "Omitting one of three guides also drops coverage below the three-guide minimum." if len(values) == PARAMETERS["min_eligible_guides"] else None})
    # Decisive = the aggregate crosses the effect threshold without this guide (not a mere coverage drop).
    decisive = [row["omitted_guide"] for row in omit if row["crosses_threshold"]]
    failing = [row["criterion"] for row in checklist(summary, len(values)) if not row["passes"]]
    discordant = [{"sgRNA": guide, "effect": float(means[i])} for i, guide in enumerate(guides) if (means[i] < threshold) != (summary["score"] is not None and summary["score"] < threshold)] if len(values) else []
    probes = []
    if len(values):
        concordant_guide = np.median(values, axis=0)
        probes.append(_probe("add_one_concordant_guide", values, guides, concordant_guide, status,
                             "If one additional independent guide reproduced the current per-repeat median effect, this is the fixed-rule verdict. Not an observation."))
        probes.append(_probe("add_one_null_guide", values, guides, np.zeros(values.shape[1]), status,
                             "If one additional independent guide showed no enrichment in either repeat, this is the fixed-rule verdict. Not an observation."))
    shortfall = max(0, PARAMETERS["min_eligible_guides"] - len(values))
    return {"status": status, "score": summary["score"], "eligible_guides": int(len(values)), "checklist": checklist(summary, len(values)),
            "failing_criteria": failing, "guide_effects": all_guides, "omit_one_guide": omit, "decisive_guides": decisive, "discordant_guides": discordant,
            "coverage_shortfall": shortfall, "hypothetical_probes": probes,
            "summary": plain_language(status, summary, guides, means, decisive, discordant, probes, shortfall, failing)}


def plain_language(status, summary, guides, means, decisive, discordant, probes, shortfall, failing) -> str:
    """Deterministic sentence built from the numbers above; not model-generated text."""
    def f(x):
        return f"{x:+.2f}".replace("-", "−")
    threshold = PARAMETERS["effect_threshold_log2"]
    if shortfall:
        return (f"Only {len(guides)} of the gene's guides pass the fixed starting-count filter; {shortfall} more eligible guide{'s' if shortfall != 1 else ''} would be needed before the count rule can give a verdict. "
                "Missing evidence is not a negative result.")
    parts = []
    if discordant:
        agree = [f(m) for i, m in enumerate(means) if guides[i] not in {d['sgRNA'] for d in discordant}]
        parts.append(f"The verdict rests on a {len(agree)}-vs-{len(discordant)} guide split: {', '.join(d['sgRNA'] + ' ' + f(d['effect']) for d in discordant)} disagree{'s' if len(discordant) == 1 else ''} with the other guide{'s' if len(agree) != 1 else ''} ({', '.join(agree)}).")
    else:
        parts.append(f"All {len(guides)} eligible guides fall on the same side of the {threshold} log₂ threshold.")
    if decisive:
        parts.append(f"Without {' or '.join(decisive)}, the aggregate crosses the {threshold} log₂ threshold.")
    else:
        parts.append("No single omitted guide moves the aggregate across the threshold.")
    if status == STATUS_WEAK and failing:
        named = {"repeat_difference": "the two repeats differ by more than the allowed 1.0 log₂", "repeat_1_median": "repeat 1 is below threshold",
                 "repeat_2_median": "repeat 2 is below threshold", "positive_guide_fraction": "too few guides are positive", "leave_one_out_minimum": "a leave-one-out estimate is below threshold"}
        parts.append("Fails because " + "; ".join(named.get(c, c) for c in failing) + ".")
    by_name = {p["probe"]: p for p in probes}
    con, nul = by_name.get("add_one_concordant_guide"), by_name.get("add_one_null_guide")
    if con and nul:
        parts.append(f"Rule probes (hypothetical, not observed): one more agreeing guide → “{con['status']}”; one more null guide → “{nul['status']}”.")
    return " ".join(parts)


def decision_dependence(screen, gene: str) -> dict:
    """Verdict dependence for one gene across both IL6 conditions, from one loaded Screen."""
    if gene == "non-targeting":
        raise ValueError("Non-targeting guides are controls, not candidate genes")
    indices = np.flatnonzero(screen.genes == gene)
    if not len(indices):
        raise ValueError(f"Unknown exact gene symbol: {gene!r}")
    selected = indices[screen.eligible[indices]]
    result = {"gene": gene, "total_guides": int(len(indices)), "eligible_guides": int(len(selected)), "conditions": {},
              "contains_hypothetical_probes": True,
              "reading_guide": "Observed items use real counts. Items marked observed=false are rule probes answering 'what evidence would change the verdict'; they are not measurements."}
    for condition, cols in CONDITIONS.items():
        all_guides = [{"sgRNA": str(screen.guides[i]), "eligible": bool(screen.eligible[i]), "baseline_counts": screen.counts[i, :2].astype(int).tolist(),
                       "mean_effect": float(screen.effects[i][cols].mean()), "repeat_effects": screen.effects[i][cols].tolist()} for i in indices]
        block = condition_dependence(screen.effects[selected][:, cols], screen.guides[selected].tolist(), all_guides)
        block["baseline_filter"] = []
        for threshold in FILTER_VARIANTS:
            subset = indices[np.all(screen.counts[indices, :2] >= threshold, axis=1)]
            summary, status = _condition(screen.effects[subset][:, cols], screen.guides[subset].tolist())
            block["baseline_filter"].append({"min_each_repeat": threshold, "eligible_guides": int(len(subset)), "score": summary["score"], "status": status,
                                             "is_default": threshold == PARAMETERS["baseline_min_each_repeat"], "status_changes": status != block["status"]})
        result["conditions"][condition] = block
    return result
