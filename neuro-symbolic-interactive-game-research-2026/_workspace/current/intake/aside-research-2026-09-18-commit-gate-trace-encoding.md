# Aside deep-research intake — commit-gate per-node evaluation trace (2026-09-18, D-073)

Status: design basis only ([INFERENCE]); advice, not evidence. Produced by an Aside browser-research session on 2026-09-18 for the D-073 dashboard trace work. Sources were opened by the Aside agent; retrieval date 2026-09-18.

# Encoding Evaluated / Not-Evaluated State in the TRACE-RPG Commit Gate

**Scope:** provenance + trace-visualization precedent, constraint-validation explanation precedent, and concrete UI recommendations for a 640×400 SVG pipeline graph.
**All retrieval dates: 2026-09-18.** Sources not successfully opened are listed in §6 under "Attempted, not retrieved" and are not cited as evidence.

---

## 1 Findings

### 1A. Provenance and trace-visualization standards

**F1. PROV-DM separates a *plan* from the *activity record*, which is exactly the distinction behind the "paper pipeline diagram" relabel.**
URL: https://www.w3.org/TR/prov-dm/ (retrieved 2026-09-18)
PROV-DM defines: "A plan is an entity that represents a set of actions or steps intended by one or more agents to achieve some goals." A plan is attached to an activity through `wasAssociatedWith(id; a, ag, pl, attrs)`. <citation refs="s5GkA1z7pYRHjbE_h0TKV">A plan is an entity that represents a set of actions or steps intended by one or more agents to achieve some goals.</citation>
**Implication:** the current six-family graph is a `prov:Plan` (intended steps). The new per-proposal trace is the `prov:Activity` record (what happened). PROV treats these as different entity types on purpose. Rendering them in the same visual container without differentiating them is the root cause of the misread, and the fix is to let the *plan* be the layout while the *activity* supplies every node's state.

**F2. OpenTelemetry's span status is a deliberate three-value vocabulary, and OTel itself flags the default as counter-intuitive. This is a cautionary precedent, not a model to copy.**
URLs: https://opentelemetry.io/docs/specs/otel/trace/api/ and https://opentelemetry.io/docs/concepts/signals/traces/ (both retrieved 2026-09-18)
The spec defines `StatusCode` as `Unset` ("The default status"), `Ok` ("The operation has been validated by an Application developer or Operator to have completed successfully"), and `Error`, with the total order `Ok > Error > Unset`, and instructs that "Instrumentation Libraries SHOULD leave the status code as `Unset` unless there is an error." <citation refs="1y47ShXgeAdxQp2pxmh7G">Generally, Instrumentation Libraries SHOULD NOT set the status code to Ok, unless explicitly configured to do so. Instrumentation Libraries SHOULD leave the status code as Unset unless there is an error</citation>
The concepts page then states: "`Unset` represents a span that completed without an error. `Ok` represents when a developer explicitly marks a span as successful," and openly calls this "unintuitive." <citation refs="DWpjZczfRpTAFJqQ5yDNy">Although this is unintuitive, it's not required to set a span status as Ok when a span is known to have completed without error, as this is covered by Unset.</citation>
**Implication:** OTel's default state is *semantically* "no judgement recorded" but is *documented and read* as "fine." That is precisely the failure mode TRACE-RPG must avoid. **Do not make the default/unset node state readable as success.** Make "no state supplied" a loud rendering error instead (see F10).

**F3. Waterfall trace UIs (Jaeger, Zipkin) are evidence-only: they contain rows for work that happened and have no vocabulary for work that did not.**
URLs: https://zipkin.io/pages/data_model and https://opentelemetry.io/docs/concepts/signals/traces/ (retrieved 2026-09-18)
A Zipkin trace is literally a JSON array of spans, each with `traceId`, `id`, `parentId`, `timestamp`, `duration`. There is no element type representing a step that was skipped or not applicable. OTel similarly defines a span as "a unit of work or operation." <citation refs="hZK54I0ygN4SNttAgA0tu">"traceId": "5982fe77008310cc80f1da5e10147517", "name": "get", "id": "bd7a977555f6b982", "timestamp": 1458702548467000, "duration": 386000</citation>
**Implication:** waterfall UIs get honesty for free because *absence renders as absence*. A fixed-topology SVG graph has the opposite default: every node is always drawn, so absence must be *explicitly encoded*. This is the single structural difference that makes the TRACE-RPG card riskier than a Jaeger waterfall, and it is why a trace strip (§3.5) that only lists what ran is a valuable complement to the graph.

**F4. Langfuse keeps severity on a separate axis from existence.**
URLs: https://langfuse.com/docs/observability/data-model and https://langfuse.com/docs/observability/features/log-levels (retrieved 2026-09-18)
Observations are "the individual steps of your application," and each carries a `level` of `DEBUG`, `DEFAULT`, `WARNING`, or `ERROR` plus an optional `statusMessage` "to provide additional context." The trace UI can filter observations by log level. <citation refs="xcyO-jiAsM12N1LzM5qDd">You can differentiate the importance of observations with the level attribute to control the verbosity of your traces and highlight errors and warnings. Available levels: DEBUG, DEFAULT, WARNING, ERROR.</citation>
**Implication:** an observation exists because code ran; `level` then grades it. Two axes, not one. TRACE-RPG should likewise separate *did this check run* from *what was the verdict*, and carry a free-text reason string alongside the enum (see F8, F12).

