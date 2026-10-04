import numpy as np
import pytest
from benchmark.triage import evaluate
from science.screen import summarize_condition


def test_random_and_boundary_panels_match_existing_scientific_reference():
    rng=np.random.default_rng(71)
    panels=[np.empty((0,2)),np.array([[2.,2.]]),np.full((3,2),0.5),np.array([[0.5,1.5]]*3),np.array([[0.5,1.500001]]*3)]
    panels += [rng.normal(loc=mean,size=(count,2)) for mean in [-1,0,0.5,1,3] for count in range(1,9) for _ in range(3)]
    for values in panels:
        ref=summarize_condition(values,[str(i) for i in range(len(values))])['fixed_checklist_pass']
        eager=evaluate(values,adaptive=False)
        adaptive=evaluate(values,adaptive=True)
        assert eager['passed']==adaptive['passed']==ref
        assert adaptive['loo_omissions']<=eager['loo_omissions']


def test_decisive_failure_skips_work_but_passing_candidate_keeps_full_check():
    failing=np.array([[4.,4.]])
    assert evaluate(failing)['stop_reason']=='coverage'
    assert evaluate(failing)['loo_omissions']==0
    passing=np.full((5,2),2.)
    assert evaluate(passing)['passed']
    assert evaluate(passing)['loo_omissions']==5


def test_guide_sensitive_signal_still_fails_after_cheap_checks_pass():
    values=np.array([[-1.,-1.],[1.,1.],[4.,4.]])
    result=evaluate(values)
    assert result['stop_reason']=='guide_sensitivity'
    assert result['loo_omissions']==3


@pytest.mark.parametrize('values',[np.ones(3),np.zeros((3,3)),np.array([[float('nan'),1.]])])
def test_invalid_measurements_fail(values):
    with pytest.raises(ValueError):evaluate(values)
