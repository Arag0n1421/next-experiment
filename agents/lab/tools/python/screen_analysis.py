from omnigent_client.tools import tool


@tool
def screen_analysis(operation: str, gene: str, run_id: str) -> dict:
    """Execute a bounded analysis on real published screen counts and save evidence.

    Args:
        operation: Exactly qc, candidate, guide-check, context, triage or dependence.
        gene: Exact gene symbol fixed by the launcher, also for qc.
        run_id: Exact run ID supplied in the system instructions.
    """
    from integration.tools import analyze
    return analyze(operation, gene, run_id)

