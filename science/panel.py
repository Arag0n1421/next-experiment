"""Bounded, deterministic decision support. No model or efficacy claims."""
import datetime
import hashlib
import json
from pathlib import Path

from science.screen import Screen, PARAMETERS
from science.dependence import decision_dependence, verdict

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "data/biological-context.json"
DEFAULT_GENES = ("UBA3", "SAMM50", "AK2", "TP53", "CDKN1A", "GABRR2")


def external_context(gene):
    raw = CONTEXT.read_bytes()
    pack = json.loads(raw)
    return {"evidence_type": "curated_external_context", "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
            "retrieved_date": pack["retrieved_date"], "source_hashes": pack["source_hashes"],
            "matrix_warning": pack["source_matrix_warning"],
            "curation_note": pack.get("curation_note", "Labels and decision implications are curator summaries, not direct publication findings."),
            "evidence": pack["genes"].get(gene, {"gene": gene, "label": "Context not curated", "published_context": "No curated evidence available. Do not infer absence of supporting literature."})}


SOURCE_METHODS = ("The source study validated selected hits with two independent sgRNAs per gene, SA-β-gal staining and "
                  "flow cytometry of MSC identity markers (CD29, CD44, CD73, CD90). Wu et al., Genome Biology 26:233 (2025), Results and Methods.")


def decision_rule(status):
    """Proposed qualitative criteria for a future biological follow-up; not registered or calibrated."""
    return {
        "retain": "At least two independent guides with confirmed target suppression reproduce reduced senescence while preserving MSC identity and acceptable cell fitness. Assess proliferation separately to distinguish senescence effects from growth alone.",
        "reject": "Adequately suppressing guides consistently fail to reproduce the proposed senescence benefit, or the benefit accompanies loss of MSC identity or impaired viability.",
        "more_evidence": "Target suppression, guide agreement, biological replication, cell identity or fitness remains unresolved. The three-guide count-screen checklist does not define the required size of this follow-up experiment.",
    }


def next_experiment(candidate, context, condition):
    summary = candidate["conditions"][condition]
    loo = summary.get("leave_one_out") or {}
    if context["evidence"].get("cell_identity_concern"):
        title = "Keep the strong signal as a reference, not the rejuvenation lead."
        question = "Can an alternative reproduce the senescence effect while preserving MSC identity?"
        change = "A strong count effect alone is insufficient: prioritize evidence that the intended phenotype improves without the published cell-identity problem."
        status = "Published cell-identity concern"
    elif candidate["eligible_guides"] < PARAMETERS["min_eligible_guides"]:
        title = "Resolve guide coverage before making a new screen call."
        question = "Does the result persist with adequate starting representation and confirmed target suppression?"
        change = "Reassess once sufficient independent guides have usable coverage; the present missing evidence is not a negative result."
        status = "Insufficient guide coverage"
    elif loo.get("threshold_reversal"):
        title = "Find out why the guides disagree."
        question = "Do independent guides reproduce a senescence phenotype after target suppression is confirmed?"
        change = "Concordant phenotype and preserved cell identity would support advancing; an effect isolated to one guide would motivate guide-specific investigation."
        status = "Resolve conflicting evidence"
    elif not summary["fixed_checklist_pass"]:
        title = "Resolve repeat and context sensitivity."
        question = "Does the effect reproduce across independent biological repeats and the relevant inflammatory context?"
        change = "Reproducibility within a defined context supports a narrower claim; disagreement supports collecting more evidence."
        status = "Needs stronger support"
    else:
        title = "Separate a senescence effect from growth alone."
        question = "Does the count signal accompany reduced senescence while preserving cell identity and fitness?"
        change = "Advance only if the relevant phenotype, cell identity and fitness evidence support the intended research objective."
        status = "Count signal survives checklist"
    return {"status": status, "title": title, "question": question,
            "design": "Compare independent CRISPRi guides with non-targeting controls in the relevant IL6 contexts; confirm target suppression and use independent biological repeats.",
            "readouts": ["Target suppression", "Senescence phenotype", "MSC identity", "Cell fitness / proliferation"],
            "decision_change": change, "decision_rule": decision_rule(status), "source_methods": SOURCE_METHODS,
            "count_status": verdict(summary, candidate["eligible_guides"]), "source_context": context["evidence"]["label"],
            "execution_status": "Proposed research design; not executed or a validated protocol"}


def build_panel(genes=DEFAULT_GENES, screen=None):
    genes = list(genes)
    if not 2 <= len(genes) <= 12 or len(set(genes)) != len(genes):
        raise ValueError("Choose 2–12 distinct exact gene symbols")
    screen = screen or Screen.load()
    candidates = []
    for gene in genes:
        candidate = screen.candidate(gene)
        context = external_context(gene)
        dependence = decision_dependence(screen, gene)
        for condition, block in dependence["conditions"].items():
            if block["status"] != verdict(candidate["conditions"][condition], candidate["eligible_guides"]):
                raise ValueError(f"Count-verdict mismatch for {gene} {condition}")
        candidates.append({**candidate, "external_context": context,
                           "decision_dependence": dependence["conditions"],
                           "next_experiments": {condition: next_experiment(candidate, context, condition)
                                                for condition in candidate["conditions"]}})
    rankings = {}
    for condition in ("without_il6", "with_il6"):
        rankings[condition] = {
            "count_support": [r["gene"] for r in sorted(candidates, key=lambda r: (
                -int(r["conditions"][condition]["fixed_checklist_pass"]),
                -(r["conditions"][condition]["score"] if r["conditions"][condition]["score"] is not None else float('-inf')), r["gene"]))],
            "resolve_uncertainty": [r["gene"] for r in sorted(candidates, key=lambda r: (
                -int(bool((r["conditions"][condition].get("leave_one_out") or {}).get("threshold_reversal")) and r["eligible_guides"] >= 3),
                -(r["conditions"][condition]["score"] if r["conditions"][condition]["score"] is not None else float('-inf')), r["gene"]))]}
    return {"schema_version": 1, "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "question": "Which gene should we test next—and what evidence would change our mind?",
            "status": "computed", "selection_method": "Explicit deterministic decision-support rules; no model ranking or held-out benefit claimed",
            "panel_selection": "Five preselected illustrative genes (UBA3, SAMM50, AK2, TP53, CDKN1A) plus GABRR2, a high-scoring checklist-pass comparison. This is a development panel, not a benchmark.",
            "ranking_rules": {"count_support": "Checklist pass first, then descending count effect, then gene name. This ranks count support, not biological usefulness.",
                              "resolve_uncertainty": "At least three guides and a leave-one-out threshold reversal first, then descending effect, then gene name. This is a heuristic, not estimated information gain."},
            "input_hashes": {"countmatrix.xlsx": screen.digest, "biological-context.json": hashlib.sha256(CONTEXT.read_bytes()).hexdigest()},
            "parameters": PARAMETERS, "rankings": rankings, "candidates": candidates,
            "limitations": ["Screen counts measure relative persistence/expansion, not rejuvenation or longevity.",
                            "Published results and curated context are external evidence, not discoveries by this build.",
                            "Context coverage is incomplete. Essentiality flags do not reject candidates.",
                            "Added-guide probes are hypothetical changes to the fixed rule, not observations or predictions of experiment outcomes.",
                            "No new biological experiments or measured agent selection advantage."]}
