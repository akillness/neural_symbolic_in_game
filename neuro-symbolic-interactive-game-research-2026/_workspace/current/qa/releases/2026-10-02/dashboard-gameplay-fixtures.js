/* UI-only fixtures. Runs inside an unpatched dashboard page with a synthetic
 * same-origin emitter, never against canonical gameplay. Not human-study data. */
(async () => {
  const dash = window.__traceDashboard;
  const $ = (id) => document.getElementById(id);
  const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const fixtures = [], guards = [];
  const check = (name, passed, detail) => fixtures.push({ fixture: name, passed: Boolean(passed), ...(detail === undefined ? {} : { detail }) });
  const families = ['POLICY', 'PRECONDITION', 'REACHABILITY', 'KNOWLEDGE', 'DISCLOSURE', 'QUEST STAGE'];
  const codes = { OBJECT_NOT_PRESENT: 'REACHABILITY', MISSING_REQUIRED_OBJECT: 'PRECONDITION', OBJECT_NOT_REACHABLE: 'REACHABILITY', FORBIDDEN_DISCLOSURE: 'DISCLOSURE', STAGE_GATED_DISCLOSURE: 'DISCLOSURE/QUEST STAGE' };
  const hash = (n) => String(n).padStart(2, '0').repeat(32);
  const summary = (n, stage = 0, commits = 0, holds = 0) => ({ state_sha256: hash(n), revision: n, stage, fact_count: 2 + stage, commit_count: commits, refusal_count: holds });
  const trace = (checks, skipped = []) => {
    const family_states = Object.fromEntries(families.map((f) => [f, 'out_of_scope']));
    for (const code of skipped) for (const f of codes[code].split('/')) family_states[f] = 'skipped';
    for (const [code, outcome] of checks) for (const f of codes[code].split('/')) if (outcome === 'fail' || family_states[f] !== 'fail') family_states[f] = outcome;
    return { checks: checks.map(([code, outcome]) => ({ code, gate: codes[code], outcome })), evaluated_gates: [...new Set(checks.map(([c]) => codes[c]))], held_at: checks.find(([, r]) => r === 'fail')?.[0] || '', short_circuit: checks.some(([, r]) => r === 'fail'), skipped: skipped.map((code) => ({ code, gate: codes[code] })), out_of_scope: families.filter((f) => family_states[f] === 'out_of_scope'), family_states };
  };
  const frame = $('game');
  const loaded = new Promise((resolve) => frame.addEventListener('load', resolve, { once: true }));
  frame.srcdoc = '<!doctype html><script>window.emit=e=>parent.postMessage(e,"*")</script><body>fixture emitter</body>';
  await loaded;
  let seq = 200;
  const envelope = (kind, payload) => ({ channel: 'trace-rpg-dashboard', engineering_only: true, seq: ++seq, kind, t_ms: 1000 + seq * 10, payload });
  const send = async (kind, payload) => {
    const beforeTick = dash.lastTick, e = envelope(kind, payload);
    frame.contentWindow.emit(e);
    const accepted = () => kind === 'tick' ? dash.lastTick !== beforeTick : dash.events.some((event) => event.seq === e.seq && event.kind === kind);
    for (let i = 0; i < 100 && !accepted(); i++) await pause(10);
    if (!accepted()) throw new Error(`Rejected authorized fixture ${kind} #${e.seq}`);
    return e;
  };
  const actionText = () => [$('action-outcome').textContent, $('action-next').textContent, $('action-checks').textContent, $('action-trace-state').textContent].join('\n');
  const commit = (n, stage = 1) => ({ operation: 'acquire_object', labels: ['Signal lens acquired'], stage_from: 0, stage_to: stage, state_sha256_before: hash(n - 1), trace: trace([['OBJECT_NOT_PRESENT', 'pass']]), ...summary(n, stage, n, 0) });
  const hold = (n = 1) => ({ operation: 'install_lens', codes: ['MISSING_REQUIRED_OBJECT'], gates: ['PRECONDITION'], next_affordance: 'Recover the signal lens from the lamp store.', state_sha256_before: hash(n), trace: trace([['MISSING_REQUIRED_OBJECT', 'fail']], ['OBJECT_NOT_PRESENT', 'OBJECT_NOT_REACHABLE']), ...summary(n, 1, 1, 1) });

  check('engineering details collapsed by default', !document.querySelector('details.engineering').open);
  check('page boot has no invented verdict', /no action|waiting/i.test($('action-outcome').textContent) && $('action-checks').children.length === 0);
  await send('session', { scenario_id: 'fixture-only', sites: [], ...summary(0) });
  check('quest is actual three-stage case, not pictured five-stage fiction', $('quest-steps').children.length === 3 && !/lamp room|stairs|tide log|stage.*5/i.test($('quest-steps').textContent), $('quest-steps').textContent);
  check('first objective matches the actual Mira-first presentation', /Mira/.test($('quest-objective').textContent));
  await send('dialogue', { npc: 'captain_mira', phase: 'open' });
  check('Mira dialogue changes only the displayed objective', /collect.*lens/i.test($('quest-objective').textContent) && dash.lastSummary.stage === 0);
  await send('commit', commit(1));
  check('committed result names real operation and verdict', /commit/i.test(actionText()) && /acquire|lens/i.test($('action-meta').textContent), actionText());
  const stable = actionText();
  for (let i = 0; i < 25; i++) { await send('tick', { x: i / 10, z: 2, yaw: 0, focus: '', moving: true, ...summary(1, 1, 1) }); }
  await send('focus', { interaction_id: 'mira' });
  check('movement focus and ticks do not replace completed verdict', actionText() === stable);

  $('freeze-readout').click();
  const pinned = actionText();
  await send('hold', hold(1));
  check('freeze readout keeps selected action stable', actionText() === pinned && $('freeze-readout').getAttribute('aria-pressed') === 'true');
  check('game counters keep updating while readout is pinned', $('kpi-holds').textContent === '1' && !$('follow-latest').hidden);
  check('newer actions are explicit while pinned', /1/.test($('newer-actions').textContent), $('newer-actions').textContent);
  $('follow-latest').click();
  check('follow latest returns to real hold and clears pin', /hold|held/i.test(actionText()) && /MISSING_REQUIRED_OBJECT/.test(actionText()) && $('freeze-readout').getAttribute('aria-pressed') === 'false', actionText());
  const checkWords = $('action-checks').textContent;
  check('ordered checks keep failed and skipped states separate', /fail/i.test(checkWords) && /skipped/i.test(checkWords) && checkWords.indexOf('MISSING_REQUIRED_OBJECT') < checkWords.indexOf('OBJECT_NOT_PRESENT'), checkWords);
  check('hold advice uses actual lens affordance, no fictional stairs', /lens/i.test($('action-next').textContent) && !/stairs|lamp room|floor 3|penalty/i.test($('action-next').textContent), $('action-next').textContent);
  const historyButtons = $('action-history').querySelectorAll('button');
  check('verdict history remains explicitly selectable', historyButtons.length === 2);
  historyButtons[historyButtons.length - 1].click();
  check('historical selection pauses the readout only', $('freeze-readout').getAttribute('aria-pressed') === 'true' && !$('follow-latest').hidden);
  $('follow-latest').click();

  await send('commit', { ...commit(2, 2), stage_from: 1, operation: 'install_object', ...summary(2, 2, 2, 1) });
  check('stage two agrees with its committed transition', /2/.test($('quest-stage-label').textContent) && /1 → 2/.test($('action-outcome').textContent));
  await send('commit', { ...commit(3, 3), stage_from: 2, operation: 'inspect_fact', ...summary(3, 3, 3, 1) });
  check('committed stage three does not invent a fourth commit', /3/.test($('quest-stage-label').textContent) && $('quest-steps').children.length === 3 && $('kpi-commits').textContent === '3', $('quest-stage-label').textContent);
  check('stage three agrees with its committed transition', /2 → 3/.test($('action-outcome').textContent));
  await send('episode_complete', { ...summary(3, 3, 3, 1), holds_by_gate: {} });
  check('episode result is explicit without changing action history', /complete/i.test($('kpi-episode').textContent) && $('action-history').querySelectorAll('button').length === 4);
  await send('hold', { operation: 'inspect_fact', codes: ['FORBIDDEN_DISCLOSURE'], gates: ['DISCLOSURE'], next_affordance: 'Use public evidence only.', ...summary(3, 3, 3, 2) });
  check('legacy envelope does not fabricate evaluated checks', /legacy|schema.only/i.test(actionText()) && $('action-checks').children.length === 0, actionText());

  const beforeUnknown = dash.familyEval.REACHABILITY.passed;
  const unknownOutcome = { ...commit(4, 3), stage_from: 3 };
  unknownOutcome.trace.checks[0].outcome = 'unreported';
  await send('commit', unknownOutcome);
  check('unknown check outcome is missing, never a fabricated pass', $('action-checks').querySelector('[data-state="missing"]') && !$('action-checks').querySelector('[data-state="pass"]'));
  check('unknown check does not inflate evaluated-pass counters', dash.familyEval.REACHABILITY.passed === beforeUnknown);
  check('unknown check cannot mark its family graph or commit edge as passed', dash.familyState.REACHABILITY === 'missing' && $('nebula').querySelector('[data-edge="REACHABILITY>commit"]').getAttribute('data-kind') === 'schema');
  await send('session', { scenario_id: 'fixture-missing-stage', sites: [], ...summary(0), stage: null });
  check('missing quest stage is not silently converted to zero', $('quest-steps').children.length === 0 && /waiting/i.test($('quest-stage-label').textContent));
  await send('session', { scenario_id: 'fixture-restart', sites: [], ...summary(0) });
  check('new session clears prior readout and history', $('action-history').querySelectorAll('button').length === 0 && /no action|waiting/i.test($('action-outcome').textContent) && $('freeze-readout').getAttribute('aria-pressed') === 'false', actionText());
  check('new session clears stale counts and episode', $('kpi-commits').textContent === '0' && $('kpi-holds').textContent === '0' && !/complete/i.test($('kpi-episode').textContent));
  for (let i = 1; i <= 130; i++) await send('commit', commit(i));
  const bounded = $('action-history').querySelectorAll('button').length;
  check('high-rate action history is bounded and keeps latest', bounded > 0 && bounded <= 12 && $('kpi-commits').textContent === '130' && $('freeze-readout').getAttribute('aria-pressed') === 'false' && /commit/i.test(actionText()), { history_count: bounded, latest: $('action-meta').textContent });
  check('recent-action rail remains compact', $('recent-actions').children.length > 0 && $('recent-actions').children.length <= 3, $('recent-actions').children.length);

  $('freeze-readout').click();
  const pinnedId = dash.selectedVerdictId, pinnedText = actionText();
  for (let i = 131; i <= 150; i++) await send('commit', commit(i));
  check('pinned result survives bounded-history eviction', dash.selectedVerdictId === pinnedId && dash.readoutFrozen && actionText() === pinnedText && $('action-meta').textContent.includes('verdict #130 '));
  check('newer counter includes every result after the pin', /20/.test($('newer-actions').textContent) && $('action-history').children.length <= 12);
  $('follow-latest').click();
  check('follow latest recovers after history eviction', !dash.readoutFrozen && dash.selectedVerdictId === 150);
  const before = dash.events.length;
  const bad = envelope('commit', commit(999));
  window.dispatchEvent(new MessageEvent('message', { source: frame.contentWindow, origin: 'https://foreign.invalid', data: bad }));
  await pause(30);
  guards.push({ guard: 'right frame but wrong origin rejected', passed: dash.events.length === before });
  window.postMessage(bad, '*');
  await pause(30);
  guards.push({ guard: 'wrong window with matching channel rejected', passed: dash.events.length === before });
  frame.contentWindow.emit({ ...bad, channel: 'foreign-channel' });
  await pause(30);
  guards.push({ guard: 'game frame foreign channel rejected', passed: dash.events.length === before });

  const iframeHeight = Math.round(frame.getBoundingClientRect().height);
  check('real-game iframe keeps established 720px height', iframeHeight === 720, iframeHeight);
  check('desktop has no page horizontal overflow', document.documentElement.scrollWidth <= window.innerWidth, { width: window.innerWidth, scroll_width: document.documentElement.scrollWidth });
  check('page review buttons have text and native keyboard semantics', $('freeze-readout').tagName === 'BUTTON' && $('follow-latest').tagName === 'BUTTON' && $('freeze-readout').textContent.trim().length > 0);
  return { fixtures, guards, passed: fixtures.every((x) => x.passed) && guards.every((x) => x.passed), engineering_only: true, reduced_motion: dash.reducedMotion, boundary: 'Synthetic renderer fixtures only. No gameplay, human readability or efficacy result.' };
})();
