#!/usr/bin/env node
'use strict';

// Operator QA: one real browser session, not an efficacy experiment. Only the
// public dashboard observer is read; all game actions are native input.
// node actual-game-driver.cjs --playwright <module> --chromium <executable> --out <new-directory>
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { setTimeout: holdDuration } = require('node:timers/promises');
const { execFileSync } = require('node:child_process');
const args = process.argv.slice(2);
function option(name, fallback) {
  const index = args.indexOf(`--${name}`);
  return index < 0 ? fallback : args[index + 1];
}
function point(name, fallback) {
  const value = option(name, process.env[name.toUpperCase().replaceAll('-', '_')]);
  if (!value) return fallback;
  const parsed = value.split(',').map(Number);
  assert.ok(parsed.length === 2 && parsed.every(Number.isFinite), `--${name} requires x,y`);
  return parsed;
}
const config = {
  playwright: option('playwright', process.env.PLAYWRIGHT_MODULE || 'playwright'),
  chromium: option('chromium', process.env.CHROMIUM_EXECUTABLE),
  url: option('url', process.env.GAME_URL || 'http://127.0.0.1:8886/dashboard/'),
  out: path.resolve(option('out', process.env.ACCEPTANCE_OUTPUT || `actual-game-${new Date().toISOString().replace(/[:.]/g, '-')}`)),
  // Original route PNGs were 2880x1800 at a 1440x900 CSS viewport (DPR 2).
  // DPR affects Godot's responsive canvas layout, not merely PNG resolution.
  deviceScaleFactor: Number(option('dpr', process.env.GAME_DPR || '2')),
  headless: option('headless', process.env.GAME_HEADLESS || 'false') === 'true',
  // Original visible-control coordinates at 1440x900, expressed in CSS pixels.
  begin: point('begin', [481, 565]), startCase: point('start-case', [835, 790]), coach: point('coach', [884, 370]),
};
const contractPath = path.join(__dirname, 'contract.json');
const contractBytes = fs.readFileSync(contractPath);
const contract = JSON.parse(contractBytes);
fs.mkdirSync(config.out, { recursive: false }); // Never overwrite an earlier attempt.
fs.copyFileSync(__filename, path.join(config.out, 'executed-driver.cjs'));
const diagnostics = { console: [], pageerror: [], requestfailed: [], httpErrors: [], driverFailures: [], warnings: [], focus: [] };
const result = {
  case_id: contract.case_id, status: 'NOT_PASS', started_at: new Date().toISOString(),
  scope: 'n=1 operator development QA; unchanged game; no human or efficacy claim',
  contract_sha256: crypto.createHash('sha256').update(contractBytes).digest('hex'),
  argv: process.argv, config, continuous_capture_since_before_navigation: false,
  driver_sha256: crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex'),
  attempt_note: option('note', null),
  interaction_boundary: { genuine_keyboard_mouse_only: true, public_observer_reads_only: true, init_scripts: false, fixtures: false, private_godot_calls: false, source_changes: false },
  steps: [], gates: {}, failures: [], diagnostics,
};
let browser, page, serial = 0;
function write(name, value) {
  const target = path.join(config.out, name);
  fs.writeFileSync(`${target}.tmp`, `${JSON.stringify(value, null, 2)}\n`);
  fs.renameSync(`${target}.tmp`, target);
}
function persist() { write('diagnostics.json', diagnostics); write('actual-game-acceptance.json', result); }
function errorRecord(error) { return { name: error.name, message: error.message, stack: error.stack }; }
function fail(error, context) {
  const item = { at: new Date().toISOString(), context, ...errorRecord(error) };
  result.failures.push(item); diagnostics.driverFailures.push(item); persist();
}
async function observe() {
  return page.evaluate(() => {
    const s = window.__traceDashboard;
    if (!s) return null;
    return JSON.parse(JSON.stringify({ session: s.session, connected: s.connected,
      tick: s.lastTick, summary: s.lastSummary, counts: s.counts, events: s.events,
      disclosureEvents: s.disclosureEvents, comparison: s.comparison,
      readoutFrozen: s.readoutFrozen, pinnedVerdict: s.pinnedVerdict,
      traceErrors: s.traceErrors, legacyEvents: s.legacyEvents,
      comparisonText: document.querySelector('.frozen-comparison')?.innerText }));
  });
}
async function snapshot(label, image = true) {
  const id = `${String(++serial).padStart(3, '0')}-${label}`;
  const state = await observe();
  write(`${id}.json`, state);
  if (image) {
    await page.screenshot({ path: path.join(config.out, `${id}.png`), fullPage: false });
    const canvas = page.frameLocator('#game').locator('canvas');
    if (await canvas.count()) await canvas.screenshot({ path: path.join(config.out, `${id}-canvas.png`), timeout: 15000 });
  }
  result.steps.push({ id, at: new Date().toISOString(), state: `${id}.json`, image: image ? `${id}.png` : null });
  persist(); return state;
}
async function waitFor(fn, arg, timeout = 15000) {
  // Playwright's second positional argument is the function argument, NOT options.
  const handle = await page.waitForFunction(fn, arg, { timeout });
  await handle.dispose();
}
async function tickAfter(timestamp) {
  await waitFor(t => window.__traceDashboard?.lastTickAt > t, timestamp, 10000);
}
async function recordFocus(label) {
  const states = [];
  for (const frame of page.frames()) states.push(await frame.evaluate(() => ({
    url: location.href, hasFocus: document.hasFocus(), visibilityState: document.visibilityState,
    isConnected: document.documentElement.isConnected, activeElement: document.activeElement?.tagName,
    canvasConnected: document.querySelector('canvas')?.isConnected ?? null,
    pointerLockElement: document.pointerLockElement?.tagName ?? null,
    userActivation: { isActive: navigator.userActivation.isActive, hasBeenActive: navigator.userActivation.hasBeenActive },
  })));
  const front = process.platform === 'darwin' && !config.headless
    ? execFileSync('/usr/bin/lsappinfo', ['front'], { encoding: 'utf8' }).trim() : null;
  const nativeFront = front ? execFileSync('/usr/bin/lsappinfo', ['info', '-only', 'name,pid', front], { encoding: 'utf8' }).trim() : null;
  diagnostics.focus.push({ label, at: new Date().toISOString(), nativeFront, states }); persist();
}
async function focusGame(label) {
  await recordFocus(`${label}-before-focus`);
  if (process.platform === 'darwin' && !config.headless) {
    // Bundle-name activation can select an older Chrome instance. Activate the
    // exact process obtained from the browser's read-only CDP process observer.
    const script = `ObjC.import('AppKit'); const app = $.NSRunningApplication.runningApplicationWithProcessIdentifier(${result.browser_pid}); app.activateWithOptions(2); JSON.stringify({frontPID: Number($.NSWorkspace.sharedWorkspace.frontmostApplication.processIdentifier)});`;
    let activation;
    for (let attempt = 0; attempt < 10; attempt++) {
      activation = JSON.parse(execFileSync('/usr/bin/osascript', ['-l', 'JavaScript', '-e', script], { encoding: 'utf8' }));
      if (activation.frontPID === result.browser_pid) break;
    }
    assert.equal(activation.frontPID, result.browser_pid, 'Exact browser process must be natively frontmost before input');
  }
  await page.bringToFront();
  await page.frameLocator('#game').locator('canvas').focus();
  await recordFocus(`${label}-after-focus`);
}
async function press(key, label) {
  const before = await observe();
  await focusGame(label);
  await page.keyboard.press(key, { delay: 120 });
  await tickAfter(await page.evaluate(() => window.__traceDashboard.lastTickAt));
  const after = await snapshot(label);
  write(`${String(serial).padStart(3, '0')}-input.json`, { key, before, after });
  return after;
}
async function visibleClick(label, point) {
  await snapshot(`${label}-visible-before`);
  await focusGame(label);
  await recordFocus(`${label}-before-click`);
  await page.mouse.click(point[0], point[1]);
  await recordFocus(`${label}-after-click`);
  await tickAfter(await page.evaluate(() => window.__traceDashboard.lastTickAt));
  return snapshot(`${label}-clicked`);
}
async function coaches(label) {
  // Public lifecycle receipts establish when the visible [OK] control exists.
  // Never click a vanished card: dismissal recaptures the pointer, so another
  // blind mouse move would rotate the real camera instead of clicking UI.
  for (let i = 0; i < 4; i++) {
    const state = await observe();
    const coach = state.events.filter(event => event.kind === 'coach_card').at(-1);
    if (coach?.payload.phase !== 'shown') return;
    await visibleClick(`${label}-coach-${i + 1}`, config.coach);
    await waitFor(seq => {
      const events = window.__traceDashboard.events.filter(event => event.kind === 'coach_card');
      return events.at(-1)?.seq > seq;
    }, coach.seq);
  }
  assert.notEqual((await observe()).events.filter(event => event.kind === 'coach_card').at(-1)?.payload.phase,
    'shown', 'All queued visible coach cards must be dismissed before movement');
}
async function walk(x, z, label) {
  await focusGame(label);
  let stalls = 0;
  for (let step = 0; step < 140; step++) {
    const before = await observe();
    assert.equal(before.tick.tutorial_open, false, 'Tutorial must be visibly closed before movement');
    assert.equal(before.tick.dialogue_open, false, 'Dialogue must be closed before movement');
    const dx = x - before.tick.x, dz = z - before.tick.z;
    if (Math.hypot(dx, dz) < 0.48) return snapshot(`${label}-arrived`);
    assert.ok(Math.abs(before.tick.yaw) < 0.03, 'Route requires original yaw; never silently counteract mouse-look');
    const alongX = Math.abs(dx) > Math.abs(dz);
    const delta = alongX ? dx : dz;
    const key = alongX ? (delta > 0 ? 'KeyD' : 'KeyA') : (delta > 0 ? 'KeyS' : 'KeyW');
    const ms = Math.max(70, Math.min(320, Math.abs(delta) / 3.3 * 850));
    await page.keyboard.down(key);
    try { await holdDuration(ms); } finally { await page.keyboard.up(key); }
    await tickAfter(await page.evaluate(() => window.__traceDashboard.lastTickAt));
    const after = await observe();
    write(`walk-${label}-${String(step).padStart(3, '0')}.json`, { key, hold_ms: ms, target: { x, z }, before: before.tick, after: after.tick });
    if (Math.hypot(after.tick.x - before.tick.x, after.tick.z - before.tick.z) < 0.03) stalls++; else stalls = 0;
    if (stalls >= 4) {
      await snapshot(`${label}-stalled`);
      throw new Error(`Real movement stalled at ${after.tick.x},${after.tick.z}; target ${x},${z}`);
    }
  }
  throw new Error(`Route exhausted at ${label}`);
}
function latest(s) { return s.disclosureEvents.at(-1)?.explanation; }
async function chooseOutcome(key, outcome, label) {
  const before = await observe();
  await press(key, `${label}-input`);
  await waitFor(({ count, outcome }) => {
    const events = window.__traceDashboard?.disclosureEvents || [];
    return events.length > count && events.at(-1)?.explanation?.decision?.outcome === outcome;
  }, { count: before.disclosureEvents.length, outcome });
  const after = await snapshot(label);
  const e = latest(after);
  assert.equal(e.decision.outcome, outcome);
  assert.equal(e.checks.consistent, true);
  assert.match(e.effect.priorHash, /^[a-f0-9]{64}$/);
  assert.match(e.effect.nextHash, /^[a-f0-9]{64}$/);
  if (outcome === 'authorized_fresh') {
    assert.equal(e.effect.mutated, true); assert.notEqual(e.effect.priorHash, e.effect.nextHash);
  } else {
    assert.equal(e.effect.mutated, false); assert.equal(e.effect.priorHash, e.effect.nextHash);
  }
  if (outcome.startsWith('authorized')) {
    assert.equal(e.decision.accepted, true);
    assert.equal(e.checks.evaluated.length, 4);
    assert.ok(e.checks.evaluated.every(check => check.outcome === 'pass'));
    assert.equal(e.checks.skipped.length, 0); assert.equal(e.checks.unreported.length, 0);
  } else {
    assert.equal(e.decision.accepted, false);
    assert.ok(e.checks.evaluated.some(check => check.code === 'STAGE_GATED_DISCLOSURE' && check.outcome === 'fail'));
    assert.equal(after.tick.stage, 0);
  }
  result.gates[label] = { passed: true, explanation: e, receipt: result.steps.at(-1).state }; persist();
  return after;
}
function inspectionInvariant(s) {
  return { hash: s.tick.state_sha256, counts: s.counts, comparison: s.comparison,
    comparisonText: s.comparisonText, disclosureEventCount: s.disclosureEvents.length,
    eventCount: s.events.length, summary: s.summary, readoutFrozen: s.readoutFrozen, pinnedVerdict: s.pinnedVerdict };
}
async function inspectMap(width, baseline) {
  await page.setViewportSize({ width, height: 900 });
  const summary = page.locator('details.engineering > summary');
  await summary.scrollIntoViewIfNeeded();
  // A genuine mouse click establishes focus, then native Tab/Shift+Tab and
  // Enter prove keyboard reachability and native details activation.
  await summary.click();
  await page.keyboard.press('Tab', { delay: 120 }); await page.keyboard.press('Shift+Tab', { delay: 120 });
  assert.equal(await summary.evaluate(el => document.activeElement === el), true, 'Summary must be keyboard reachable');
  const wasOpen = await summary.evaluate(el => el.parentElement.open);
  await page.keyboard.press('Enter', { delay: 120 });
  assert.equal(await summary.evaluate(el => el.parentElement.open), !wasOpen);
  await page.keyboard.press('Enter', { delay: 120 });
  assert.equal(await summary.evaluate(el => el.parentElement.open), wasOpen);
  if (!wasOpen) await page.keyboard.press('Enter', { delay: 120 });
  await page.locator('#ontology-map-rows tr').first().waitFor({ state: 'visible' });
  const map = await page.evaluate(() => {
    const rows = [...document.querySelectorAll('#ontology-map-rows tr')];
    return { viewport: { width: innerWidth, height: innerHeight },
      document: { scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth },
      tableCount: document.querySelectorAll('.ontology-map table').length,
      roles: rows.map(row => ({ id: row.querySelector('[data-observed-role]')?.dataset.observedRole,
        heading: row.querySelector('th')?.innerText, declared: row.cells[1]?.innerText,
        frozen: row.cells[2]?.innerText, observed: row.cells[3]?.innerText,
        bilingual: !!row.querySelector('th [lang=en]') && !!row.querySelector('th [lang=ko]') })),
      lists: [...document.querySelectorAll('#ontology-map-rules section')].map(section => ({ heading: section.querySelector('h3').innerText, items: [...section.querySelectorAll('li')].map(li => li.innerText) })),
      boundary: document.querySelector('#ontology-map-boundary').innerText,
      source: document.querySelector('#ontology-map-source').innerText,
    };
  });
  assert.equal(map.viewport.width, width); assert.equal(map.tableCount, 1);
  assert.deepEqual(map.roles.map(row => row.id), contract.ontology_role_ids);
  assert.deepEqual(map.lists.map(list => list.items.length), [7, 6, 7]);
  assert.ok(map.roles.every(row => row.bilingual && row.declared && row.frozen));
  assert.ok(map.roles.some(row => /authorized_redisplay/.test(row.observed)), 'Observed map must reflect the actual redisplay');
  assert.ok(map.document.scrollWidth <= map.document.clientWidth, 'No horizontal document overflow');
  assert.match(map.boundary, /[Mm]issing.*unreported/);
  write(`map-${width}.json`, map);
  await page.locator('#ontology-map-title').scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(config.out, `map-${width}-heading.png`) });
  for (const role of contract.ontology_role_ids) {
    await page.locator(`[data-observed-role="${role}"]`).scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(config.out, `map-${width}-${role}.png`) });
  }
  for (let i = 0; i < 3; i++) {
    await page.locator('#ontology-map-rules section').nth(i).scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(config.out, `map-${width}-rules-${i + 1}.png`) });
  }
  const after = await snapshot(`map-${width}-after`, false);
  assert.deepEqual(inspectionInvariant(after), baseline, 'Inspection must not change hash/counts/events/frozen comparison/readout');
  result.gates[`map_${width}`] = { passed: true, keyboard_Enter: true, no_inspection_mutation: true, dom: `map-${width}.json`, screenshots: `map-${width}-*.png` }; persist();
}
async function run() {
  try {
    const { chromium } = require(config.playwright);
    browser = await chromium.launch({ executablePath: config.chromium, headless: config.headless });
    const browserObserver = await browser.newBrowserCDPSession();
    const processInfo = await browserObserver.send('SystemInfo.getProcessInfo');
    result.browser_pid = processInfo.processInfo.find(info => info.type === 'browser')?.id;
    assert.ok(Number.isInteger(result.browser_pid), 'Native activation requires the observed browser PID');
    await browserObserver.detach();
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: config.deviceScaleFactor });
    page = await context.newPage();
    const stamp = () => ({ at: new Date().toISOString(), url: page.url() });
    page.on('console', msg => {
      const entry = { ...stamp(), type: msg.type(), text: msg.text(), location: msg.location() };
      diagnostics.console.push(entry); if (msg.type() === 'warning') diagnostics.warnings.push(entry); persist();
    });
    page.on('pageerror', error => { diagnostics.pageerror.push({ ...stamp(), ...errorRecord(error) }); persist(); });
    page.on('requestfailed', request => { diagnostics.requestfailed.push({ ...stamp(), resource: request.url(), method: request.method(), failure: request.failure() }); persist(); });
    page.on('response', response => { if (response.status() >= 400) { diagnostics.httpErrors.push({ ...stamp(), resource: response.url(), status: response.status() }); persist(); } });
    result.continuous_capture_since_before_navigation = true; persist();
    await page.goto(config.url, { waitUntil: 'load', timeout: 120000 });
    await waitFor(() => !!window.__traceDashboard?.lastTick, null, 120000);
    await focusGame('loaded');
    await snapshot('loaded');
    await visibleClick('begin-investigation', config.begin);
    await waitFor(() => window.__traceDashboard?.lastTick?.tutorial_open === true, null, 20000);
    await visibleClick('start-case', config.startCase);
    await waitFor(() => window.__traceDashboard?.lastTick?.play_started === true && window.__traceDashboard.lastTick.tutorial_open === false, null);
    await walk(0, 9.4, 'mira-north'); await walk(3, 9.4, 'mira-approach');
    await waitFor(() => window.__traceDashboard.lastTick.focus === 'mira', null);
    await press('KeyE', 'open-mira-stage0');
    await waitFor(() => window.__traceDashboard.lastTick.dialogue_open, null);
    await chooseOutcome('Digit3', 'denied', 'stage_zero_denial'); await coaches('first-hold');
    await press('Escape', 'close-mira');
    await walk(0, 8.5, 'leave-mira'); await walk(0, 4.2, 'lens-north-strip');
    // Clear the hut's west wall in x before moving north: its +z face ends
    // at 3.625, with the player capsule extending the collision to about 3.98.
    await walk(-5, 4.2, 'lens-detour1'); await walk(-10.6, 4.3, 'lens-detour2');
    await walk(-10.6, 1, 'lens-approach');
    await waitFor(() => window.__traceDashboard.lastTick.focus === 'lens_pickup', null);
    await press('KeyE', 'collect-lens');
    await waitFor(() => window.__traceDashboard.lastTick.stage === 1, null);
    result.gates.lens_pickup = { passed: true, state: await snapshot('lens-stage1') }; persist();
    await coaches('first-commit');
    await walk(-10.6, 4.3, 'return-detour2');
    await walk(-5, 4.3, 'return-detour1'); await walk(0, 4.3, 'return-strip');
    await walk(0, 8.6, 'mount-north'); await walk(7.4, 8.6, 'mount-east'); await walk(7.4, 12.2, 'mount-approach');
    await waitFor(() => window.__traceDashboard.lastTick.focus === 'lamp_mount', null);
    await press('KeyE', 'install-lens'); await waitFor(() => window.__traceDashboard.lastTick.stage === 2, null);
    result.gates.mount_stage2 = { passed: true, state: await snapshot('mount-stage2') }; persist();
    await coaches('mount-coach');
    await walk(3, 11.6, 'return-mira');
    await waitFor(() => window.__traceDashboard.lastTick.focus === 'mira', null);
    await press('KeyE', 'open-mira-stage2'); await waitFor(() => window.__traceDashboard.lastTick.dialogue_open, null);
    await chooseOutcome('Digit3', 'authorized_fresh', 'fresh_disclosure');
    await chooseOutcome('Digit1', 'authorized_redisplay', 'authorized_redisplay');
    // Freeze using the visible dashboard button, then take the invariant baseline.
    await page.locator('#freeze-readout').click();
    const baseline = inspectionInvariant(await observe());
    assert.equal(baseline.readoutFrozen, true);
    await inspectMap(1440, baseline); await inspectMap(390, baseline);
    const finalState = await observe();
    assert.equal(finalState.traceErrors, 0); assert.equal(finalState.legacyEvents, 0);
    assert.equal(diagnostics.console.filter(item => item.type === 'error').length, 0, 'Console errors since before navigation');
    assert.equal(diagnostics.pageerror.length, 0, 'Page errors since before navigation');
    assert.equal(diagnostics.requestfailed.length, 0, 'Failed requests since before navigation');
    assert.equal(diagnostics.httpErrors.length, 0, 'HTTP errors since before navigation');
    result.gates.continuous_diagnostics = { passed: true, warnings: diagnostics.warnings.length };
    result.status = 'PASS';
  } catch (error) { fail(error, 'actual-game-route'); }
  finally {
    if (page && !page.isClosed()) {
      for (const key of ['KeyW', 'KeyA', 'KeyS', 'KeyD']) await page.keyboard.up(key).catch(error => fail(error, 'release-key'));
      try { result.final_state = await snapshot('final', true); } catch (error) { fail(error, 'final-snapshot'); }
    }
    if (browser) await browser.close().catch(error => fail(error, 'browser-close'));
    if (result.failures.length || diagnostics.pageerror.length || diagnostics.requestfailed.length || diagnostics.httpErrors.length || diagnostics.console.some(item => item.type === 'error')) result.status = 'NOT_PASS';
    result.finished_at = new Date().toISOString(); persist();
    console.log(JSON.stringify({ status: result.status, receipt: path.join(config.out, 'actual-game-acceptance.json'), failures: result.failures.map(item => item.message) }, null, 2));
    process.exitCode = result.status === 'PASS' ? 0 : 1;
  }
}
run().catch(error => { fail(error, 'driver-top-level'); result.finished_at = new Date().toISOString(); persist(); process.exitCode = 1; });