**F5. LangSmith distinguishes the tree-shaped trace from a flattened projection, and documents when each is appropriate.**
URL: https://docs.langchain.com/langsmith/observability-concepts (retrieved 2026-09-18)
A *run* is "a single unit of work executed by an agent"; a *trace* is "a collection of runs for a single operation"; a *trajectory* is "a flat, ordered list of messages that shows the path an agent took from start to finish," described explicitly as "a projection over the traces." LangSmith gives a "reach for it when" table: trace for "debugging why one operation failed," trajectory for reading "what was exchanged in the session, without the execution detail." <citation refs="LULB0oFV4wvWsz1E7qUyh">a trajectory flattens the entire session into an ordered list of messages that shows the path an agent took from start to finish</citation>
**Implication:** direct support for shipping **two coordinated views**: the graph (topology) and the ordered "last proposal trace" strip (path). Naming them distinctly, and saying what each is for, is established practice.

**F6. AgentSight is a published precedent for observing an agent from a boundary where the observation cannot be silently wrong.**
URL: https://arxiv.org/abs/2508.02736 (retrieved 2026-09-18)
"boundary tracing, monitors agents from outside their application code at stable system interfaces using eBPF," addressing a "critical semantic gap: existing tools observe either an agent's high-level intent (via LLM prompts) or its low-level actions (e.g., system calls), but cannot correlate these two views." Published at PACMI'2025, doi 10.1145/3766882.3767169. <citation refs="MtZbIawrvJWnsv0tZY5sv">existing tools observe either an agent's high-level intent (via LLM prompts) or its low-level actions (e.g., system calls), but cannot correlate these two views</citation>
**Implication:** the intent/action gap is the same gap as plan/trace. The correct fix is correlation with both layers preserved and labelled, not replacing one with the other. Keep the six-family architecture visible; bind it to per-proposal evidence.

### 1B. Constraint validation and partial evaluation

**F7. JSON Schema 2020-12 formalizes "evaluated" as a first-class, tracked property distinct from pass/fail, and states directly that failed evaluation does not count as evaluation.**
URL: https://json-schema.org/draft/2020-12/json-schema-core (retrieved 2026-09-18)
Key normative text:
- "Such failed evaluations are not considered to contribute to whether or not the item or property has been evaluated. **Only successful evaluations are considered.**"
- "While 'short-circuit' evaluation is possible for assertions, collecting annotations requires examining all schemas that apply to an instance location, even if they cannot change the overall assertion result."
- "Schema objects that produce a false assertion result MUST NOT produce any annotation results."
- For `else` when `if` is absent: "Implementations MUST NOT evaluate the instance against this keyword, for either validation or annotation collection purposes, in such cases." (This is architectural out-of-scope, exactly analogous to a family that does not apply to an operation type.)
- On the cheapest output format: "Because no errors or annotations are returned with this format, it is RECOMMENDED that implementations use short-circuiting logic to return failure or success as soon as the outcome can be determined."
<citation refs="4SDdSO7YtI_Yue6L_-zE4">Such failed evaluations are not considered to contribute to whether or not the item or property has been evaluated. Only successful evaluations are considered.</citation>
**Implication:** the spec makes the explicit trade TRACE-RPG is now making: *short-circuiting is cheap but destroys the evaluation record; keeping the record costs extra evaluation.* Adopt its vocabulary distinction (evaluated vs unevaluated vs failed) rather than inventing one.

**F8. JSON Schema's four output formats are a ready-made fidelity ladder, and the highest one requires an explicit per-node verdict rather than letting viewers infer it.**
URL: https://json-schema.org/draft/2020-12/json-schema-core (retrieved 2026-09-18)
Four formats: flag, basic, detailed ("a condensed hierarchical structure"), verbose ("an uncondensed hierarchical structure that matches the exact structure of the schema"). On verbose: "The primary difference between this and the 'Detailed' structure is that all results are returned... Because of this, it is RECOMMENDED that each node also carry a `valid` property to indicate the validation result for that node."
**Implication:** this is the closest formal analogue to the proposed change. The "paper diagram" is roughly the *flag* format dressed up as a graph. The new trace should target *verbose*: full topology retained, **every node carrying its own explicit verdict field**.

**F9. SMT-LIB normatively warns that non-membership in an explanation means nothing at all.**
URL: https://smt-lib.org/papers/smt-lib-reference-v2.6-r2021-05-12.pdf (retrieved 2026-09-18, opened as PDF and text-extracted)
- `(get-unsat-core)` returns "a subset of all the formulas in the current context that is unsatisfiable by itself"; "Unlabeled formulas in the unsatisfiable core are simply not reported."
- Note 51: the labeling mechanism is useful "when they already know that the rest of the asserted formulas are jointly satisfiable."
- `(get-unsat-assumptions)`: "The returned sequence is not required to be minimal."
**Implication:** the strongest standards-body statement against the exact misreading in question. An explanation is a *subset*, not a *partition*: membership means "contributed," non-membership means **nothing** — not satisfied, not irrelevant. SMT-LIB manages this by documenting what silence means. A dashboard cannot rely on prose alone, because the graph *draws* the silent items.

**F10. xclingo tracks which rules fired, and explicitly declares "why not" out of scope in the artifact's own documentation.**
URL: https://arxiv.org/html/2009.10242v1 (Cabalar, Fandinno & Muñiz, *A System for Explainable Answer Set Programming*; retrieved 2026-09-18)
- The translation "includes auxiliary predicates and clingo theory atoms to keep track of the rules that have been fired"; xclingo "identifies which rules have been fired for each model by finding the `fired_` atoms."
- "a negative literal `not p` is never used in derivations, since it is understood as 'there is no cause for p.'"
- "This information may be relevant for answering why was not the light turned on, but is irrelevant for explaining why it has simply remained off, which is the purpose of xclingo."
- "the tool skips any intermediate node in the derivation tree that has no explicit trace label."
- "By now, xclingo just guarantees correctness of the obtained derivations, but not their minimality."
**Implication:** peer-reviewed precedent for the *boundary note* pattern: state in prose, next to the artifact, which question the visualization answers and which it does not. §4 is modelled on this.

