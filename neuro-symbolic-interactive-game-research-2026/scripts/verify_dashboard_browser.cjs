#!/usr/bin/env node
'use strict';

// Engineering renderer fixtures in a clean, unpatched browser. This driver does
// not perform a human study and never claims model/player efficacy. Playwright
// must already be available; no dependency installation is performed here.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const base = process.argv[2] || 'http://localhost:8788/dashboard/';
const out = path.resolve(process.argv[3] || path.join(process.env.TMPDIR || '/tmp', 'dashboard-browser-qa'));
const oldFixture = path.join(root, '_workspace/current/qa/releases/2026-09-18/dashboard-trace-fixtures.js');
const gameplayFixture = path.join(root, '_workspace/current/qa/releases/2026-10-02/dashboard-gameplay-fixtures.js');
fs.mkdirSync(out, { recursive: true });

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROME_BINARY || undefined,
    args: ['--enable-unsafe-swiftshader', '--use-angle=swiftshader'],
  });
  const report = {
    base,
    captured_at: new Date().toISOString(),
    browser: browser.version(),
    runtime: { node: process.version, platform: process.platform, architecture: process.arch, headless: true, init_scripts: 0, stealth_patches: 0 },
    source_sha256: Object.fromEntries(['game-track/web/dashboard/index.html', 'game-track/web/dashboard/dashboard.css', 'game-track/web/dashboard/dashboard.js', '_workspace/current/qa/releases/2026-09-18/dashboard-trace-fixtures.js', '_workspace/current/qa/releases/2026-10-02/dashboard-gameplay-fixtures.js'].map((file) => [file, crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex')])),
    boundary: 'Engineering-only synthetic renderer regression. Not real gameplay, usability, fun, G4/G6, or model/player efficacy evidence.',
    runs: [],
  };
  try {
    for (const motion of ['no-preference', 'reduce']) {
      for (const [name, file] of [['evaluation-trace', oldFixture], ['gameplay-readability', gameplayFixture]]) {
        if (!fs.existsSync(file)) {
          if (name === 'gameplay-readability') continue;
          throw new Error(`Missing fixture: ${file}`);
        }
        const context = await browser.newContext({ viewport: { width: 1440, height: 1100 }, reducedMotion: motion });
        const page = await context.newPage();
        const consoleErrors = [], pageErrors = [];
        page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
        page.on('pageerror', (err) => pageErrors.push(String(err)));
        // The fixture explicitly replaces the game with a same-origin emitter.
        // Avoid downloading/running an irrelevant 50MB Web export for that mock.
        await page.route('**/public/index.html', (route) => route.fulfill({ contentType: 'text/html', body: '<!doctype html><body>renderer fixture only</body>' }));
        await page.goto(base, { waitUntil: 'domcontentloaded' });
        await page.waitForFunction(() => Boolean(window.__traceDashboard));
        const result = await page.evaluate(fs.readFileSync(file, 'utf8'));
        const expectedFamily = name === 'evaluation-trace' ? 'KNOWLEDGE' : 'REACHABILITY';
        const expectedMissingStateErrors = consoleErrors.filter((x) => x.startsWith('dashboard trace:') && x.includes('missing') && x.includes(expectedFamily));
        const unexpectedConsoleErrors = consoleErrors.filter((x) => !expectedMissingStateErrors.includes(x));
        const run = {
          name, reduced_motion: motion, result, console_errors: consoleErrors,
          expected_missing_state_errors: expectedMissingStateErrors,
          unexpected_console_errors: unexpectedConsoleErrors, page_errors: pageErrors,
          passed: result.passed && pageErrors.length === 0 && unexpectedConsoleErrors.length === 0,
        };
        // Each fixture deliberately sends exactly one malformed trace. All
        // other console errors remain failures.
        run.passed = run.passed && expectedMissingStateErrors.length === 1;
        if (name === 'gameplay-readability') {
          run.layout = [];
          for (const width of [1440, 768, 390, 320]) {
            await page.setViewportSize({ width, height: 1100 });
            const layout = await page.evaluate(() => ({ width: innerWidth, scroll_width: document.documentElement.scrollWidth, iframe_height: document.getElementById('game').getBoundingClientRect().height, buttons: [...document.querySelectorAll('#freeze-readout,#follow-latest')].filter((b) => !b.hidden).map((b) => ({ text: b.textContent.trim(), width: b.getBoundingClientRect().width, height: b.getBoundingClientRect().height })) }));
            layout.passed = layout.scroll_width <= width && Math.round(layout.iframe_height) === 720 && layout.buttons.every((b) => b.width > 0 && b.height > 0);
            run.layout.push(layout);
          }
          await page.setViewportSize({ width: 1440, height: 1100 });
          const freeze = page.locator('#freeze-readout');
          await freeze.focus();
          await page.keyboard.press('Space');
          const keyboardFreeze = await freeze.getAttribute('aria-pressed') === 'true';
          await page.locator('#follow-latest').focus();
          await page.keyboard.press('Enter');
          run.keyboard = { space_freezes: keyboardFreeze, enter_follows_latest: await freeze.getAttribute('aria-pressed') === 'false' };
          await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
          const zoomLayout = await page.evaluate(() => ({ width: innerWidth, scroll_width: document.documentElement.scrollWidth, freeze_visible: document.getElementById('freeze-readout').getBoundingClientRect().width > 0 }));
          run.zoom_200_percent = { ...zoomLayout, method: 'CSS root zoom=2 (layout simulation, not human readability measurement)', passed: zoomLayout.scroll_width <= zoomLayout.width && zoomLayout.freeze_visible };
          run.passed = run.passed && run.layout.every((x) => x.passed) && run.keyboard.space_freezes && run.keyboard.enter_follows_latest && run.zoom_200_percent.passed;
        }
        report.runs.push(run);
        await context.close();
      }
    }
    report.passed = report.runs.length === 4 && report.runs.every((x) => x.passed);
    report.counts = {
      runs: report.runs.length,
      fixtures: report.runs.reduce((n, x) => n + (x.result.fixtures || []).length, 0),
      fixture_failures: report.runs.reduce((n, x) => n + (x.result.fixtures || []).filter((f) => !f.passed).length, 0),
      guard_failures: report.runs.reduce((n, x) => n + (x.result.guards || []).filter((g) => !g.passed).length, 0),
    };
    fs.writeFileSync(path.join(out, 'dashboard-browser-fixtures.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify({ passed: report.passed, counts: report.counts, runs: report.runs.map((r) => ({ name: r.name, motion: r.reduced_motion, passed: r.passed, failures: (r.result.fixtures || []).filter((f) => !f.passed), unexpected_console_errors: r.unexpected_console_errors, page_errors: r.page_errors })), receipt: path.join(out, 'dashboard-browser-fixtures.json') }, null, 2));
    if (!report.passed) process.exitCode = 1;
  } catch (err) {
    report.passed = false;
    report.driver_error = String(err && err.stack || err);
    fs.writeFileSync(path.join(out, 'dashboard-browser-fixtures.json'), JSON.stringify(report, null, 2) + '\n');
    throw err;
  } finally {
    await browser.close();
  }
})().catch((err) => { console.error(err); process.exitCode = 1; });
