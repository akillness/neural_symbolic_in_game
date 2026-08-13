# Local Codex OAuth LLM companion

This optional local companion delegates authentication and model execution to the official Codex
CLI. It does not implement a browser OAuth client, expose an API key, or ship authentication into
the Godot/Vercel build. OpenAI's official documentation recommends device-code authentication for
headless or callback-blocked environments and documents `codex login status` for inspecting the
active method: [Codex authentication](https://developers.openai.com/codex/auth/).

## Boundary

- `login` invokes exactly `codex login --device-auth` with the terminal streams inherited. The
  official CLI prints the one-time URL/code; this wrapper does not capture or log it.
- `status` invokes `codex login status` and emits only a secret-free JSON projection. It never reads
  a Codex credential file.
- `prompt` accepts only a ChatGPT-authenticated status, then invokes `codex exec` in a disposable
  empty directory with `--ephemeral`, `--sandbox read-only`, an explicit output schema, ignored
  project rules, and no persistent session.
- Every successful result is `candidate_soft_proposal_only`, has `authorization_effect: none`, and
  states `canonical_state_mutated: false` plus `hard_validation_required: true`.
- This path never calls the hard policy writer, commits a game action, edits canonical state, or
  creates research evidence. A caller must separately submit any proposed game action to the
  deterministic hard validator.

Do not expose this command through a public web endpoint. The official documentation warns against
exposing Codex execution in untrusted or public environments.

## Usage

```bash
# Interactive, official device-code flow. Run only when a login is needed.
python3 scripts/codex_oauth_llm.py login

# Machine-readable; exits 0 only when ChatGPT OAuth is ready for prompt use.
python3 scripts/codex_oauth_llm.py status

# One isolated soft proposal. The request ID is copied into and checked against the result.
python3 scripts/codex_oauth_llm.py prompt \
  --request-id scene-dialogue:001 \
  "Suggest a short harbor-master response."

# Explicit live smoke; this contacts the service and may consume account quota.
python3 scripts/codex_oauth_llm.py smoke --request-id oauth-smoke:001
```

Use `--model <model>` only when the account is entitled to that exact model. The default leaves
model selection to the installed Codex CLI. Static tests never log in or contact the service:

```bash
./scripts/validate_codex_oauth_llm.sh
```
