"""An explicit run input must survive tool-worker environment boundaries."""
import hashlib
import pytest
from integration import policy, tools
from science import screen, panel


def test_bound_input_reaches_worker_and_drift_is_denied(tmp_path, monkeypatch):
    monkeypatch.setattr(policy, "DB_PATH", tmp_path / "policy.sqlite3")
    monkeypatch.setattr(tools, "LIVE", tmp_path / "live")
    fixture = tmp_path / "COUNTERFACTUAL-test.xlsx"
    fixture.write_bytes(b"fixture supplied to mocked loader")
    digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
    seen = []
    def measured(operation, gene, data_path):
        seen.append(data_path)
        return {"status": "computed", "tool": operation,
                "evidence_type": "computed_from_observed_counts",
                "input_kind": "counterfactual_evaluation",
                "input_hashes": {"countmatrix.xlsx": digest}, "observations": {"gene": gene}}
    monkeypatch.setattr(screen, "run_tool", measured)
    run = policy.create_run(data_path=fixture)
    assert run["source_path"] == str(fixture.resolve())
    result = tools.analyze("guide-check", "UBA3", run["id"])
    assert seen == [str(fixture.resolve())]
    assert result["input_kind"] == "counterfactual_evaluation"
    fixture.write_bytes(b"changed after binding")
    with pytest.raises(policy.PolicyDenied, match="changed"):
        tools.analyze("guide-check", "UBA3", run["id"])
    assert policy.inspect_run(run["id"])["attempt_records"][-1]["status"] == "failed"


def test_explicit_path_cannot_claim_another_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(policy, "DB_PATH", tmp_path / "policy.sqlite3")
    fixture = tmp_path / "input.xlsx"
    fixture.write_bytes(b"fixture")
    with pytest.raises(policy.PolicyDenied, match="disagree"):
        policy.create_run(data_path=fixture, source_sha256="0" * 64)


def test_missing_context_finishes_the_reserved_attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(policy, "DB_PATH", tmp_path / "policy.sqlite3")
    monkeypatch.setattr(policy, "source_digest", lambda: "a" * 64)
    monkeypatch.setattr(screen, "run_tool", lambda *a, **k: {"status": "computed", "input_hashes": {"countmatrix.xlsx": "a" * 64}})
    def missing(gene):
        raise FileNotFoundError("context missing")
    monkeypatch.setattr(panel, "external_context", missing)
    run = policy.create_run(source_sha256="a" * 64)
    with pytest.raises(FileNotFoundError):
        tools.analyze("candidate", "UBA3", run["id"])
    assert policy.inspect_run(run["id"])["attempt_records"][0]["status"] == "failed"
