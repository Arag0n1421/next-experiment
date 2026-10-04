'use strict';
const roles = [
  ['QUESTION + MEASUREMENT', 'A strong signal is a reason to investigate.', "The Planner measures UBA3's existing guide counts and asks whether its high effect-only ranking justifies further work. The initial no-IL6 enrichment estimate is 4.174.", 'A specific question, measured input and bounded specialist tasks.'],
  ['COMPETING EXPLANATIONS', 'A biological effect—or an unstable measurement?', 'The Scientist frames two explanations: a real context-associated count effect, or guide-specific behavior and pooled-count variability. Relative persistence of guide-bearing cells does not establish rejuvenation.', 'A narrow claim and two explanations that the next test should distinguish.'],
  ['TEST SELECTION + EXECUTION', 'Check what happens when each guide is removed.', 'The Experimentalist compares guide sensitivity with IL6 context analysis. It selects guide sensitivity because the guides may disagree, then runs the tool on the observed counts.', 'A measured sensitivity result, with every guide omission and all declared thresholds.'],
  ['REVIEW + UPDATED DECISION', 'Ask for better evidence before prioritizing.', 'The Critic finds that the no-IL6 interpretation is fragile. The Planner records a changed action: request additional evidence, then test the three guides individually. Context dependence alone does not justify rejection.', 'An updated action, evidence record IDs and one proposed next measurement.'],
];

function bindTabs(selector, activate) {
  const buttons = Array.from(document.querySelectorAll(selector));
  function select(index, focus = false) {
    buttons.forEach((b, i) => { b.setAttribute('aria-selected', String(i === index)); b.tabIndex = i === index ? 0 : -1; });
    activate(index);
    if (focus) buttons[index].focus();
  }
  buttons.forEach((button, index) => {
    button.addEventListener('click', () => select(index));
    button.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % buttons.length;
      if (event.key === 'ArrowLeft') next = (index - 1 + buttons.length) % buttons.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = buttons.length - 1;
      if (next !== undefined) { event.preventDefault(); select(next, true); }
    });
  });
}
bindTabs('[data-step]', index => {
  ['role-kind', 'role-title', 'role-description', 'role-output'].forEach((id, i) => {
    document.getElementById(id).textContent = (i === 3 ? 'Output → ' : '') + roles[index][i];
  });
  document.getElementById('role-panel').setAttribute('aria-labelledby', `role-tab-${index}`);
});
bindTabs('[data-evidence]', index => {
  for (let i = 0; i < 3; i++) document.getElementById(`evidence-panel-${i}`).hidden = i !== index;
});

function element(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}
const fixed = value => Number(value).toFixed(3).replace(/^-/, '−');

async function loadEvidence() {
  try {
    const responses = await Promise.all(['candidate', 'guide-check', 'decision'].map(name => fetch(`/next-experiment/evidence/${name}.json`)));
    if (responses.some(r => !r.ok)) throw new Error('Missing evidence');
    const [candidate, check, decision] = await Promise.all(responses.map(r => r.json()));
    if (candidate.id !== '452fda4c1e084b9d9b1ae4fea2e1e39f' || check.id !== 'd8edc9f95f0c4934ae9b4358fd89e98f' || decision.payload.selected_test !== 'guide-check') throw new Error('Unexpected evidence');
    const no = check.payload.observations.conditions.without_il6;
    const yes = check.payload.observations.conditions.with_il6;
    const rows = [{label: 'All 3 guides', value: no.score, withValue: yes.score}, ...no.leave_one_out.omissions.map((o, i) => ({label: `Omit guide ${i + 1}`, guide: o.omitted_guide, value: o.score, withValue: yes.leave_one_out.omissions.find(p => p.omitted_guide === o.omitted_guide).score}))];
    const chart = document.getElementById('chart');
    const table = document.getElementById('measurement-rows');
    rows.forEach(row => {
      const line = element('div', undefined, `chart-row${row.value < .5 ? ' weak' : ''}`);
      const label = element('span', row.label, 'chart-label');
      if (row.guide) label.title = row.guide;
      const track = element('div', undefined, 'bar-track');
      const bar = element('div', undefined, 'bar');
      // Diverging bars preserve sign around a visible zero baseline.
      const width = Math.min(48, Math.abs(row.value) / 4.5 * 48);
      bar.style.width = `${width}%`;
      bar.style.marginLeft = `${row.value < 0 ? 50 - width : 50}%`;
      track.append(bar);
      line.append(label, track, element('span', fixed(row.value), 'chart-value'));
      chart.append(line);
      const tr = document.createElement('tr');
      tr.append(element('td', row.guide ? `${row.label}: ${row.guide}` : row.label), element('td', fixed(row.value)), element('td', fixed(row.withValue)));
      table.append(tr);
    });
    const strict = check.payload.observations.baseline_count_sensitivity.find(x => x.baseline_min_each_repeat === 50);
    const tr = document.createElement('tr');
    tr.append(element('td', 'Stricter starting count ≥50 (2 guides)'), element('td', fixed(strict.conditions.without_il6.score)), element('td', fixed(strict.conditions.with_il6.score)));
    table.append(tr);
    document.getElementById('analysis-seconds').textContent = check.payload.duration_seconds;
    document.getElementById('score-range').textContent = `${fixed(no.leave_one_out.score_min)} to ${fixed(no.leave_one_out.score_max)}`;
  } catch (error) {
    document.getElementById('data-error').hidden = false;
    document.querySelector('.run-badge').textContent = 'EVIDENCE UNAVAILABLE';
  }
}

