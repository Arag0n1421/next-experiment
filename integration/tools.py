"""No generic filesystem, network, shell or credential access exposed to agents."""
import datetime
import hashlib
import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "runs/live"
from integration import policy
OPERATIONS = policy.OPERATIONS


def append_record(kind, payload, run_id=None):
    LIVE.mkdir(parents=True, exist_ok=True)
    record = {"id": uuid.uuid4().hex, "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "kind": kind, "payload": payload}
    if run_id is not None:
        record["run_id"] = run_id
    encoded = json.dumps(record, allow_nan=False, sort_keys=True)
    path = LIVE / (record["id"] + ".json")
    path.write_text(encoded + "\n")
    # Individual immutable records avoid concurrent append races.
    return {"record_id": record["id"], "artifact": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def analyze(operation, gene, run_id=None):
    if operation not in OPERATIONS:
        raise ValueError("Unsupported operation")
    if operation != "qc" and not re.fullmatch(r"[A-Za-z0-9_.-]{1,40}", gene):
        raise ValueError("Use one exact gene symbol")
    from science.screen import run_tool
    attempt_id, run = policy.reserve_analysis(run_id, operation, gene)
    try:
        bound_path = run.get("source_path")
        actual_digest = policy.source_digest(bound_path) if bound_path else policy.source_digest()
        if actual_digest != run["source_sha256"]:
            raise policy.PolicyDenied("Source file changed after the run was created")
        result = run_tool(operation, gene=gene if operation != "qc" else None, **({"data_path": bound_path} if bound_path else {}))
        if result.get("status") != "computed" or result.get("input_hashes", {}).get("countmatrix.xlsx") != run["source_sha256"]:
            raise policy.PolicyDenied("Analysis did not produce measured evidence from the bound input")
        if operation == "candidate":
            from science.panel import external_context
            result["external_context"] = external_context(gene)
    except BaseException:
        policy.finish_analysis(attempt_id, "failed")
        raise
    if operation == "candidate" and isinstance(result.get("observations"), dict):
        full = result["observations"]
        result = dict(result)
        result["observations"] = {
            "gene": full.get("gene"), "total_guides": full.get("total_guides"),
            "eligible_guides": full.get("eligible_guides"),
            "conditions": {name: {key: value.get(key) for key in ("status", "score", "repeat_scores", "eligible_guides")} for name, value in full.get("conditions", {}).items()},
            "missing_endpoints": full.get("missing_endpoints"),
            "unexecuted_checks": ["guide-check", "context"],
            "optional_diagnostics": ["dependence"],
        }
    # Preserve full observations on disk; limit verbose mapping notes in model context.
    try:
        evidence = append_record("scientific_tool", result, run_id)
        policy.finish_analysis(attempt_id, "completed", evidence["record_id"])
    except BaseException:
        policy.finish_analysis(attempt_id, "failed")
        raise
    if operation == "qc" and isinstance(result.get("observations"), dict):
        result = dict(result)
        result["observations"] = dict(result["observations"])
        notes = result["observations"].get("mapping_notes", [])
        result["observations"]["mapping_notes"] = notes[:5]
        result["observations"]["mapping_notes_truncated_in_response"] = max(0, len(notes)-5)
    return {**result, "saved_evidence": evidence}


def decision_record(decision_json, run_id=None):
    run = policy.check_run(run_id)
    if not isinstance(decision_json, str) or len(decision_json) > 20000:
        raise ValueError("Decision exceeds size limit")
    value = json.loads(decision_json)
    required = {"question", "gene", "candidate_tests", "selected_test", "measured_evidence", "previous_action", "updated_action", "reason", "next_test", "limitations", "selection_reason"}
    if not isinstance(value, dict) or not required.issubset(value):
        raise ValueError("Decision must contain all required fields")
    if not isinstance(value["candidate_tests"], list) or len(value["candidate_tests"]) < 2:
        raise ValueError("Compare at least two tests")
    if value["gene"] != run["gene"]:
        raise ValueError("Decision must use this run's exact gene")
    ids = []
    for candidate in value["candidate_tests"]:
        if not isinstance(candidate, dict) or candidate.get("operation") not in {"guide-check", "context"}:
            raise ValueError("Candidate tests must name supported operations")
        if any(not isinstance(candidate.get(k), str) or not candidate[k].strip() for k in ("expected_learning", "feasibility", "cost")):
            raise ValueError("Each test needs expected_learning, feasibility and cost rationale")
        ids.append(candidate["operation"])
    if len(ids) != len(set(ids)) or set(ids) != {"guide-check", "context"}:
        raise ValueError("Compare two distinct available tests")
    if any(not isinstance(value.get(k), str) or not value[k].strip() for k in ("question", "selection_reason", "reason", "next_test", "previous_action")):
        raise ValueError("Question, selection reason, decision reason, next test and previous action must be nonempty")
    if not isinstance(value["limitations"], list) or not value["limitations"] or any(not isinstance(v,str) or not v.strip() for v in value["limitations"]):
        raise ValueError("Record explicit limitations")
    if value["updated_action"] not in {"retain", "reject", "restrict_to_context", "request_additional_evidence"}:
        raise ValueError("Invalid updated action")
    if not isinstance(value["measured_evidence"], list) or not value["measured_evidence"]:
        raise ValueError("Measured evidence must cite saved scientific-tool record IDs")
    if value["selected_test"] not in {"guide-check", "context"}:
        raise ValueError("Selected test must be the exact executed operation: guide-check or context")
    selected_test_found = False
    for item in value["measured_evidence"]:
        if not isinstance(item, str) or not re.fullmatch(r"[a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",item):
            raise ValueError("Evidence references must be record IDs")
        record = LIVE / (uuid.UUID(item).hex + ".json")
        if not record.is_file():
            raise ValueError("Evidence record is missing or not a scientific tool result")
        stored = json.loads(record.read_text())
        payload = stored.get("payload", {})
        if stored.get("run_id") != run_id or payload.get("input_hashes", {}).get("countmatrix.xlsx") != run["source_sha256"]:
            raise ValueError("Evidence must match this exact run and input SHA256")
        attempts = policy.inspect_run(run_id)["attempt_records"]
        if not any(a["status"] == "completed" and a["record_id"] == stored.get("id") for a in attempts):
            raise ValueError("Evidence must be from a successful reserved analysis in this run")
        if stored.get("kind") != "scientific_tool" or payload.get("status") != "computed" or payload.get("evidence_type") != "computed_from_observed_counts":
            raise ValueError("Evidence must be a successful measured scientific tool result")
        if payload.get("observations", {}).get("gene") != value["gene"]:
            raise ValueError("Evidence must refer to the decision's exact gene")
        selected_test_found |= payload.get("tool") == value["selected_test"]
    if not selected_test_found:
        raise ValueError("No measured evidence from the selected test")
    if "count_assessment" in value:
        assessment = value["count_assessment"]
        if not isinstance(assessment, dict) or assessment.get("condition") not in {"without_il6", "with_il6"} or assessment.get("status") not in {"fragile", "supported", "insufficient"} or not isinstance(assessment.get("reason"), str) or not assessment["reason"].strip():
            raise ValueError("Count assessment needs condition, fragile/supported/insufficient status and reason")
    counterfactual = any(json.loads((LIVE / (uuid.UUID(item).hex + ".json")).read_text())["payload"].get("input_kind") == "counterfactual_evaluation" for item in value["measured_evidence"])
    value["input_kind"] = "counterfactual_evaluation" if counterfactual else "observed_public_data"
    value["evaluation_status"] = ("Synthetic input evaluation only; not a biological finding" if counterfactual else "exploratory; no held-out advantage demonstrated")
    artifact = append_record("decision", value, run_id)
    policy.close_run(run_id, artifact["record_id"])
    return {"status": "recorded", "run_id": run_id, **artifact}


def export_proposal(decision_id, run_id):
    """Called only behind the configured Omnigent ASK gate; makes a local copy."""
    run = policy.check_run(run_id, allow_completed=True)
    if run["status"] != "completed" or decision_id != run["decision_id"]:
        raise ValueError("Only this run's final recorded decision can be exported")
    record = json.loads((LIVE / (decision_id + ".json")).read_text())
    if record.get("kind") != "decision" or record.get("run_id") != run_id:
        raise ValueError("Decision provenance mismatch")
    return {"status": "exported_locally", **append_record("reviewed_proposal", {
        "decision_id": decision_id, "next_test": record["payload"]["next_test"],
        "limitations": record["payload"]["limitations"],
        "approval_boundary": "Omnigent function-policy ASK before tool dispatch",
        "execution_status": "proposed_only; no experiment authorized or performed",
    }, run_id)}
