"""Same checklist decisions; optional early return after a decisive failure."""
from __future__ import annotations
import numpy as np
from science.screen import PARAMETERS


def evaluate(values, guides=None, *, adaptive=True):
    values = np.asarray(values, dtype=float)
    if values.ndim != 2 or values.shape[1] != 2 or not np.isfinite(values).all():
        raise ValueError('Expected finite guide x two-repeat effects')
    count = len(values)
    checks = 0
    omissions = 0
    failures = []
    # Lazy statistics ensure a decided candidate does not pay for later checks.
    repeats = None
    means = None
    for name in ('coverage', 'repeat_one', 'repeat_two', 'repeat_agreement', 'positive_guides', 'guide_sensitivity'):
        checks += 1
        if name == 'coverage':
            passed = count >= PARAMETERS['min_eligible_guides']
        elif name in ('repeat_one', 'repeat_two', 'repeat_agreement'):
            if repeats is None:
                repeats = np.median(values, axis=0) if count else np.array([np.nan, np.nan])
            if name == 'repeat_agreement':
                passed = abs(repeats[1] - repeats[0]) <= PARAMETERS['max_repeat_difference_log2']
            else:
                passed = repeats[0 if name == 'repeat_one' else 1] >= PARAMETERS['effect_threshold_log2']
        else:
            if means is None:
                means = values.mean(axis=1)
            if name == 'positive_guides':
                passed = count > 0 and float((means > 0).mean()) >= PARAMETERS['min_positive_guide_fraction']
            else:
                # Evaluate all omissions if reached: do not optimize the eager
                # method differently or hide an unfavorable omitted guide.
                scores = [float(np.median(np.delete(means, i))) for i in range(count)] if count >= 2 else []
                omissions += len(scores)
                passed = bool(scores) and min(scores) >= PARAMETERS['effect_threshold_log2']
        if not passed:
            failures.append(name)
            if adaptive:
                break
    return {'passed': not failures, 'check_count': checks, 'loo_omissions': omissions,
            'stop_reason': failures[0] if failures else 'all_checks_passed',
            'executed_checks': checks, 'skipped_checks': 6-checks,
            'scope': 'same heuristic checklist decision; not biological validation'}
