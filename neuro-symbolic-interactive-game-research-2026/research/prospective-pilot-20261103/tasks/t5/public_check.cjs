const assert = require("node:assert/strict");
module.exports.check = async function(page, send) {
  let n = 0;
  for (const [accepted, expected] of [[null, "unknown"], [false, "false"]]) {
    const explanation = {
      schema_id: "trace-rpg-semantic-explanation", schema_version: "1.0.0",
      input: {}, ontology: {}, checks: {}, state_effect: {}, engine: {},
      decision: {outcome: "denied", accepted, result_codes: []}
    };
    await send({channel: "trace-rpg-dashboard", kind: "disclosure_outcome", payload: {explanation}});
    n += 1;
    await page.waitForFunction(count => document.querySelectorAll("#disclosure-events .disclosure-event").length === count, n);
    const detail = page.locator("#semantic-explanation .semantic-step").filter({has: page.locator("h3", {hasText: /^Decision$/})}).locator(".semantic-detail");
    assert.equal((await detail.textContent()).trim(), `accepted: ${expected} · codes: none reported`);
  }
};
