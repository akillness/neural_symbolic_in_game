# TRACE-RPG Harness

Architecture: gated fan-out/fan-in with producer–reviewer loops.

The file-based agent definitions live in `../.claude/agents/`; reusable skills live in `../.claude/skills/`. This directory owns platform-neutral workflows, the ownership map, and release gates. Agent-team execution requires a compatible runtime; otherwise run each workflow phase with native subagents and preserve the same artifacts.

| Phase | Parallel producers | Independent gate | Output |
|---|---|---|---|
| Evidence | evidence researcher, ontology engineer | research orchestrator | source/claim ledgers |
| Protocol | experiment designer, statistician, game integrator | logic auditor | frozen protocol and bridge |
| Execution | model adapters and engine/mock track | reproducibility verifier | immutable traces |
| Manuscript | bilingual editor | research orchestrator | claim-linked KO/EN drafts |

No agent may approve its own high-risk artifact. The orchestrator records gate decisions in
`_workspace/current/production/gate-reviews/` and never deletes failed intermediate outputs.
