# TRACE-RPG Benchmark Datasheet (Gebru et al. Format)

## 1. Motivation & Scope
- **Purpose**: Reproducible neuro-symbolic safety, multi-hop epistemic/disclosure gating, counterexample-guided candidate repair, and live Godot 4.7.1 closed-loop verification benchmark for interactive RPG agents.
- **Maintainers**: Authors (double-anonymous anonymized for peer review).

## 2. Composition
1. `multihop_ontology_results.json`: 48 deterministic epistemic/disclosure cases across 3 worlds (16 1-hop, 16 derivation, 16 role-inheritance).
2. `multiquest_live_results.json`: 24 live Antigravity CLI Gemini episodes (129 turns) across 3 worlds (`sealed-lighthouse-v1`, `sunken-archive-v1`, `clockwork-observatory-v1`).
3. `audit_b_calibrated_results.json`, `audit_b_live_results.json`, `audit_b_jev_results.json`: 88 EN/KO cases testing Stage-2 `keeper_secret` escape filtering.
4. `tr_human_eval_packet.json`: 36 blinded `TR01-TR06` trace items (`12` clean commit, `12` repaired commit, `12` uncommitted failure; status `AWAITING_HUMAN_RATERS`, `N=0` raters, 0 fabricated labels).
5. `phase2_multihop_5world_results.json`: 120 deterministic cases across 5 quest worlds (adding `ivory-citadel-v1` [6 rooms, 3 actors] and `glass-foundry-v1` [8 rooms, 3 actors]).
6. `phase2_multiagent_epistemic_results.json`: 30 3-role multi-agent episodes (90 turns/arm x 5 shielding arms = 150 arm-episode evaluations) with Wilson 95% CIs and exact McNemar p-values.
7. `phase2_godot_live_closed_loop_results.json`: 16 live Gemini -> Headless Godot 4.7.1 closed-loop episodes + fresh-process 0-LLM Godot replay checking `EXACT_TERMINAL_HASH`.
8. `phase2_multisecret_escape_results.json`: Disjoint 180-case 3-domain bilingual EN/KO corpus (`keeper_secret`, `council_forgery`, `eclipse_sabotage`).
9. `phase2_live_shield_and_multihop_results.json`: 60 live 5-world tasks comparing deterministic `rho` repair vs. live LLM self-repair (`K=1`) and `multihop_ontology_gate` vs. flat/affordance masks.

## 3. Provenance & Known Boundaries
- **No Personal / Web-Scraped PII**: All worlds, entities, and EN/KO texts are author-constructed synthetic narrative domains; zero user logs or private host IPs appear.
- **Model Metadata Limits**: Live CLI runs record `--json-schema`, CLI version, token counts, and wall latency, with provider revisions (`UNATTESTED_BY_CLI`) and seeds (`CLI_UNSUPPORTED`) preserved transparently and all timeout/parse failures retained in denominators.
- **Human Studies Unexecuted**: `N=0` human players/raters (`TR01-TR06` packet awaits >= 2 independent human raters for Krippendorff alpha).
