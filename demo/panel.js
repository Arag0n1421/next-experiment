'use strict';
let panel = null, selected;
const $ = id => document.getElementById(id);
const conditions = ['without_il6', 'with_il6'];
const goals = ['resolve_uncertainty', 'count_support'];
const conditionNames = { without_il6: 'Without IL6', with_il6: 'With IL6' };
const fmt = n => n == null || !Number.isFinite(n) ? '—' : Number(n).toFixed(2).replace('-', '−');
const hasText = value => typeof value === 'string' && value.trim().length > 0;
const numberOrNull = value => value === null || Number.isFinite(value);
const textList = value => Array.isArray(value) && value.every(hasText);
function write(id, value) { const e = $(id); if (e) e.textContent = value; }
function node(tag, text, cls) {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (cls) e.className = cls;
  return e;
}
function setControls(disabled) {
  ['goal', 'condition', 'reveal'].forEach(id => { $(id).disabled = disabled; });
}
function requireEvidence(valid) { if (!valid) throw Error('Incomplete or invalid saved evidence'); }
function validatePanel(data) {
  requireEvidence(data && data.status === 'computed' && Array.isArray(data.candidates) && data.candidates.length > 0);
  requireEvidence(hasText(data.panel_selection) && textList(data.limitations));
  const genes = data.candidates.map(c => c && c.gene);
  requireEvidence(genes.every(hasText) && new Set(genes).size === genes.length);
  goals.forEach(goal => requireEvidence(data.ranking_rules && hasText(data.ranking_rules[goal])));
  conditions.forEach(condition => goals.forEach(goal => {
    const order = data.rankings && data.rankings[condition] && data.rankings[condition][goal];
    requireEvidence(Array.isArray(order) && order.length === genes.length && new Set(order).size === genes.length && order.every(g => genes.includes(g)));
  }));
  data.candidates.forEach(c => {
    requireEvidence(Number.isInteger(c.total_guides) && c.total_guides > 0 && Number.isInteger(c.eligible_guides) && c.eligible_guides >= 0 && c.eligible_guides <= c.total_guides);
    requireEvidence(Array.isArray(c.guides) && c.guides.length === c.total_guides && c.guides.every(g => g && hasText(g.sgRNA) && typeof g.eligible === 'boolean' && Array.isArray(g.centered_log2_enrichment) && g.centered_log2_enrichment.length === 4 && g.centered_log2_enrichment.every(Number.isFinite)));
    requireEvidence(c.guides.filter(g => g.eligible).length === c.eligible_guides);
    const context = c.external_context && c.external_context.evidence;
    requireEvidence(context && hasText(context.label) && hasText(context.published_context) && typeof context.source_url === 'string' && /^https?:\/\/[^\s]+$/i.test(context.source_url));
    conditions.forEach(condition => {
      const s = c.conditions && c.conditions[condition], next = c.next_experiments && c.next_experiments[condition];
      requireEvidence(s && s.status === 'computed' && numberOrNull(s.score));
      if (s.repeat_scores != null) requireEvidence(Array.isArray(s.repeat_scores) && s.repeat_scores.length === 2 && s.repeat_scores.every(Number.isFinite));
      if (s.leave_one_out != null) requireEvidence(numberOrNull(s.leave_one_out.score_min) && numberOrNull(s.leave_one_out.score_max));
      requireEvidence(next && ['status', 'title', 'question', 'design', 'decision_change'].every(k => hasText(next[k])) && textList(next.readouts));
      const d = c.decision_dependence && c.decision_dependence[condition];
      if (d != null) {
        requireEvidence(Number.isInteger(d.coverage_shortfall) && d.coverage_shortfall >= 0 && textList(d.decisive_guides) && textList(d.failing_criteria) && hasText(d.summary) && Array.isArray(d.hypothetical_probes));
        requireEvidence(d.hypothetical_probes.every(p => p && ['add_one_concordant_guide', 'add_one_null_guide'].includes(p.probe) && hasText(p.status) && hasText(p.meaning) && typeof p.status_changes === 'boolean'));
      }
    });
  });
  return data;
}
function showList(reset = false) {
  if (!panel) return;
  const condition = $('condition').value, goal = $('goal').value;
  const order = panel.rankings[condition] && panel.rankings[condition][goal];
  if (!order) return;
  if (reset || !order.includes(selected)) selected = order[0];
  $('rule').textContent = panel.ranking_rules[goal];
  $('genes').replaceChildren();
  let selectedButton;
  order.forEach((gene, index) => {
    const c = panel.candidates.find(x => x.gene === gene), s = c.conditions[condition];
    const b = node('button', undefined, 'gene');
    b.type = 'button';
    b.setAttribute('aria-pressed', String(gene === selected));
    const top = node('span', undefined, 'gene-top');
    top.append(node('span', `${String(index + 1).padStart(2, '0')}  ${gene}`), node('span', fmt(s.score), 'gene-score'));
    b.append(top, node('span', c.external_context.evidence.label, 'gene-sub'), node('span', c.next_experiments[condition].status, 'gene-flag'));
    b.addEventListener('click', () => {
      selected = gene;
      const currentButton = showList();
      // Rebuilding the shortlist replaces this button; retain keyboard focus on its replacement.
      if (currentButton) currentButton.focus({ preventScroll: true });
      announce(`Showing ${selected}, ${conditionNames[$('condition').value]}.`);
    });
    $('genes').append(b);
    if (gene === selected) selectedButton = b;
  });
  showGene();
  return selectedButton;
}
function announce(message) { write('selection-announcement', message); }
function takeaway(status) {
  const meanings = {
    'Resolve conflicting evidence': 'The guides disagree: check that independent measurements reproduce the effect before advancing this gene.',
    'Insufficient guide coverage': 'Too few guides pass our starting-count filter for a confident count-based assessment; this is not a negative biological finding.',
    'Published cell-identity concern': 'The count signal is strong, but the source paper reports a cell-identity concern: assess identity before treating this as a useful intervention.',
    'Count signal survives checklist': 'The count signal passes our fixed checks; it still needs biological follow-up before any aging benefit can be claimed.',
    'Needs stronger support': 'The count signal fails at least one fixed check: collect stronger evidence before advancing this gene.'
  };
  return meanings[status] || 'Review the measured counts, source context, and proposed follow-up before deciding whether to advance this gene.';
}
function showGene() {
  const c = panel.candidates.find(x => x.gene === selected), condition = $('condition').value;
  const s = c.conditions[condition], context = c.external_context.evidence, next = c.next_experiments[condition];
  $('target-kind').textContent = context.label;
  $('gene-name').textContent = c.gene;
  $('verdict').textContent = next.status;
  write('gene-takeaway', takeaway(next.status));
  write('condition-label', `${conditionNames[condition]} · saved screen condition`);
  $('question').textContent = next.question;
  $('score').textContent = fmt(s.score);
  $('coverage').textContent = `${c.eligible_guides} / ${c.total_guides}`;
  $('repeats').textContent = s.repeat_scores ? s.repeat_scores.map(fmt).join(' / ') : 'Not available';
  const loo = s.leave_one_out;
  $('check-summary').textContent = loo && loo.score_min != null && loo.score_max != null
    ? `Leaving one guide out moves the estimate from ${fmt(loo.score_min)} to ${fmt(loo.score_max)}.`
    : 'Too few eligible guides, or no saved analysis, to measure leave-one-out sensitivity.';
  $('guide-details').hidden = true;
  $('reveal').setAttribute('aria-expanded', 'false');
  $('reveal').textContent = 'Inspect the guides ↓';
  $('guide-chart').replaceChildren();
  const cols = condition === 'without_il6' ? [0, 1] : [2, 3];
  const values = c.guides.map(g => (g.centered_log2_enrichment[cols[0]] + g.centered_log2_enrichment[cols[1]]) / 2);
  const scale = Math.max(1, ...values.map(Math.abs));
  c.guides.forEach((g, i) => {
    const row = node('div', undefined, 'guide-row' + (g.eligible ? '' : ' excluded'));
    const label = node('span', `Guide ${i + 1}${g.eligible ? '' : ' *'}`);
    label.title = g.sgRNA;
    const track = node('div', undefined, 'guide-track'), bar = node('div', undefined, 'guide-bar' + (values[i] < 0 ? ' negative' : ''));
    const width = Math.abs(values[i]) / scale * 48;
    bar.style.width = `${width}%`;
    bar.style.left = `${values[i] < 0 ? 50 - width : 50}%`;
    track.append(bar);
    row.append(label, track, node('span', fmt(values[i])));
    $('guide-chart').append(row);
  });
  $('loo').textContent = '* Excluded by the fixed starting-count filter. All guides remain visible. Guide effects average the two observed repeats; the aggregate is their eligible-guide median.';
  $('biology').textContent = context.published_context;
  const essentialityLimit = hasText(context.essentiality_limit) ? context.essentiality_limit : 'External fitness context is unavailable; unknown does not mean non-essential.';
  $('essentiality').textContent = context.essentiality && typeof context.essentiality.isEssential === 'boolean'
    ? `External fitness evidence: ${context.essentiality.isEssential ? 'flagged essential' : 'not flagged essential'} in DepMap. ${essentialityLimit}`
    : essentialityLimit;
  const stats = context.published_screen_statistics, prefix = condition === 'without_il6' ? 'IL6m' : 'IL6p';
  const beta = stats && stats[prefix + '|beta'], fdr = stats && stats[prefix + '|FDR'];
  $('published').textContent = Number.isFinite(beta) && Number.isFinite(fdr)
    ? `Published supplement: beta ${beta}; reported FDR ${fdr}.`
    : 'Published gene-level statistics are incomplete or unavailable for this condition.';
  $('paper-link').href = context.source_url;
  $('next-title').textContent = next.title;
  $('design').textContent = next.design;
  $('readouts').replaceChildren(...next.readouts.map(x => node('span', x)));
  $('change').textContent = next.decision_change;
  showDependence(c, condition, next);
}
function guideLabel(c, sgRNA) { const i = c.guides.findIndex(g => g.sgRNA === sgRNA); return i < 0 ? sgRNA : `Guide ${i + 1}`; }
function showDependence(c, condition, next) {
  const d = c.decision_dependence && c.decision_dependence[condition];
  $('decisive').textContent = '';
  $('dependence').textContent = '';
  $('probes').replaceChildren();
  $('decision-rule-list').replaceChildren();
  $('source-methods').textContent = '';
  // The proposed biological decision rule remains useful when count-dependence data is absent.
  const rule = next.decision_rule || {};
  [['Retain if', rule.retain], ['Reject if', rule.reject], ['More evidence if', rule.more_evidence]].forEach(([k, v]) => {
    if (hasText(v)) $('decision-rule-list').append(node('dt', k), node('dd', v));
  });
  $('source-methods').textContent = hasText(next.source_methods) ? next.source_methods : 'No source-method summary saved for this proposal.';
  if (!d) { $('dependence').textContent = 'Decision-dependence analysis not available for this gene.'; return; }
  if (d.coverage_shortfall > 0) $('decisive').textContent = `${d.coverage_shortfall} more eligible guide${d.coverage_shortfall === 1 ? '' : 's'} needed before the count rule can give a verdict.`;
  else if (d.decisive_guides.length) $('decisive').textContent = `The aggregate depends on ${d.decisive_guides.map(g => guideLabel(c, g)).join(' and ')}: omitting any listed guide moves it across the 0.5 log₂ threshold.`;
  else if (d.failing_criteria.length) $('decisive').textContent = `No single guide is decisive; the verdict fails on: ${d.failing_criteria.map(x => x.replace(/_/g, ' ')).join(', ')}.`;
  else $('decisive').textContent = 'No single guide is decisive: omitting any one guide leaves the aggregate above threshold.';
  $('dependence').textContent = d.summary.split('Rule probes (hypothetical, not observed):')[0].trim().replace(/[A-Za-z0-9.-]+_[+-]_\d+/g, m => guideLabel(c, m));
  d.hypothetical_probes.forEach(p => {
    const chip = node('span', undefined, 'probe' + (p.status_changes ? ' changes' : ''));
    chip.append(node('b', 'Hypothetical'), node('span', `${p.probe === 'add_one_concordant_guide' ? '+1 agreeing guide' : '+1 null guide'} → ${p.status}`));
    chip.title = p.meaning;
    $('probes').append(chip);
  });
}
function showEvaluation() {
  const evaluation = panel.agent_evaluation;
  $('agent-evaluation').hidden = true;
  const labels = { fragile: 'Fragile count evidence', supported: 'Passes the fixed count checklist', insufficient: 'Insufficient count evidence' };
  if (!evaluation || evaluation.status !== 'completed' || !Array.isArray(evaluation.rows) || !evaluation.rows.length || !evaluation.rows.every(r => r && hasText(r.label) && r.count_assessment && labels[r.count_assessment.status])) {
    write('agent-summary', 'No complete recorded agent evaluation is available in this saved build.');
    return;
  }
  $('agent-evaluation').hidden = false;
  $('evaluation-results').replaceChildren(...evaluation.rows.map(r => {
    const row = node('div', undefined, 'evaluation-row');
    row.append(node('span', `${r.label}${r.synthetic ? ' (synthetic)' : ''}`), node('strong', labels[r.count_assessment.status]));
    return row;
  }));
  write('agent-summary', `${evaluation.rows.length} saved agent investigations. Tools supply the fixed-rule verdicts. ${evaluation.rows.map(r => `${r.label}: ${labels[r.count_assessment.status].toLowerCase()}`).join('. ')}.`);
  write('evaluation-note', 'The calculation tool supplies the fixed-rule labels; these runs check how agents use that evidence. A curator description was misattributed as a published finding in one run. The source labels were clarified afterward; these recorded runs have not been repeated with that correction.');
  $('evaluation-limit').textContent = 'One development case, one run per variant. This checks response to evidence; it does not establish general reliability or a biological discovery. Two earlier fixture launches were stopped by the source-file guard; their failures are included in the record.';
}
$('goal').addEventListener('change', () => {
  if (!panel) return;
  showList(true);
  announce(`Priority changed. Showing the first ranked gene, ${selected}, ${conditionNames[$('condition').value]}.`);
});
$('condition').addEventListener('change', () => {
  if (!panel) return;
  showList();
  announce(`Condition changed to ${conditionNames[$('condition').value]}. Still showing ${selected}.`);
});
$('reveal').addEventListener('click', () => {
  if (!panel) return;
  const open = $('guide-details').hidden;
  $('guide-details').hidden = !open;
  $('reveal').setAttribute('aria-expanded', String(open));
  $('reveal').textContent = open ? 'Hide guide details ↑' : 'Inspect the guides ↓';
});
setControls(true);
if ($('recorded-loop')) $('recorded-loop').hidden = true;
write('data-state', 'Loading saved analysis');
(async () => {
  try {
    const r = await fetch('/evidence/panel.json');
    if (!r.ok) throw Error('Saved evidence could not be loaded');
    const data = validatePanel(await r.json());
    panel = data;
    $('candidate-count').textContent = `${panel.candidates.length} genes`;
    $('selection').textContent = panel.panel_selection;
    $('limits').textContent = panel.limitations.join(' ');
    const hash = panel.input_hashes && panel.input_hashes['countmatrix.xlsx'];
    $('hash').textContent = hasText(hash) ? `Count matrix SHA256: ${hash}` : 'Count matrix hash unavailable in this saved record.';
    const created = typeof panel.created_utc === 'string' ? Date.parse(panel.created_utc) : NaN;
    write('built', Number.isFinite(created) ? `Built ${new Date(created).toISOString().slice(0, 16).replace('T', ' at ')} UTC` : 'Build time unavailable in this saved record');
    write('data-state', 'Saved analysis');
    write('interaction-note', 'These controls explore recorded results. Changing a goal or condition does not start a new calculation or model call.');
    $('error').hidden = true;
    $('workspace').hidden = false;
    showList(true);
    showEvaluation();
    if ($('recorded-loop')) $('recorded-loop').hidden = false;
    setControls(false);
  } catch (e) {
    panel = null;
    selected = undefined;
    setControls(true);
    $('rule').textContent = 'Saved evidence unavailable. Reload after rebuilding or restoring the evidence file.';
    write('data-state', 'Evidence unavailable');
    write('built', 'No saved analysis loaded');
    write('interaction-note', 'The saved evidence could not be validated. Controls are disabled until a valid record loads.');
    announce('Saved evidence unavailable. Gene controls are disabled.');
    $('error').hidden = false;
    $('workspace').hidden = true;
    $('agent-evaluation').hidden = true;
    if ($('recorded-loop')) $('recorded-loop').hidden = true;
    $('genes').replaceChildren();
  }
})();
