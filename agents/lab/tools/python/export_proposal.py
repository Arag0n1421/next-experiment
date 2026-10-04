from omnigent_client.tools import tool


@tool
def export_proposal(decision_id: str, run_id: str) -> dict:
    """Ask the human to approve a local copy of a completed next-test proposal.

    Args:
        decision_id: Saved final decision ID for this run.
        run_id: Exact run ID supplied by the launcher.
    """
    from integration.tools import export_proposal as export
    return export(decision_id, run_id)
