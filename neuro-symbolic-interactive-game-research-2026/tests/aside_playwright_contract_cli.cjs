"use strict";

// Cloud SDK CONTRACT, not native Aside certification. Executes the unchanged
// generated worker against real, fresh Chromium DOM/CSP/HTTP, never a user profile.
const fs = require("node:fs");
const { randomUUID } = require("node:crypto");

async function main() {
  if (process.env.NSG_ASIDE_TEST_TRANSPORT !== "playwright")
    throw new Error("explicit Playwright contract transport required");
  if (process.env.NSG_ASIDE_PROFILE)
    throw new Error("native profiles are forbidden in cloud SDK contract transport");
  const source = fs.readFileSync(0, "utf8");
  const { chromium } = require("playwright");
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}),
  });
  const logs = [];
  let error = null;
  try {
    const context = await browser.newContext();
    const ids = new WeakMap();
    const targetId = page => {
      if (!ids.has(page)) ids.set(page, randomUUID().replaceAll("-", ""));
      return ids.get(page);
    };
    const listBrowserTabs = async () => context.pages().map(page => ({
      targetId: targetId(page), url: page.url(),
    }));
    const openTab = async url => {
      const page = await context.newPage();
      Object.defineProperty(page, "targetId", { value: targetId(page) });
      await page.goto(url);
      return page;
    };
    const closeTab = async page => { await page.close(); };
    const snapshot = async page => ({ tree: await page.locator("body").ariaSnapshot() });
    const consoleFixture = { log: value => logs.push(String(value)) };
    const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
    await new AsyncFunction("listBrowserTabs", "openTab", "closeTab", "snapshot", "console", source)(
      listBrowserTabs, openTab, closeTab, snapshot, consoleFixture,
    );
  } catch (caught) {
    error = String(caught);
  } finally {
    await browser.close();
  }
  process.stdout.write(JSON.stringify({ run: { error, content: [{ type: "text", text: logs.join("\n") }] } }));
  if (error) process.exitCode = 1;
}
main().catch(() => {
  // Never publish paths, page contents, browser metadata or external exceptions.
  process.stderr.write("Cloud SDK contract transport failed\n");
  process.exitCode = 1;
});