**F11. clingo-explaid gives every unsatisfiable constraint a stable addressable id, and separates raw core from minimized core.**
URL: https://github.com/potassco/clingo-explaid (retrieved 2026-09-18)
Provides "Minimal Unsatisfiable Subsets (MUS)" via `CoreComputer` / `cc.shrink(core)`, and an "Unsatisfiable Constraints" reporting loop over an `uc_id -> unsat_constraint` mapping.
**Implication:** give every check a stable `code` (e.g. `PRECOND.DOOR_SEALED`) so the UI addresses a specific check rather than a position in the graph. Also note the two-stage vocabulary: the first answer is an over-approximation that is *then* narrowed, which argues for showing raw order before any summarization.

**F12. NeMo Guardrails reports only rails that were activated, marks the terminating rail explicitly, and separates policy-block from engine-failure.**
URL: https://docs.nvidia.com/nemo/guardrails/observability/logging (retrieved 2026-09-18)
- `activated_rails` holds "Detailed information about rails activated during generation."
- "To find which rail stopped a request on `IORails`, read `log.activated_rails` and look for the entry with `stop` set to `True`. The action's `return_value["failed"]` value distinguishes a rail failure from a policy block."
- Output variables include `triggered_input_rail` ("Name of input rail that triggered (if any)") and `allowed`.
**Implication:** three separations TRACE-RPG needs: (a) which checks ran, (b) which one *stopped* the run (flagged explicitly, not inferred from being last in the list), and (c) whether stopping was a legitimate deny or an engine fault. A pass/fail binary cannot express (c), which is why §2 proposes an `ERROR` state.

**F13. Guardrails AI logs validators in execution order with a per-validator outcome, but has no `not_run` outcome — absence is the only signal.**
URL: https://www.guardrailsai.com/docs/concepts/logs (retrieved 2026-09-18)
"Whenever `Guard.__call__` or `Guard.parse` is called, a new `Call` entry is added to a stack in sequence of execution"; calls decompose into `Iteration` objects; `validator_logs` entries carry `validator_name`, `value_before_validation`, `validation_result.outcome` (observed value `"fail"`), `value_after_validation`; failures are reachable via `iteration.failed_validations`; call-level `status` prints as `pass`.
**Implication (partly inference):** machine-honest but renderer-hostile. A UI that draws one node per *configured* validator and colors from `validator_logs` will paint un-run validators with whatever its fallback is. This is the TRACE-RPG bug in another codebase. The `value_before_validation` / `value_after_validation` pairing is, however, a good model for the repair step in the trace strip.

**F14. OPA keeps "what failed" and "what ran at all" as two separate tools.**
URLs: https://www.openpolicyagent.org/docs/cli/ and https://www.openpolicyagent.org/docs/debugging (retrieved 2026-09-18)
`opa eval --explain` accepts `{off, full, notes, fails, debug}` and `opa test --explain` accepts `{fails, full, notes, debug}` — `fails` is a dedicated first-class mode. Separately, "`rego_eval_with_profile` and `rego_eval_with_coverage` surface hot rules and per-line coverage."
**Implication:** "which check failed" and "which checks were evaluated" are different questions and get different affordances. Do not overload one graph with both. The graph answers coverage; the trace strip answers causation.
*Honest gap:* OPA's individual trace event-type names could not be confirmed (one candidate URL lacked the section, another returned 404). No claim is made about them.

**F15. pytest is the best human-facing vocabulary for "declared but never executed."**
URL: https://docs.pytest.org/en/stable/how-to/skipping.html (retrieved 2026-09-18)
- "A skip means that you expect your test to pass only if some conditions are met, otherwise pytest should skip running the test altogether."
- "pytest counts and lists skip and xfail tests separately."
- With `@pytest.mark.xfail(run=False)` — "If a test should be marked as xfail and reported as such but should not be even executed" — the reported line is literally `XFAIL xfail_demo.py::test_hello2` / `reason: [NOTRUN]`.
- Every skip API carries a `reason` string, e.g. `@pytest.mark.skipif(..., reason="requires python3.13 or higher")`.
**Implication:** four transferable mechanisms — a distinct terminal state never folded into pass; a **separate count** in the summary; a literal `[NOTRUN]` token; and a **mandatory reason** on every non-run item. Adopt all four.

**F16. Microsoft Guidance constrains generation and visually distinguishes model-generated from grammar-forced tokens, but does not expose a per-constraint pass/fail trace.**
URL: https://github.com/guidance-ai/guidance (retrieved 2026-09-18)
Guidance "allows users to constrain generation (e.g. with regex and CFGs)". In a Jupyter notebook it renders a widget, and the README notes "the varying highlighting of the generation. This is showing another of Guidance's capabilities: fast-forwarding of tokens... Guidance can fill in `h1>` without needing the model to perform a forward pass." It also supports offline grammar validation via `grammar.match(...)` and a `Mock` model. <citation refs="hlnRecXr00gp2_FeRk127">Note the varying highlighting of the generation. This is showing another of Guidance's capabilities: fast-forwarding of tokens.</citation>
**Implication:** Guidance's relevant contribution is *per-unit provenance highlighting* (which tokens the model chose vs which the grammar forced), not partial-evaluation labelling. Useful as precedent for marking provenance inline; **not** a source for not-evaluated semantics. Stated here so it is not over-claimed.

