/* One backend contract for source evidence, scenario awards and reports. */
'use strict';
const $ = id => document.getElementById(id);
const state = { token: '', applicants: [], result: null, evidence: null, sequence: 0, evidenceSequence: 0, toolSequence: 0, report: '' };
const dollars = n => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(n);
function node(tag, text, className) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; }
function error(message = '') { $('error').textContent = message; $('error').hidden = !message; }
async function api(path, body, method = 'POST') {
  const response = await fetch(path, { method: body === undefined ? 'GET' : method, cache: 'no-store',
    headers: { ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data));
  return data;
}
function parameters() {
  const weights = Object.fromEntries(['w_cascade', 'w_anchor', 'w_people', 'w_purity'].map(k => [k, Number($(k).value)]));
  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  if (!Number.isFinite(total) || total <= 0) throw new Error('At least one policy weight must be positive.');
  for (const k of Object.keys(weights)) weights[k] /= total;
  return { mode: $('mode').value, budget: Number($('budget').value), preferred_regime: $('regime').value, weights };
}
function setReport(text) { state.report = text || ''; $('report').textContent = state.report || 'No report returned.'; $('download-report').disabled = !state.report; }
function metric(value, label) { const el = node('div', undefined, 'metric'); el.append(node('strong', value), node('span', label)); return el; }
function renderQueue() {
  const scenario = $('mode').value === 'canonical';
  $('queue-title').textContent = scenario ? 'Illustrative scenario' : 'Registry location records';
  const head = node('tr');
  for (const h of scenario ? ['Applicant', 'Request', 'Proposed award', 'Decision'] : ['Registry location', 'Industry', 'Modeled reach', 'Intake']) head.append(node('th', h));
  $('queue-head').replaceChildren(head);
  const query = $('search').value.toLocaleLowerCase();
  const rows = scenario && state.result ? state.result.selected_portfolio.allocations : state.applicants;
  const fragment = document.createDocumentFragment();
  for (const app of rows.filter(a => `${a.name} ${a.address || ''}`.toLocaleLowerCase().includes(query))) {
    const tr = node('tr'); const name = node('td', app.name); name.append(node('small', app.address || app.id)); tr.append(name);
    const cells = scenario ? [dollars(app.requested_amount), dollars(app.award_amount || 0), app.tier || 'Run analysis'] : [app.industry_type || app.naics || '', String(app.reach_2hop ?? app.reach ?? app.exposed_businesses ?? '—'), app.intake?.status || 'MISSING'];
    for (const value of cells) tr.append(node('td', value));
    tr.addEventListener('click', () => { $('business-a').value = app.id; loadEvidence(); });
    fragment.append(tr);
  }
  $('queue-body').replaceChildren(fragment);
}
function selectors() {
  for (const id of ['business-a', 'business-b']) {
    const previous = $(id).value;
    $(id).replaceChildren(...state.applicants.map(a => { const option = node('option', `${a.name} · ${a.address || a.id}`); option.value = a.id; return option; }));
    if (state.applicants.some(a => a.id === previous)) $(id).value = previous;
  }
  if ($('business-b').value === $('business-a').value && state.applicants.length > 1) $('business-b').selectedIndex = 1;
}
async function analyze() {
  const seq = ++state.sequence; error();
  $('connection-status').textContent = 'Analyzing…'; $('run-analysis').disabled = true;
  state.result = null; state.evidence = null; ++state.evidenceSequence; ++state.toolSequence;
  $('evidence-form').reset(); $('review-form').reset(); $('evidence-fields').disabled = true; $('review-fields').disabled = true;
  $('evidence-history').textContent = ''; $('intake-status').textContent = 'Waiting for current analysis…';
  setReport(''); $('metrics').replaceChildren(); $('regime-comparison').replaceChildren();
  try {
    const result = await api('/api/agent/run', parameters());
    if (seq !== state.sequence) return;
    state.result = result.data;
    if (result.data.status === 'EVIDENCE_ONLY') {
      state.applicants = result.data.applicants;
      $('metrics').replaceChildren(metric(state.applicants.length, 'Registry records'), metric(state.applicants.filter(a => a.intake?.status === 'VERIFIED_INTAKE').length, 'Reviewed intakes'), metric('Unknown', 'Grant effectiveness'), metric('None', 'Awards computed'));
      setReport(result.data.report_markdown);
    } else {
      const apps = await api(`/api/corridor/applicants?mode=${encodeURIComponent($('mode').value)}`);
      if (seq !== state.sequence) return;
      state.applicants = apps.applicants;
      const p = result.data.selected_portfolio;
      $('metrics').replaceChildren(metric(dollars(p.total_disbursed), 'Modeled awards'), metric(p.funded_count, 'Scenario recipients'), metric(dollars(p.remaining_budget), 'Unallocated budget'), metric(p.direct_jobs_preserved, 'Associated scenario FTEs · not jobs saved'));
      setReport(result.data.red_team_compliance_report_markdown);
      const table = node('table'); const header = node('tr'); for (const h of ['Regime', 'Proposed awards', 'Recipients', 'Spatial audit']) header.append(node('th', h)); table.append(header);
      for (const p of Object.values(result.data.regimes_comparison.regimes)) { const row = node('tr'); for (const v of [p.regime, dollars(p.total_disbursed), p.funded_count, p.spatial_cluster_audit.all_clusters_compliant ? 'Pass (proxy)' : 'Review required']) row.append(node('td', v)); table.append(row); }
      $('regime-comparison').replaceChildren(table);
    }
    $('source-label').textContent = result.source;
    $('connection-status').textContent = 'Backend connected';
    $('evidence-notice').textContent = $('mode').value === 'canonical' ? 'Illustrative scenario: finances, jobs, supply links and grant effects are assumptions. Proposed awards are not approvals.' : 'Source evidence: supply links are modeled. Reviewed intake does not establish grant effectiveness. No awards are computed.';
    renderQueue(); selectors(); await loadEvidence();
  } catch (e) {
    if (seq === state.sequence) { error(e.message); $('connection-status').textContent = 'Analysis unavailable'; state.applicants = []; $('queue-body').replaceChildren(); $('business-a').replaceChildren(); $('business-b').replaceChildren(); }
  } finally { if (seq === state.sequence) $('run-analysis').disabled = false; }
}
async function loadEvidence() {
  const seq = ++state.evidenceSequence;
  state.evidence = null; $('evidence-form').reset(); $('review-fields').disabled = true;
  const sourceMode = $('mode').value === 'local_csv';
  $('evidence-form').hidden = !sourceMode; $('review-form').hidden = !sourceMode; $('evidence-history').hidden = !sourceMode;
  $('evidence-fields').disabled = !sourceMode;
  if (!sourceMode || !$('business-a').value) { $('evidence-fields').disabled = true; $('intake-status').textContent = 'Intake reviews use registry IDs in reviewed registry evidence mode.'; $('evidence-history').textContent = ''; return; }
  $('intake-status').textContent = 'Loading intake…';
  const bid = $('business-a').value;
  try {
    const evidence = await api(`/api/evidence/${encodeURIComponent(bid)}`);
    if (seq !== state.evidenceSequence) return;
    state.evidence = evidence;
    $('intake-status').textContent = `${evidence.status} · revision ${evidence.version}` + (evidence.assessment.financial_runway_quarters !== undefined ? ` · reviewed runway ${evidence.assessment.financial_runway_quarters} quarters` : '');
    const form = $('evidence-form');
    for (const [key, value] of Object.entries(evidence.submission || {})) { const input = form.elements.namedItem(key); if (!input) continue; if (input.type === 'checkbox') input.checked = value; else input.value = value ?? ''; }
    $('review-fields').disabled = evidence.status !== 'PENDING_REVIEW';
    $('evidence-history').textContent = JSON.stringify({ history: evidence.history, assessment: evidence.assessment }, null, 2);
  } catch (e) { if (seq === state.evidenceSequence) { error(e.message); $('evidence-fields').disabled = true; } }
}
$('analysis-form').addEventListener('submit', e => { e.preventDefault(); analyze(); });
$('access-form').addEventListener('submit', e => { e.preventDefault(); state.token = $('access-token').value; $('access-token').value = ''; analyze(); });
$('mode').addEventListener('change', () => { state.evidenceSequence++; $('tool-output').textContent = ''; $('trace-paths').replaceChildren(); analyze(); });
$('search').addEventListener('input', renderQueue);
$('business-a').addEventListener('change', loadEvidence);
$('tool-form').addEventListener('submit', async e => {
  e.preventDefault(); error(); const seq = ++state.toolSequence; $('tool-status').textContent = 'Executing backend tool…'; $('tool-output').textContent = ''; $('trace-paths').replaceChildren();
  try {
    const action = $('action').value;
    const body = { ...parameters(), action, business_ids: action === 'variety' ? [] : action === 'compare' ? [$('business-a').value, $('business-b').value] : [$('business-a').value], max_hops: Number($('max-hops').value), direction: $('direction').value, grant_amount: Number($('grant-amount').value) };
    const result = await api('/api/chat', body);
    if (seq !== state.toolSequence) return;
    $('tool-status').textContent = `${result.execution} · ${result.tool}`;
    $('tool-output').textContent = JSON.stringify(result.result, null, 2);
    if (Array.isArray(result.result)) {
      for (const trace of result.result) for (const endpoint of (trace.endpoints || []).slice(0, 12)) {
        const path = node('div', undefined, 'path'); path.append(node('strong', `Modeled exposure · ${endpoint.hop} hop(s)`));
        path.append(node('span', (endpoint.named_path || endpoint.path || []).map(n => typeof n === 'string' ? n : n.name).join(' → '))); $('trace-paths').append(path);
      }
    }
  } catch (e) { if (seq === state.toolSequence) { error(e.message); $('tool-status').textContent = 'Tool unavailable'; } }
});
$('evidence-form').addEventListener('submit', async e => {
  e.preventDefault(); error(); if (!state.evidence) return;
  const bid = $('business-a').value;
  const payload = { version: state.evidence.version };
  for (const input of $('evidence-form').elements) { if (!input.name) continue; payload[input.name] = input.type === 'checkbox' ? input.checked : input.type === 'number' ? (input.value === '' ? null : Number(input.value)) : input.value; }
  try { await api(`/api/evidence/${encodeURIComponent(bid)}`, payload, 'PUT'); await analyze(); } catch (e) { error(e.message); }
});
$('review-form').addEventListener('submit', async e => {
  e.preventDefault(); error(); if (!state.evidence) return;
  try { await api(`/api/evidence/${encodeURIComponent($('business-a').value)}/review`, { version: state.evidence.version, reviewer: $('reviewer').value, notes: $('review-notes').value, decision: $('review-decision').value }); await analyze(); } catch (e) { error(e.message); }
});
$('download-report').addEventListener('click', () => { const url = URL.createObjectURL(new Blob([state.report], { type: 'text/markdown;charset=utf-8' })); const link = node('a'); link.href = url; link.download = 'central-market-review.md'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); });
analyze();
