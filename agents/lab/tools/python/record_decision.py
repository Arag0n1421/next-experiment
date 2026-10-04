from omnigent_client.tools import tool


@tool
def record_decision(decision_json: str, run_id: str) -> dict:
    """Save a structured decision tied to existing measured scientific-tool record IDs.

    Args:
        decision_json: JSON with question, gene, candidate_tests, selected_test, measured_evidence, previous_action, updated_action, reason, next_test limitations and selection_reason. candidate_tests contains objects with operation, expected_learning, feasibility and cost.
        run_id: Exact run ID supplied by the launcher.
    """
    from integration.tools import decision_record
    return decision_record(decision_json, run_id)