### 1C. Visual encoding

**F17. WCAG 2.2 SC 1.4.1 names green-valid / red-invalid as requiring an additional non-color indicator.**
URL: https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html (retrieved 2026-09-18)
"Color is not used as the only visual means of conveying information..." and, decisively: "if content relies on the user's ability to accurately perceive or differentiate a particular color an additional visual indicator will be required regardless of the contrast ratio between those colors. For example, knowing whether an outline is green for valid or red for invalid." Failure F81 covers "identifying required or error fields using color differences only."

**F18. WCAG 2.2 SC 1.4.11 requires 3:1 contrast for graphical objects and for component *states*.**
URL: https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html (retrieved 2026-09-18)
Covers "Visual information required to identify user interface components and states, except for inactive components" and "Parts of graphics required to understand the content," at "a contrast ratio of at least 3:1 against adjacent color(s)." "The term 'graphical object' applies to... the important parts of a more complex diagram such as each line in a graph." Threshold is strict: "the computed values should not be rounded (e.g. 2.999:1 would not meet the 3:1 threshold)." Contrast is not required where "A graphic with text embedded or overlaid conveys the same information." Also: "best practice would be for authors to avoid particularly thin lines and shapes."
**Note (inference):** a not-evaluated node is *informative*, not an inactive control, so the inactive-component exemption should not be claimed for it. A washed-out 1.5:1 gray node would be both non-conforming and misleading.

**F19. WCAG Technique G111 endorses pattern-plus-color, with a flow-chart example nearly identical to this use case.**
URL: https://www.w3.org/WAI/WCAG22/Techniques/general/G111 (retrieved 2026-09-18)
Objective: "to ensure that when color differences are used to convey information within non-text content, patterns are included to convey the same information in a manner that does not depend on color." Example 3: "A flow chart... uses dashed, arrowed lines with a green background to point to the next step in the process when the specified condition passes. It uses dotted arrowed lines with a red background... when the specified condition fails." Example 1 adds: "The legend uses the same colors and patterns to identify each bar."

**F20. Vega-Lite documents the exact failure mode: by default, invalid data renders as a legitimate value.**
URL: https://vega.github.io/vega-lite/docs/invalid-data.html (retrieved 2026-09-18)
In `"show"` mode "by default invalid values will produce the same visual values as zero (if the scale includes zero) or the minimum value (if the scale does not include zero)." Remedies named: set `config.scale.invalid` to an explicit color (`{color: {value: '#aaa'}}`), `"filter"` (exclude entirely), `"break-paths"` (visibly break the line), or conditional color encoding.
**Implication:** a major visualization grammar ships the default that silently turns missing data into a plausible value. This is the strongest single citation for the risk and for the mitigation: **require an explicit state per node; never let a fallback fill stand in for a verdict.**

**F21. Datawrapper ships hatching for incomplete data, with an automatic legend entry.**
URL: https://www.datawrapper.de/academy/pattern-overlay-in-choropleth-maps (retrieved 2026-09-18)
Purpose names incomplete data first: "for example, if the data is incomplete, from a different source, collected on a different date than in other regions." On legends: "To make it easy for your readers to interpret your patterns, legends are crucial. That's why as soon as you add a pattern to your map, it will automatically show up in a legend as well." Diagonals preferred because "they don't visually interfere with vertical or horizontal region boundaries"; "it's easier to tell two diagonal patterns apart if one has thicker lines"; "our default pattern opacity is only 50%. We recommend keeping the opacity at this level or even lower"; and restraint: "Most maps will work best with only one or two categories, since it's hard to distinguish between them."

**F22. Gray is the established encoding for missing data; red/green is a known hazard.**
URL: https://www.datawrapper.de/blog/colors-for-data-vis-style-guides (retrieved 2026-09-18)
"Gray is the most important color in data visualization. You'll need it to show less important data, missing data, or context data." Gray is also specified for "regions without data in choropleth maps." On red/green: "If you want to use green and red, test how they look to colorblind readers. Quite a few companies use blue for positive and red for negative instead to get around colorblindness issues."

**F23. Redundant encoding and the black-and-white test.**
URL: https://www.datawrapper.de/blog/colorblindness-part2 (retrieved 2026-09-18)
"for them, red and green won't look like an indicator for something good and bad, but like a darker olive/orange and a lighter one." "Blue is the safest hue." The test: "'Get it right in black & white'... If you print your data visualization with a black/white printer and it's still readable, any colorblind person will be able to read it, too." Quoting Peter Cardwell-Gardner: "The only bulletproof solution is to encode your data with a second visual variable: position, shape, patterns." Also: "To show colorblind readers that something is good or bad, double-encode with symbols like ✔️." Caution that Okabe-Ito pairs can be hard to distinguish "especially if they're used for fine lines."

**F24. GOV.UK Tag: the status word is always present; color is only a modifier.**
URL: https://design-system.service.gov.uk/components/tag/ (retrieved 2026-09-18)
"Use the Tag component to show users the status of something." Explicit rule: "Do not use colour alone to convey information, because it's not accessible... This is to meet WCAG 2.2 success criterion 1.4.1 Use of colour." Every documented example carries the word (`Completed`, `Active`, `Inactive`, `Pending`, `Rejected`, `Delayed`) with color as a class (`govuk-tag--grey`, `--red`, `--green`). Gray is used for `Inactive`. Restraint: "start with the smallest number of statuses you think might work." Naming: "Use adjectives (descriptive words) and not verbs (action words)."