function metricEntries(value, prefix = '') {
  if (!value || typeof value !== 'object') return [];
  if (Array.isArray(value)) return value.flatMap((v, i) => {
    if (v && typeof v === 'object' && ('label' in v || 'name' in v) && 'value' in v) return [[v.label || v.name, v.value + (v.unit ? ` ${v.unit}` : '')]];
    return metricEntries(v, String(i + 1));
  });
  return Object.entries(value).flatMap(([key, v]) => {
    const label = `${prefix ? prefix + ' · ' : ''}${key.replaceAll('_', ' ')}`;
    if (typeof v === 'number' || typeof v === 'string' || typeof v === 'boolean') return [[label, v]];
    return metricEntries(v, label);
  });
}
async function loadBenchmark() {
  const button = document.getElementById('refresh-benchmark');
  button.disabled = true;
  const metrics = document.getElementById('benchmark-metrics');
  const limits = document.getElementById('benchmark-limitations');
  metrics.replaceChildren(); limits.replaceChildren();
  try {
    const response = await fetch('/next-experiment/runs/benchmark/report.json');
    if (!response.ok) throw new Error('No completed report');
    const report = await response.json();
    if (!report.headline || !report.metrics) throw new Error('Incomplete report');
    if (report.status !== 'passed') {
      document.getElementById('benchmark-status').textContent = 'COMPARISON FAILED VALIDATION';
      document.getElementById('benchmark-headline').textContent = 'The comparison is not validated. No improvement is claimed.';
      for (const key of ['Decision mismatches', 'Reference mismatches']) {
        if (key in report.metrics) limits.append(element('li', `${key}: ${report.metrics[key]}`));
      }
      (report.limitations || []).forEach(text => limits.append(element('li', String(text))));
      return;
    }
    document.getElementById('benchmark-status').textContent = 'MEASURED · CHECKLIST COMPUTATION ONLY';
    document.getElementById('benchmark-headline').textContent = report.headline;
    const preferred = ['Gene-condition decisions', 'Decision mismatches', 'LOO work reduction percent', 'Checklist kernel speedup', 'Eager median seconds', 'Adaptive median seconds'];
    const displayMetrics = preferred.every(k => k in report.metrics) ? preferred.map(k => [k, report.metrics[k]]) : metricEntries(report.metrics).slice(0, 9);
    const friendly = {'Gene-condition decisions': 'Gene–condition decisions', 'Decision mismatches': 'Changed pass/fail decisions', 'LOO work reduction percent': 'Fewer guide-omission recomputations', 'Checklist kernel speedup': 'Faster checklist computation', 'Eager median seconds': 'Eager checklist · median seconds', 'Adaptive median seconds': 'Early-stop checklist · median seconds'};
    displayMetrics.forEach(([label, value]) => {
      const item = element('div', undefined, 'metric');
      let display = typeof value === 'number' && !Number.isInteger(value) ? Number(value.toFixed(4)) : value;
      if (label === 'LOO work reduction percent') display += '%';
      if (label === 'Checklist kernel speedup') display = Number(value).toFixed(2) + '×';
      if (label === 'Gene-condition decisions') display = Number(value).toLocaleString('en-US');
      item.append(element('strong', String(display)), element('span', friendly[label] || label)); metrics.append(item);
    });
    (report.limitations || []).forEach(text => limits.append(element('li', String(text))));
    if ('Shared setup seconds (excluded)' in report.metrics) limits.append(element('li', `Shared setup: ${report.metrics['Shared setup seconds (excluded)']} seconds, excluded from both kernel timings. Timings are medians of five paired runs.`));
  } catch (error) {
    document.getElementById('benchmark-status').textContent = 'COMPARISON NOT AVAILABLE';
    document.getElementById('benchmark-headline').textContent = 'No completed comparison is loaded.';
    limits.append(element('li', 'This page makes no performance improvement claim until the measured report is available.'));
  } finally { button.disabled = false; }
}
document.getElementById('refresh-benchmark').addEventListener('click', loadBenchmark);
loadEvidence(); loadBenchmark();
