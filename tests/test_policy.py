import asyncio
import concurrent.futures
import importlib.util
import multiprocessing
import time
from pathlib import Path

import pytest
from integration import policy


def reserve_worker(path, run_id):
    policy.DB_PATH=Path(path)
    try:
        policy.reserve_analysis(run_id,'candidate','UBA3')
        return True
    except policy.PolicyDenied:
        return False


@pytest.fixture
def run(tmp_path,monkeypatch):
    monkeypatch.setattr(policy,'DB_PATH',tmp_path/'policy.sqlite3')
    return policy.create_run('UBA3',source_sha256='a'*64)['id']


def event(name,args=None):
    return {'type':'tool_call','target':name,'data':{'name':name,'arguments':args or {}}}


def test_processes_share_exact_four_attempt_cap(run):
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
        results=list(pool.map(reserve_worker,[str(policy.DB_PATH)]*12,[run]*12))
    assert sum(results)==4
    assert policy.inspect_run(run)['attempts']==4


def test_fixed_gene_and_missing_run_fail_closed(run):
    with pytest.raises(policy.PolicyDenied):policy.reserve_analysis(run,'candidate','TP53')
    with pytest.raises(policy.PolicyDenied):policy.reserve_analysis(None,'candidate','UBA3')
    assert policy.inspect_run(run)['attempts']==0


def test_deadline_blocks_new_admissions(run,monkeypatch):
    expired=policy.inspect_run(run)['deadline']+1
    monkeypatch.setattr(policy.time,'time',lambda:expired)
    with pytest.raises(policy.PolicyDenied):policy.reserve_analysis(run,'candidate','UBA3')


def test_roles_bound_to_three_stable_sessions_and_no_overrides(run):
    gate=policy.workflow_policy(run)
    for role in ['scientist','experimentalist','critic']:
        assert gate(event('sys_session_send',{'agent':role,'title':role}))['result']=='ALLOW'
    assert gate(event('sys_session_send',{'agent':'scientist','title':'scientist','args':'Assess the measured count evidence'}))['result']=='ALLOW'
    assert gate(event('sys_session_send',{'agent':'scientist','title':'scientist','args':17}))['result']=='DENY'
    assert len(policy.inspect_run(run)['roles'])==3
    assert gate(event('sys_session_send',{'agent':'scientist','title':'a-new-session'}))['result']=='DENY'
    assert gate(event('sys_session_send',{'agent':'scientist','title':'scientist','args':{'model':'other'}}))['result']=='DENY'
    assert gate(event('sys_session_send',{'session_id':'anything'}))['result']=='DENY'
    assert gate(event('sys_session_create'))['result']=='DENY'


def test_actual_omnigent_runner_gate_asks_before_export_and_denies_shell(run,tmp_path,monkeypatch):
    from omnigent.runner.policy import RunnerToolPolicyGate
    from omnigent.spec.types import AgentSpec, FunctionPolicySpec, FunctionRef, GuardrailsSpec
    from omnigent.spec import parse
    spec=parse(policy.ROOT/'agents/lab')
    spec.guardrails=GuardrailsSpec(policies=[FunctionPolicySpec(name='bounded',on=None,function=FunctionRef(path='integration.policy.workflow_policy',arguments={'run_id':run,'role':'planner'}))])
    gate=RunnerToolPolicyGate.from_spec(spec)
    assert not gate.is_empty
    assert asyncio.run(gate.evaluate_tool_call('export_proposal',{'run_id':run,'decision_id':'unused'})).action=='deny'
    assert asyncio.run(gate.evaluate_tool_call('shell',{'command':'anything'})).action=='deny'
    assert asyncio.run(gate.evaluate_tool_call('screen_analysis',{'run_id':'wrong'})).action=='deny'
    assert asyncio.run(gate.evaluate_tool_call('screen_analysis',{'run_id':run,'gene':'UBA3','operation':'candidate'})).action=='allow'
    from integration import tools
    monkeypatch.setattr(tools,'LIVE',tmp_path/'live')
    artifact=tools.append_record('decision',{'next_test':'Measure all three guides independently.'},run)
    policy.close_run(run,artifact['record_id'])
    verdict=asyncio.run(gate.evaluate_tool_call('export_proposal',{'run_id':run,'decision_id':artifact['record_id']}))
    assert verdict.action=='ask'
    assert 'all three guides' in verdict.reason
    assert not list(tools.LIVE.glob('reviewed_proposal*'))


def test_source_agent_specs_fail_closed_without_launcher():
    from omnigent.runner.policy import RunnerToolPolicyGate
    from omnigent.spec import parse
    spec=parse(policy.ROOT/'agents/lab')
    gate=RunnerToolPolicyGate.from_spec(spec)
    assert asyncio.run(gate.evaluate_tool_call('screen_analysis',{'run_id':'anything'})).action=='deny'


def test_specialists_cannot_export_or_delegate(run):
    for role in ['scientist','experimentalist','critic']:
        gate=policy.workflow_policy(run,role)
        assert gate(event('export_proposal',{'run_id':run}))['result']=='DENY'
        assert gate(event('sys_session_send',{'agent':'scientist','title':'scientist'}))['result']=='DENY'


@pytest.mark.parametrize('role',['planner','scientist','experimentalist','critic'])
def test_actual_omnigent_agent_start_gate_initializes_bound_roles(run,role):
    from omnigent.runner.app import _evaluate_agent_start_gate
    from omnigent.spec import parse
    from omnigent.spec.types import FunctionPolicySpec, FunctionRef, GuardrailsSpec
    path=policy.ROOT/'agents/lab'
    if role!='planner':path=path/'agents'/role
    spec=parse(path)
    spec.guardrails=GuardrailsSpec(policies=[FunctionPolicySpec(name='bounded',on=None,function=FunctionRef(path='integration.policy.workflow_policy',arguments={'run_id':run,'role':role}))])
    verdict=asyncio.run(_evaluate_agent_start_gate(spec,'codex'))
    assert verdict is not None and verdict.action=='allow'
    assert asyncio.run(_evaluate_agent_start_gate(spec,'claude')).action=='deny'
