import json
import pytest
from integration import policy, tools

DIGEST = 'a' * 64


@pytest.fixture
def run(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, 'LIVE', tmp_path / 'live')
    monkeypatch.setattr(policy, 'DB_PATH', tmp_path / 'policy.sqlite3')
    monkeypatch.setattr(policy, 'source_digest', lambda: DIGEST)
    return policy.create_run('UBA3', source_sha256=DIGEST)['id']


def decision(record_id):
    return {'question':'Follow up?', 'gene':'UBA3', 'candidate_tests':[
        {'operation':'guide-check', 'expected_learning':'Detect single-guide dependence', 'feasibility':'Measured guides available', 'cost':'One bounded CPU analysis'},
        {'operation':'context', 'expected_learning':'Detect IL6 dependence', 'feasibility':'Both conditions available', 'cost':'One bounded CPU analysis'}],
        'selected_test':'guide-check', 'selection_reason':'Guide artifact uncertainty is the first constraint; both tests are feasible and equally bounded',
        'measured_evidence':[record_id], 'previous_action':'retain', 'updated_action':'request_additional_evidence',
        'reason':'Sensitivity', 'next_test':'Independent measurement', 'limitations':['Exploratory']}


def measured(run, status='computed', gene='UBA3', operation='guide-check', digest=DIGEST):
    aid, _ = policy.reserve_analysis(run, operation, 'UBA3')
    artifact = tools.append_record('scientific_tool', {'status':status, 'evidence_type':'computed_from_observed_counts', 'tool':operation, 'input_hashes':{'countmatrix.xlsx':digest}, 'observations':{'gene':gene}}, run)
    policy.finish_analysis(aid,'completed',artifact['record_id'])
    return artifact['record_id']


@pytest.mark.parametrize('status,gene,operation', [('failed','UBA3','guide-check'),('computed','TP53','guide-check'),('computed','UBA3','candidate')])
def test_unmeasured_or_unrelated_evidence_is_rejected(run, status, gene, operation):
    rid = measured(run,status,gene,operation)
    with pytest.raises(ValueError):tools.decision_record(json.dumps(decision(rid)),run)


@pytest.mark.parametrize('hyphenated',[False,True])
def test_successful_selected_test_can_support_decision(run, hyphenated):
    rid=measured(run)
    if hyphenated:rid=str(tools.uuid.UUID(rid))
    result=tools.decision_record(json.dumps(decision(rid)),run)
    assert result['status']=='recorded'
    assert policy.inspect_run(run)['status']=='completed'
    assert json.loads(tools.Path(result['artifact']).read_text())['payload']['evaluation_status'].startswith('exploratory')
    with pytest.raises(policy.PolicyDenied):policy.reserve_analysis(run,'context','UBA3')


def test_generic_shell_operation_cannot_run():
    with pytest.raises(ValueError):tools.analyze('shell', 'UBA3')


@pytest.mark.parametrize('change', ['duplicate','missing_cost','wrong_source','cross_run','old_unbounded'])
def test_strict_comparison_and_provenance(run, change):
    rid=measured(run,digest='b'*64 if change=='wrong_source' else DIGEST)
    value=decision(rid)
    if change=='duplicate':value['candidate_tests'][1]=value['candidate_tests'][0]
    if change=='missing_cost':del value['candidate_tests'][0]['cost']
    if change=='cross_run':run=policy.create_run('UBA3',source_sha256=DIGEST)['id']
    if change=='old_unbounded':
        p=tools.LIVE/(rid+'.json');record=json.loads(p.read_text());del record['run_id'];p.write_text(json.dumps(record))
    with pytest.raises(ValueError):tools.decision_record(json.dumps(value),run)


def test_failed_analysis_still_spends_one_attempt(run, monkeypatch):
    import science.screen
    def fail(*args,**kwargs):raise RuntimeError('calculation failed')
    monkeypatch.setattr(science.screen,'run_tool',fail)
    with pytest.raises(RuntimeError):tools.analyze('candidate','UBA3',run)
    stored=policy.inspect_run(run)
    assert stored['attempts']==1 and stored['attempt_records'][0]['status']=='failed'


def test_source_change_stops_before_computation(run,monkeypatch):
    monkeypatch.setattr(policy,'source_digest',lambda:'b'*64)
    with pytest.raises(policy.PolicyDenied):tools.analyze('candidate','UBA3',run)
    assert policy.inspect_run(run)['attempts']==1