**F25. Per-event animation must be gated, with a non-motion fallback.**
URL: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion (retrieved 2026-09-18)
"used to detect if a user has enabled a setting on their device to minimize the amount of non-essential motion"; motion "can trigger discomfort for those with vestibular motion disorders." Values `no-preference` and `reduce`. Notably the documented example **substitutes** a gentler animation rather than deleting the signal, and additionally changes background color and adds `text-decoration: overline`, preserving the information through non-motion channels. Baseline since January 2020.

---

## 2 Recommended state-semantics table

Six states. Five are per-check; the sixth (`REPAIRED`) is per-check-attempt and only appears after a repair round. Every state is carried **explicitly** in the trace payload; there is no inferred or default state.

| State (enum) | Label shown to viewer | Meaning (precise) | Must **not** be confused with | Visual encoding |
|---|---|---|---|---|
| `PASS` | `passed` | The engine ran this check against this proposal and the predicate was satisfied. Positive evidence. | `OUT_OF_SCOPE` and `SKIPPED`, which contain **no** evidence about satisfiability (F9, F7). | Solid blue fill `#DCE9F7`, stroke `#14539A` 2px solid, glyph `✓`, word `passed`. |
| `FAIL` | `failed` | The engine ran this check and the predicate was violated. This is a legitimate gate decision, not a malfunction. | `ERROR` — a policy block is not an engine fault (F12). | Solid red-tint fill `#FBE0DA`, stroke `#B3261E` 3px solid + 1px outer ring, glyph `✗`, word `failed`, plus the `code`. |
| `SKIPPED` | `skipped (short-circuit)` | In scope for this operation type and queued to run, but never executed because an earlier check failed and the engine stopped. Its verdict is **unknown**. | `PASS` (it never ran) and `OUT_OF_SCOPE` (it *was* applicable). | No fill (card background), stroke `#5F6368` 2px **dashed** `6 3`, glyph `↷`, word `skipped`. |
| `OUT_OF_SCOPE` | `not evaluated (n/a)` | Architecturally not applicable to this operation type. The engine was never going to run it. Carries a mandatory `reason`. | `PASS` above all; also `SKIPPED`, which would have run had the gate continued. | Diagonal **hatch** fill `#9AA0A6` at 50% opacity over card bg, stroke `#5F6368` 1.5px solid, glyph `∅`, word `not evaluated`. |
| `ERROR` | `could not evaluate` | The engine attempted the check and it could not produce a verdict (exception, timeout, missing world state). A fault, not a verdict. | `FAIL` (a real violation) and `OUT_OF_SCOPE` (an intended omission). Collapsing this into "not evaluated" hides genuine faults (F12). | Amber fill `#FDE68A`, stroke `#8A5300` 2.5px solid, glyph `!`, word `could not evaluate`. |
| `REPAIRED` | `failed → repaired → passed` | Attempt *n* was `FAIL`; a repair was applied; attempt *n+1* was `PASS`. Both attempts stay in the trace. | A clean `PASS` on first attempt. Never overwrite attempt 1. | Blue `PASS` body with a `#B3261E` left edge bar 4px, glyph `✓↻`, and both attempts listed in the strip (F13's before/after pattern). |

**Invariants that make the table load-bearing:**

1. **No default state.** A node whose state is absent from the payload renders as a visible `ERROR`-style "state missing" node and logs a console error. Do not fall back to gray, to neutral, or to `PASS`. This directly counters the documented Vega-Lite default (F20) and the OTel `Unset`-reads-as-success trap (F2).
2. **`PASS` requires positive evidence.** Following JSON Schema (F7), only a successful evaluation counts as evaluated. `SKIPPED` and `OUT_OF_SCOPE` are not weak passes.
3. **Every non-evaluated state carries a mandatory `reason` string** (F15, F21). `OUT_OF_SCOPE` reason example: `"operation_type=UTTER does not touch quest state"`.
4. **Counts never merge.** The summary reads `3 evaluated (2 passed, 1 failed) · 1 skipped · 2 not evaluated`, never `3/6` or `6 families checked` (F15's separate-counts rule).
5. **The short-circuit point is flagged explicitly**, not inferred from list position (F12's `stop: true`).

**Suggested payload shape** (verbose-format analogue per F8):

```json
{
  "proposal_id": "p-8814",
  "operation_type": "OPEN_CONTAINER",
  "decision": "hold",
  "short_circuit_at": "PRECONDITION.CONTAINER_UNLOCKED",
  "checks": [
    {"ord": 1, "family": "PRECONDITION", "code": "PRECONDITION.ACTOR_ADJACENT",
     "state": "PASS", "ms": 0.4},
    {"ord": 2, "family": "PRECONDITION", "code": "PRECONDITION.CONTAINER_UNLOCKED",
     "state": "FAIL", "ms": 0.6, "detail": "lock.state=sealed"},
    {"ord": 3, "family": "DISCLOSURE", "code": "DISCLOSURE.NO_UNEARNED_REVEAL",
     "state": "SKIPPED", "reason": "short-circuited at ord 2"}
  ],
  "not_evaluated": [
    {"family": "QUEST_STAGE",  "state": "OUT_OF_SCOPE",
     "reason": "operation type does not advance quest state"},
    {"family": "KNOWLEDGE",    "state": "OUT_OF_SCOPE", "reason": "no belief write"},
    {"family": "POLICY",       "state": "OUT_OF_SCOPE", "reason": "no narration emitted"},
    {"family": "REACHABILITY", "state": "OUT_OF_SCOPE", "reason": "no graph mutation"}
  ]
}
```

Note that `checks` and `not_evaluated` are **separate arrays**. This mirrors OPA's refusal to make one view answer both questions (F14) and makes it structurally impossible for a renderer to iterate `checks` and accidentally paint the rest.

---

## 3 Visual encoding recommendations

Assumes a light card background `#F7F8FA` at 640×400. Dark-theme variants should be derived by swapping fills and re-verifying contrast, not by inverting mechanically.

### 3.1 Layout budget

640×400 is tight for six nodes plus a legend plus a trace strip. Recommended split:

- **y 0–28** title + boundary note line 1
- **y 28–240** the graph (six family nodes in two rows of three, plus `proposal` entry node and `commit`/`hold` terminal)
- **y 240–276** per-event legend (single row, only states present in this event)
- **y 276–400** "last proposal trace" strip (scrollable, ~6–8 rows visible)

Node size ~104×44 is enough for a glyph, the family name at 11px, and the state word at 9px. Do not shrink below this: WCAG warns against thin lines and shapes that anti-alias faint (F18), and the state word must remain legible since it is the primary carrier (F24).

### 3.2 Node state palette

```
PASS          fill #DCE9F7  stroke #14539A  2.0px solid    glyph ✓   word "passed"
FAIL          fill #FBE0DA  stroke #B3261E  3.0px solid    glyph ✗   word "failed"
ERROR         fill #FDE68A  stroke #8A5300  2.5px solid    glyph !   word "could not evaluate"
SKIPPED       fill none     stroke #5F6368  2.0px dash 6 3 glyph ↷   word "skipped"
OUT_OF_SCOPE  fill url(#hatch-oos)  stroke #5F6368  1.5px solid  glyph ∅  word "not evaluated"
```

Rationale, point by point:

- **Blue for pass, not green.** Red/green alone reads to red-green-blind viewers as "a darker olive/orange and a lighter one," not as good/bad (F23); blue "is the safest hue" and blue-positive/red-negative is a documented workaround (F22).
- **Every node carries its state in words.** GOV.UK never ships a status without its word, explicitly to meet SC 1.4.1 (F24); WCAG requires an additional non-color indicator for valid/invalid outlines "regardless of the contrast ratio" (F17). Use adjectives, not verbs (F24).
- **Glyph as a third channel** (F23's "double-encode with symbols").
- **Hatching only for `OUT_OF_SCOPE`.** Use diagonal hatch, ~50% opacity, per Datawrapper's shipped incomplete-data pattern and opacity default (F21), and per G111 (F19). Restrict to **one** hatch pattern: two diagonal patterns are hard to tell apart (F21), which is why `SKIPPED` is differentiated by a **dashed outline with no fill** rather than a second hatch.
- **The two "no result" states differ from each other structurally**, not just by label: hatched-fill vs no-fill-dashed-outline.
- **Contrast.** Every stroke must clear 3:1 against `#F7F8FA` as a graphical object conveying **state**; do not round (F18). Do not claim the "inactive components" exemption for `OUT_OF_SCOPE` — it is informative content, and a near-invisible node is itself a misread.
- **Grayscale self-test.** Screenshot the card and desaturate. If `OUT_OF_SCOPE` and `PASS` are not instantly distinguishable, the encoding has failed (F23). Vary lightness across all five states, not just hue.

Hatch definition:

```svg
<defs>
  <pattern id="hatch-oos" width="6" height="6"
           patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
    <rect width="6" height="6" fill="#F7F8FA"/>
    <line x1="0" y1="0" x2="0" y2="6" stroke="#9AA0A6"
          stroke-width="2" stroke-opacity="0.5"/>
  </pattern>
</defs>
```

### 3.3 Per-event edge animation

- **Animate only edges that were actually traversed for this proposal.** Today's all-six pulse is the bug in motion form; an edge that animates is a factual claim that control flowed through it.
- Traversed edge: stroke `#14539A`, `stroke-dasharray` dash travelling once from source to target over ~600ms, then settling to a solid 2px stroke with an arrowhead marker that **persists**. The persistent state, not the motion, is the evidence.
- Edge into the short-circuit point: same travel, settling to `#B3261E` 3px solid, terminating in a small square cap rather than an arrowhead ("flow stopped here").
- Edges into `SKIPPED` nodes: 1px `#5F6368` dotted, **no animation**, no arrowhead.
- Edges into `OUT_OF_SCOPE` nodes: do not draw them at all, or draw at 1px dotted `#C4C7C5`. Following G111's flow-chart example, dashed vs dotted vs solid carries pass/fail/skip without color (F19).
- **Gate all motion:**

```css
@media (prefers-reduced-motion: reduce) {
  .edge-pulse { animation: none; }
  .edge-traversed { stroke-width: 3px; }          /* non-motion emphasis */
  .edge-traversed-last { stroke-dasharray: none; filter: url(#edge-glow); }
}
```

Follow MDN's own example and **substitute** rather than delete: reduced-motion users must still be able to see which edges fired, via weight/color/marker (F25).

### 3.4 Per-event legend

- Render legend rows **only for states present in this event**, plus always render a row for any of `SKIPPED` / `OUT_OF_SCOPE` / `ERROR` that occurs. A state that appears in the graph with no legend row is a state the viewer will guess at; Datawrapper adds the legend row automatically the moment a pattern is used (F21), and G111's legend reproduces both color and pattern (F19).
- Each row reproduces **the exact swatch** including hatch and dash pattern, plus glyph, plus word.
- Append separate counts, pytest-style (F15):
  `2 passed · 1 failed · 1 skipped · 2 not evaluated`
  Never `3/6`, never a single percentage, never a green "6 families" badge.

### 3.5 "Last proposal trace" strip

Ordered, monospace, one row per check, in execution order (F13's execution-order stack; F5's flattened trajectory):

```
#  FAMILY        CODE                            OUTCOME                 ms
1  PRECONDITION  PRECONDITION.ACTOR_ADJACENT     ✓ passed               0.4
2  PRECONDITION  PRECONDITION.CONTAINER_UNLOCKED ✗ failed  lock=sealed  0.6
   ══ short-circuit here: remaining in-scope checks were not run ══
3  DISCLOSURE    DISCLOSURE.NO_UNEARNED_REVEAL   ↷ skipped                –

   Not evaluated for operation type OPEN_CONTAINER (out of scope)
   ∅ QUEST STAGE   no quest-state advance
   ∅ KNOWLEDGE     no belief write
   ∅ POLICY        no narration emitted
   ∅ REACHABILITY  no graph mutation
```

Design notes:

- The short-circuit terminator is a **rendered rule line**, driven by the explicit `short_circuit_at` field, not inferred from which row happens to be last (F12).
- The out-of-scope block is visually **below and separated**, with a heading naming the operation type, and every entry carries its reason (F15, F21).
- When a repair round occurs, show both attempts as sibling rows (`2a` / `2b`) with before/after values (F13), never collapsing to a single green row.
- Clicking a strip row highlights the corresponding graph node, and vice versa. The graph answers coverage; the strip answers causation; keeping both and cross-linking them is the OPA split (F14) plus the LangSmith two-view pattern (F5).

---

## 4 Boundary wording

Two alternatives, both under 80 words. Place as a persistent subtitle on the card, not in a tooltip. Following xclingo's precedent of declaring in prose what the artifact does and does not answer (F10).

**Version A — plain-language, viewer-facing (65 words)**

> This is a per-proposal evaluation trace, not a schematic. Each node shows what the engine actually did for this commit: checks that ran and passed, the check that failed, checks skipped after the first failure, and families out of scope for this operation type. Families marked "not evaluated" never ran. That is not a pass, and says nothing about whether they would hold.

**Version B — precise, engineering-facing (58 words)**

> Per-proposal trace. The engine evaluates only the families relevant to each operation type and stops at the first failing check, so most commits legitimately leave families unevaluated. Unevaluated nodes are hatched and labelled; they are not passes and are excluded from the pass count. The six-family layout shows the architecture; the node states show this single proposal.

Both are honest about the same three things: (1) the layout is the plan and the states are the evidence (F1); (2) partial evaluation is *correct behaviour*, not a gap; (3) non-evaluation carries no information about satisfiability (F9).

---

## 5 Risks of misreading and mitigations

| # | Risk | Why it happens | Mitigation |
|---|---|---|---|
| R1 | **Not-evaluated read as passed** — the headline risk. | A fixed-topology graph draws all six nodes always; absence has no natural rendering (F3). Vega-Lite documents this exact default, where invalid values render as zero or the scale minimum (F20). | Distinct hue family + hatch + glyph + the words "not evaluated" + separate count. Never a dimmed-green or low-opacity pass (F21, F22, F24). |
| R2 | **Missing state silently renders as neutral-good.** | Renderer fallback fill; OTel's `Unset` default is documented as "unintuitive" precisely for this reason (F2). | Make state a required field. Unknown or missing state renders as a loud "state missing" node and logs an error. No silent default, ever. |
| R3 | **Short-circuit read as "the other checks passed."** | Human default assumption is that a pipeline runs to completion. SMT-LIB warns explicitly that non-membership in an explanation implies nothing (F9). | Explicit `short_circuit_at`, a rendered terminator rule in the strip, and `SKIPPED` nodes styled as *unknown* (no fill, dashed) rather than resolved (F12). |
| R4 | **Aggregate badge arithmetic hides the split.** | "3/6" or "50% green" folds three semantically distinct states into one denominator. | Never print a ratio over all six families. Use pytest-style separate counts: `2 passed · 1 failed · 1 skipped · 2 not evaluated` (F15). |
| R5 | **Colorblind or grayscale collapse.** | Red/green reads as two olives to red-green-blind viewers; hatch on a thin stroke anti-aliases away (F18, F23). | Blue-for-pass; vary lightness across all states; run the black-and-white test before shipping; keep strokes ≥2px and ≥3:1 contrast, unrounded (F18, F22, F23). |
| R6 | **Animation implies flow that did not occur.** | Today's card pulses all six edges on every commit — the current, known defect. | Animate only traversed edges; no animation into `SKIPPED` or `OUT_OF_SCOPE`; persistent settled stroke carries the evidence; gate behind `prefers-reduced-motion` with a non-motion fallback (F25). |
| R7 | **Engine faults disguised as policy decisions (or as omissions).** | A pass/fail binary has nowhere to put "the check could not run." NeMo separates `failed` from a policy block for exactly this reason (F12). | Distinct `ERROR` state with amber and `!`. Never fold engine faults into `OUT_OF_SCOPE`, which would make a broken checker look like an intentional design boundary. |
| R8 | **Stale trace after repair.** | The repair step re-runs checks; overwriting attempt 1 makes a gate that initially failed look clean. | Keep all attempts, show `REPAIRED` with a red edge bar, list `2a`/`2b` with before/after values (F13). Stamp the strip with `proposal_id`. |
| R9 | **Legend omits a state that is on screen.** | Legends are often authored once and drift as states are added. | Generate legend rows programmatically from the states present in the payload, reproducing exact swatches (F19, F21). Add a test asserting `set(states_rendered) ⊆ set(legend_rows)`. |
| R10 | **Screenshots outlive their caveat.** | Cards get pasted into slides and papers without the boundary note. | Render the boundary note **inside the SVG viewport**, not in surrounding HTML, so it travels with any export. Stamp `proposal_id` and timestamp in the corner. |
| R11 | **Collecting the full trace changes engine behaviour.** | JSON Schema is explicit that annotation collection forecloses short-circuiting that assertions alone would permit (F7); running all six families "for the trace" would be both slower and a different system. | Do **not** evaluate extra families to fill the graph. Record what the short-circuiting engine actually did, and render the gaps honestly. The trace must describe the engine, not reshape it. |

---

## 6 Sources

All retrieved **2026-09-18**.

**Provenance and trace standards**
1. W3C PROV-DM — https://www.w3.org/TR/prov-dm/
2. OpenTelemetry Tracing API specification (span `Status`, `Unset`/`Ok`/`Error`) — https://opentelemetry.io/docs/specs/otel/trace/api/
3. OpenTelemetry Traces concepts (span status narrative) — https://opentelemetry.io/docs/concepts/signals/traces/
4. Zipkin data model — https://zipkin.io/pages/data_model
5. Jaeger frontend UI configuration — https://www.jaegertracing.io/docs/2.10/frontend-ui/ *(opened; configuration-only, contributed no state semantics — recorded for completeness)*
6. Langfuse data model — https://langfuse.com/docs/observability/data-model
7. Langfuse log levels — https://langfuse.com/docs/observability/features/log-levels
8. LangSmith observability concepts — https://docs.langchain.com/langsmith/observability-concepts
9. AgentSight: System-Level Observability for AI Agents Using eBPF (arXiv:2508.02736, PACMI'2025) — https://arxiv.org/abs/2508.02736

**Constraint validation and partial evaluation**
10. JSON Schema draft 2020-12 core (annotations, unevaluated vocabulary, short-circuiting, output formats) — https://json-schema.org/draft/2020-12/json-schema-core
11. SMT-LIB Standard v2.6 (r2021-05-12), `get-unsat-core` / `get-unsat-assumptions` — https://smt-lib.org/papers/smt-lib-reference-v2.6-r2021-05-12.pdf
12. Cabalar, Fandinno & Muñiz, *A System for Explainable Answer Set Programming* (xclingo) — https://arxiv.org/html/2009.10242v1
13. clingo-explaid (Potassco) — https://github.com/potassco/clingo-explaid
14. NVIDIA NeMo Guardrails, observability/logging — https://docs.nvidia.com/nemo/guardrails/observability/logging
15. Guardrails AI, logs and history concepts — https://www.guardrailsai.com/docs/concepts/logs
16. Open Policy Agent CLI reference (`--explain {off,full,notes,fails,debug}`) — https://www.openpolicyagent.org/docs/cli/
17. Open Policy Agent debugging (explain, profile, coverage) — https://www.openpolicyagent.org/docs/debugging
18. pytest, "How to use skip and xfail" (`SKIPPED`, `[NOTRUN]`, `reason=`) — https://docs.pytest.org/en/stable/how-to/skipping.html
19. Microsoft Guidance — https://github.com/guidance-ai/guidance

**Visual encoding**
20. WCAG 2.2 Understanding SC 1.4.1 Use of Color — https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
21. WCAG 2.2 Understanding SC 1.4.11 Non-text Contrast — https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html
22. WCAG 2.2 Technique G111: Using color and pattern — https://www.w3.org/WAI/WCAG22/Techniques/general/G111
23. Vega-Lite, Invalid Data — https://vega.github.io/vega-lite/docs/invalid-data.html
24. Datawrapper Academy, Pattern overlay in choropleth maps — https://www.datawrapper.de/academy/pattern-overlay-in-choropleth-maps
25. Datawrapper blog, colors in data vis style guides — https://www.datawrapper.de/blog/colors-for-data-vis-style-guides
26. Datawrapper blog, visualizing data for colorblind readers (part 2) — https://www.datawrapper.de/blog/colorblindness-part2
27. GOV.UK Design System, Tag component — https://design-system.service.gov.uk/components/tag/
28. MDN, `prefers-reduced-motion` — https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion

**Attempted, not retrieved (no claims rest on these)**
- https://jfly.uni-koeln.de/color/ (Okabe & Ito) — returned empty content. The Okabe-Ito palette is mentioned only as referenced *by* source 26.
- https://style.ons.gov.uk/data-visualisation/using-colours/ — returned a 0-byte response.
- https://microsoft.github.io/z3guide/docs/strategies/cores-and-satisfying-subsets/ — HTTP 404. Unsat-core semantics rest on source 11 (SMT-LIB) only, not on Z3 documentation.
- https://www.openpolicyagent.org/docs/policy-reference/builtins/trace — HTTP 404; and https://www.openpolicyagent.org/docs/policy-reference#tracing had no tracing section. **OPA's individual trace event-type names are therefore unverified and are not cited anywhere above.**
- https://ceur-ws.org/Vol-3428/paper2.pdf ("Advancements in xASP") — seen only as a search excerpt, not opened; not cited.
- No CDC / Eurostat / USGS "insufficient data" cartographic style guide was successfully opened. The hatching-for-incomplete-data precedent rests on sources 22 and 24, both of which were read in full.

**Marked inferences (not source claims):** the five-to-six state expansion including `ERROR` is extrapolated from NeMo's `failed`-vs-policy-block distinction (F12), not stated by any source as a UI recommendation. The judgement that `OUT_OF_SCOPE` cannot claim WCAG's "inactive components" exemption is my reading of SC 1.4.11's scope, not an explicit ruling in the Understanding document. The specific hex values in §3.2 are my proposals and must be contrast-verified against your actual card background before shipping.