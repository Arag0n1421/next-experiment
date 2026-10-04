"""Run-scoped limits shared by all Omnigent worker processes."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "runs/policy.sqlite3"
ROLES = {"scientist", "experimentalist", "critic"}
OPERATIONS = {"qc", "candidate", "guide-check", "context", "triage", "dependence"}


class PolicyDenied(ValueError):
    pass


@contextmanager
def transaction():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=20, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.executescript("""
    CREATE TABLE IF NOT EXISTS runs (
      id TEXT PRIMARY KEY, gene TEXT NOT NULL, source_sha256 TEXT NOT NULL,
      created REAL NOT NULL, deadline REAL NOT NULL, max_analyses INTEGER NOT NULL,
      attempts INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'active',
      decision_id TEXT);
    CREATE TABLE IF NOT EXISTS attempts (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL, operation TEXT NOT NULL,
      started REAL NOT NULL, finished REAL, status TEXT NOT NULL, record_id TEXT);
    CREATE TABLE IF NOT EXISTS roles (
      run_id TEXT NOT NULL, role TEXT NOT NULL, PRIMARY KEY(run_id, role));
    """)
    db.execute("BEGIN IMMEDIATE")
    # Migrate under the write lock: concurrent workers cannot add this column twice.
    if "source_path" not in {r[1] for r in db.execute("PRAGMA table_info(runs)")}:
        db.execute("ALTER TABLE runs ADD COLUMN source_path TEXT")
    try:
        yield db
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    finally:
        db.close()


def source_digest(path=None):
    from science.screen import DEFAULT_DATA
    return hashlib.sha256((Path(path) if path else DEFAULT_DATA).read_bytes()).hexdigest()


def create_run(gene="UBA3", max_analyses=4, seconds=900, source_sha256=None, data_path=None):
    if not isinstance(gene, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,40}", gene):
        raise PolicyDenied("Use one exact gene symbol")
    if type(max_analyses) is not int or not 1 <= max_analyses <= 4:
        raise PolicyDenied("Analysis limit must be between one and four")
    if type(seconds) is not int or not 10 <= seconds <= 3600:
        raise PolicyDenied("Tool-admission window must be 10 to 3600 seconds")
    bound_path = str(Path(data_path).resolve(strict=True)) if data_path is not None else None
    actual = source_digest(bound_path) if bound_path else None
    if actual and source_sha256 and actual != source_sha256:
        raise PolicyDenied("Explicit source path and SHA256 disagree")
    digest = source_sha256 or actual or source_digest()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise PolicyDenied("An exact input SHA256 is required")
    run_id, now = uuid.uuid4().hex, time.time()
    with transaction() as db:
        db.execute("INSERT INTO runs(id,gene,source_sha256,created,deadline,max_analyses,source_path) VALUES(?,?,?,?,?,?,?)", (run_id,gene,digest,now,now+seconds,max_analyses,bound_path))
    return inspect_run(run_id)


def _get(db, run_id, allow_completed=False):
    if not isinstance(run_id, str) or not re.fullmatch(r"[a-f0-9]{32}", run_id):
        raise PolicyDenied("A valid launcher-created run_id is required")
    row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if row is None:
        raise PolicyDenied("Unknown run_id")
    if row["deadline"] <= time.time():
        raise PolicyDenied("Run tool-admission deadline reached")
    if row["status"] != "active" and not (allow_completed and row["status"] == "completed"):
        raise PolicyDenied("Run is closed")
    return dict(row)


def inspect_run(run_id):
    with transaction() as db:
        row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise PolicyDenied("Unknown run_id")
        value = dict(row)
        value["attempt_records"] = [dict(r) for r in db.execute("SELECT * FROM attempts WHERE run_id=? ORDER BY started", (run_id,))]
        value["roles"] = [r[0] for r in db.execute("SELECT role FROM roles WHERE run_id=? ORDER BY role", (run_id,))]
        return value


def check_run(run_id, gene=None, allow_completed=False):
    with transaction() as db:
        run = _get(db, run_id, allow_completed)
        if gene is not None and gene != run["gene"]:
            raise PolicyDenied("This run is restricted to its original exact gene")
        return run


def reserve_analysis(run_id, operation, gene):
    if operation not in OPERATIONS:
        raise PolicyDenied("Unsupported scientific operation")
    with transaction() as db:
        run = _get(db, run_id)
        if gene != run["gene"]:
            raise PolicyDenied("This run is restricted to its original exact gene")
        if run["attempts"] >= run["max_analyses"]:
            raise PolicyDenied("Run scientific-analysis budget exhausted")
        aid = uuid.uuid4().hex
        db.execute("UPDATE runs SET attempts=attempts+1 WHERE id=?", (run_id,))
        db.execute("INSERT INTO attempts(id,run_id,operation,started,status) VALUES(?,?,?,?,?)", (aid,run_id,operation,time.time(),"started"))
        return aid, run


def finish_analysis(attempt_id, status, record_id=None):
    with transaction() as db:
        db.execute("UPDATE attempts SET finished=?, status=?, record_id=? WHERE id=? AND status='started'", (time.time(),status,record_id,attempt_id))


def close_run(run_id, decision_id):
    with transaction() as db:
        _get(db, run_id)
        db.execute("UPDATE runs SET status='completed',decision_id=? WHERE id=?", (decision_id,run_id))


def workflow_policy(run_id=None, role="planner"):
    """Omnigent 0.16 function factory. Missing run binding fails closed."""
    def evaluate(event):
        if event.get("type") not in {"tool_call", "request", "llm_request"}:
            return {"result": "ALLOW"}
        try:
            if event.get("type") != "tool_call":
                check_run(run_id, allow_completed=True)
                return {"result": "ALLOW"}
            data = event.get("data") or {}
            name = event.get("target") or data.get("name", "")
            arguments = data.get("arguments") or {}
            # The runner can namespace local tools when exposing them through MCP.
            name = name.split("__")[-1]
            if name == "sys_agent_start":
                # Omnigent synthesizes this lifecycle event BEFORE initializing
                # the inbox. It is not an agent-callable scientific capability.
                check_run(run_id)
                expected_name = "next-experiment" if role == "planner" else role
                if arguments.get("agent_name") != expected_name or arguments.get("harness") != "codex" or arguments.get("sandbox") is not None:
                    raise PolicyDenied("Unexpected agent startup configuration")
                return {"result": "ALLOW"}
            permitted = {"sys_read_inbox", "sys_session_get_info"}
            if role == "planner":
                permitted |= {"screen_analysis", "record_decision", "export_proposal", "sys_session_send"}
            elif role == "experimentalist":
                permitted |= {"screen_analysis"}
            if name not in permitted:
                raise PolicyDenied("Tool is outside this role's declared capability allowlist")
            run = check_run(run_id, allow_completed=name in {"export_proposal", "sys_read_inbox", "sys_session_get_info"})
            if name in {"screen_analysis", "record_decision", "export_proposal"} and arguments.get("run_id") != run_id:
                raise PolicyDenied("Tool run_id does not match this agent's bound run")
            if name == "sys_session_send":
                target = arguments.get("agent")
                if target not in ROLES or arguments.get("title") != target or arguments.get("session_id"):
                    raise PolicyDenied("Use a declared role and that exact role as its stable title")
                overrides = arguments.get("args")
                if overrides is not None and not isinstance(overrides, (str, dict)):
                    raise PolicyDenied("Child args must be text or an object")
                if isinstance(overrides, dict) and (overrides.get("model") or overrides.get("harness")):
                    raise PolicyDenied("Model and harness overrides are disabled")
                # Reusing the same (agent,title) continues one child by Omnigent's contract.
                with transaction() as db:
                    _get(db, run_id)
                    db.execute("INSERT OR IGNORE INTO roles(run_id,role) VALUES(?,?)", (run_id,target))
            if name == "export_proposal":
                if run["status"] != "completed" or arguments.get("decision_id") != run["decision_id"]:
                    raise PolicyDenied("A completed decision must be available before requesting human approval")
                from integration.tools import LIVE
                record = json.loads((LIVE / (run["decision_id"] + ".json")).read_text())
                if record.get("kind") != "decision" or record.get("run_id") != run_id:
                    raise PolicyDenied("Decision provenance does not match")
                proposal = record["payload"]["next_test"]
                return {"result": "ASK", "reason": f"Approve saving this proposed next test as a human-reviewed local export? {proposal} Decision: {run['decision_id']}. Approval saves a local copy only; it does not send, publish, or authorize an experiment."}
            return {"result": "ALLOW"}
        except (ValueError, TypeError, KeyError, OSError, sqlite3.Error):
            return {"result": "DENY", "reason": "Run policy denied: invalid scope, exhausted/expired run, or capability outside the allowlist."}
    return evaluate
