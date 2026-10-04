// Renders demo/panel.js in a minimal DOM mock against evidence JSON passed on stdin.
// Usage: node tests/panel_render_check.js < demo/evidence/panel.json
'use strict';
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const script = fs.readFileSync('demo/panel.js', 'utf8');
const optionalIds = ['built', 'data-state', 'interaction-note', 'selection-announcement', 'gene-takeaway', 'condition-label', 'agent-summary', 'evaluation-note', 'recorded-loop'];

class Element {
  constructor(tag, ownerDocument) { this.ownerDocument = ownerDocument; this.tag = tag; this.children = []; this.textContent = ''; this.listeners = {}; this.style = {}; this.attributes = {}; this.hidden = false; this.disabled = false; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  setAttribute(name, value) { this.attributes[name] = value; }
  focus(options) { this.ownerDocument.activeElement = this; this.focusOptions = options; }
  get text() { return this.textContent + this.children.map(c => c.text).join(' '); }
}
function startRender(panel, { condition = 'without_il6', goal = 'resolve_uncertainty', fetch, missingIds = [] } = {}) {
  const nodes = new Map();
  const document = { activeElement: null };
  nodes.document = document;
  const missing = new Set(missingIds);
  const byId = id => {
    if (missing.has(id)) return null;
    if (!nodes.has(id)) nodes.set(id, new Element('div', document));
    return nodes.get(id);
  };
  byId('condition').value = condition;
  byId('goal').value = goal;
  ['error', 'workspace', 'guide-details', 'agent-evaluation'].forEach(id => { byId(id).hidden = true; });
  document.getElementById = byId;
  document.createElement = tag => new Element(tag, document);
  const context = vm.createContext({
    document,
    fetch: fetch || (async () => ({ ok: true, json: async () => panel })),
    console,
  });
  vm.runInContext(script, context);
  return nodes;
}
async function settled(nodes) { await new Promise(resolve => setTimeout(resolve, 0)); return nodes; }
async function render(panel, options) { return settled(startRender(panel, options)); }
const clone = object => JSON.parse(JSON.stringify(object));
function fire(nodes, id, event = 'change') { assert.doesNotThrow(() => nodes.get(id).listeners[event](), `${id} event must not throw`); }
function clickGene(nodes, gene) {
  const button = nodes.get('genes').children.find(b => b.children[0].children[0].textContent.endsWith(`  ${gene}`));
  assert.ok(button, `${gene} must be in the shortlist`);
  button.focus();
  assert.doesNotThrow(() => button.listeners.click());
  const replacement = nodes.get('genes').children.find(b => b.attributes['aria-pressed'] === 'true');
  assert.notEqual(replacement, button, 'shortlist renders a replacement button');
  assert.equal(nodes.document.activeElement, replacement, 'gene activation keeps focus on the recreated selected button');
  assert.equal(replacement.focusOptions.preventScroll, true, 'preserving focus does not scroll the page');
}
function assertUnavailable(nodes) {
  assert.equal(nodes.get('error').hidden, false);
  assert.equal(nodes.get('workspace').hidden, true);
  assert.equal(nodes.get('agent-evaluation').hidden, true);
  assert.equal(nodes.get('recorded-loop').hidden, true, 'recorded example is hidden when evidence cannot load');
  assert.equal(nodes.get('genes').children.length, 0);
  assert.match(nodes.get('rule').textContent, /unavailable/i);
  assert.doesNotMatch(nodes.get('rule').textContent, /loading/i);
  assert.equal(nodes.get('data-state').textContent, 'Evidence unavailable');
  ['condition', 'goal', 'reveal'].forEach(id => {
    assert.equal(nodes.get(id).disabled, true, `${id} stays disabled after failure`);
    fire(nodes, id, id === 'reveal' ? 'click' : 'change');
  });
  assert.equal(nodes.get('workspace').hidden, true, 'events cannot expose invalid data');
  assert.equal(nodes.get('guide-details').hidden, true, 'reveal cannot expose invalid data');
}

(async () => {
  const panel = JSON.parse(fs.readFileSync(0, 'utf8'));
  let nodes = await render(panel);
  assert.equal(nodes.get('error').hidden, true, 'valid evidence must hide the error');
  assert.equal(nodes.document.activeElement, null, 'initial rendering does not steal focus');
  assert.equal(nodes.get('workspace').hidden, false);
  assert.equal(nodes.get('recorded-loop').hidden, false, 'recorded example appears after valid evidence loads');
  ['condition', 'goal', 'reveal'].forEach(id => assert.equal(nodes.get(id).disabled, false));
  assert.equal(nodes.get('data-state').textContent, 'Saved analysis');
  assert.equal(nodes.get('built').textContent, `Built ${new Date(panel.created_utc).toISOString().slice(0, 16).replace('T', ' at ')} UTC`);
  assert.match(nodes.get('interaction-note').textContent, /does not start a new calculation or model call/);
  assert.equal(nodes.get('candidate-count').textContent, `${panel.candidates.length} genes`);
  assert.equal(nodes.get('gene-name').textContent, 'UBA3');
  assert.equal(nodes.get('verdict').textContent, 'Resolve conflicting evidence');
  assert.match(nodes.get('gene-takeaway').textContent, /guides disagree/);
  assert.equal(nodes.get('condition-label').textContent, 'Without IL6 · saved screen condition');
  assert.match(nodes.get('decisive').textContent, /Guide 1 and Guide 5/);
  assert.match(nodes.get('dependence').textContent, /2-vs-1 guide split: Guide 2/);
  const probes = nodes.get('probes').children;
  assert.equal(probes.length, 2);
  assert.equal(probes[0].children[0].textContent, 'Hypothetical');
  assert.match(probes[0].text, /\+1 agreeing guide → Count signal survives checklist/);
  assert.match(probes[1].text, /\+1 null guide → Resolve conflicting evidence/);
  assert.equal(nodes.get('decision-rule-list').children.map(c => c.tag).join(''), 'dtdddtdddtdd');
  assert.match(nodes.get('source-methods').textContent, /two independent sgRNAs/);
  assert.match(nodes.get('evaluation-note').textContent, /calculation tool supplies/);
  assert.match(nodes.get('evaluation-note').textContent, /not been repeated with that correction/);
  assert.match(nodes.get('evaluation-results').children[1].text, /synthetic/);
  assert.match(nodes.get('evaluation-results').children[1].text, /Passes the fixed count checklist/);
  assert.match(nodes.get('agent-summary').textContent, /Tools supply the fixed-rule verdicts/);

  // Opening detail then changing condition preserves the gene and closes old detail.
  fire(nodes, 'reveal', 'click');
  assert.equal(nodes.get('guide-details').hidden, false);
  for (const condition of ['with_il6', 'without_il6']) {
    nodes.get('condition').value = condition;
    nodes.get('condition').focus();
    fire(nodes, 'condition');
    assert.equal(nodes.document.activeElement, nodes.get('condition'), 'condition change keeps focus on the select');
    assert.equal(nodes.get('gene-name').textContent, 'UBA3');
    assert.equal(nodes.get('score').textContent, Number(panel.candidates[0].conditions[condition].score).toFixed(2));
    assert.equal(nodes.get('guide-details').hidden, true);
    assert.equal(nodes.get('reveal').attributes['aria-expanded'], 'false');
    assert.match(nodes.get('selection-announcement').textContent, /Still showing UBA3/);
    assert.match(nodes.get('selection-announcement').textContent, /IL6/, 'condition announcements preserve IL6 capitalization');
    const selected = nodes.get('genes').children.filter(b => b.attributes['aria-pressed'] === 'true');
    assert.equal(selected.length, 1);
    assert.match(selected[0].text, /UBA3/);
  }
  nodes.get('goal').value = 'count_support';
  nodes.get('goal').focus();
  fire(nodes, 'goal');
  assert.equal(nodes.document.activeElement, nodes.get('goal'), 'priority change keeps focus on the select');
  assert.equal(nodes.get('gene-name').textContent, panel.rankings.without_il6.count_support[0]);
  assert.match(nodes.get('selection-announcement').textContent, /Priority changed.*first ranked gene/);

  // Every candidate renders the matching saved fields under both priorities/conditions.
  for (const condition of ['without_il6', 'with_il6']) {
    nodes.get('condition').value = condition;
    fire(nodes, 'condition');
    for (const goal of ['resolve_uncertainty', 'count_support']) {
      nodes.get('goal').value = goal;
      fire(nodes, 'goal');
      for (const c of panel.candidates) {
        clickGene(nodes, c.gene);
        assert.equal(nodes.get('gene-name').textContent, c.gene);
        assert.equal(nodes.get('verdict').textContent, c.next_experiments[condition].status);
        assert.equal(nodes.get('score').textContent, Number(c.conditions[condition].score).toFixed(2).replace('-', '−'));
        assert.equal(nodes.get('question').textContent, c.next_experiments[condition].question);
        assert.equal(nodes.get('design').textContent, c.next_experiments[condition].design);
        assert.equal(nodes.get('change').textContent, c.next_experiments[condition].decision_change);
        assert.equal(nodes.get('guide-chart').children.length, c.guides.length);
        if (c.gene === 'SAMM50') assert.match(nodes.get('decisive').textContent, /2 more eligible guides needed/);
        if (c.gene === 'TP53') assert.match(nodes.get('decisive').textContent, /No single guide is decisive/);
      }
    }
  }

  // Absent optional evidence never renders undefined or invents measurements.
  const stripped = clone(panel);
  delete stripped.created_utc;
  delete stripped.input_hashes;
  stripped.candidates.forEach(c => {
    delete c.decision_dependence;
    delete c.external_context.evidence.published_screen_statistics;
    delete c.external_context.evidence.essentiality;
    delete c.external_context.evidence.essentiality_limit;
    Object.values(c.conditions).forEach(s => { delete s.repeat_scores; delete s.leave_one_out; });
  });
  nodes = await render(stripped);
  assert.equal(nodes.get('error').hidden, true);
  assert.equal(nodes.get('probes').children.length, 0);
  assert.match(nodes.get('dependence').textContent, /not available/);
  assert.equal(nodes.get('decision-rule-list').children.length, 6, 'biological rules survive missing count-dependence evidence');
  assert.match(nodes.get('published').textContent, /unavailable/);
  assert.match(nodes.get('hash').textContent, /unavailable/);
  assert.match(nodes.get('built').textContent, /unavailable/);
  assert.match(nodes.get('essentiality').textContent, /unknown does not mean non-essential/);
  assert.ok([...nodes.values()].every(e => !/undefined|NaN/.test(e.text)), 'optional omissions cannot leak undefined or NaN');
  const partialStats = clone(panel);
  delete partialStats.candidates[0].external_context.evidence.published_screen_statistics['IL6m|FDR'];
  partialStats.created_utc = 'invalid timestamp';
  nodes = await render(partialStats);
  assert.equal(nodes.get('error').hidden, true);
  assert.match(nodes.get('published').textContent, /incomplete/);
  assert.match(nodes.get('built').textContent, /unavailable/);
  // Added descriptive nodes are optional to keep older embedding surfaces working.
  nodes = await render(panel, { missingIds: optionalIds });
  assert.equal(nodes.get('error').hidden, true);

  // No controls can act while fetch/validation is still pending.
  let resolveFetch;
  nodes = startRender(panel, { fetch: () => new Promise(resolve => { resolveFetch = resolve; }) });
  ['goal', 'condition', 'reveal'].forEach(id => {
    assert.equal(nodes.get(id).disabled, true);
    fire(nodes, id, id === 'reveal' ? 'click' : 'change');
  });
  assert.equal(nodes.get('data-state').textContent, 'Loading saved analysis');
  assert.equal(nodes.get('recorded-loop').hidden, true, 'recorded example stays hidden while evidence is loading');
  resolveFetch({ ok: true, json: async () => panel });
  await settled(nodes);
  assert.equal(nodes.get('workspace').hidden, false);
  assert.equal(nodes.get('condition').disabled, false);
  assert.equal(nodes.get('recorded-loop').hidden, false, 'validated evidence reveals the recorded example');

  // Failed fetch and incomplete required structures fail closed, including later events.
  for (const fetch of [async () => { throw Error('network failed'); }, async () => ({ ok: false }), async () => ({ ok: true, json: async () => { throw Error('invalid JSON'); } })]) {
    assertUnavailable(await render(panel, { fetch }));
  }
  const invalidCases = [{ status: 'failed' }, { status: 'computed', candidates: [{}] }];
  for (const mutate of [
    p => delete p.rankings.with_il6,
    p => p.rankings.without_il6.count_support.push('UNKNOWN'),
    p => p.rankings.without_il6.count_support[1] = p.rankings.without_il6.count_support[0],
    p => delete p.candidates[0].conditions.with_il6,
    p => delete p.candidates[0].next_experiments.with_il6,
    p => p.candidates[0].guides[0].centered_log2_enrichment[0] = null,
    p => p.candidates[0].conditions.without_il6.score = 'not a number',
    p => p.candidates[0].external_context.evidence.source_url = 'javascript:alert(1)',
  ]) {
    const invalid = clone(panel);
    mutate(invalid);
    invalidCases.push(invalid);
  }
  for (const invalid of invalidCases) assertUnavailable(await render(invalid));
  console.log('panel render checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
