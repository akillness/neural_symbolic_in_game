# Recorded-response experiment track

The recorded adapter freezes proposal payloads before evaluation so validation, replay, metric code, and paper-table generation can be tested without network drift or model cost. `schemas/recorded-proposals.schema.json` and the runtime boundary reject implicit string/number coercion, malformed candidate arrays, duplicate set members, and non-JSON metadata.

| Input field | Meaning |
|---|---|
| `model_id`, `model_revision` | Exact source identity for every case |
| `scenario_id`, `seed` | Unique lookup key within the fixture |
| `candidate` | Untrusted model proposal; authoritative `ActionPolicy` still governs it |
| `provider_latency_ms` | Latency observed when the response was originally captured |
| `input_tokens`, `output_tokens` | Frozen provider accounting |
| `failure` | Classified timeout/API/parse outcome with no candidate |

`run_experiment_case` emits one schema- and semantic-contract-validated assigned-case record (schema `1.2.0`). Missing, malformed, timeout, invalid-adapter, and classified repair-callback failures leave the full canonical state unchanged and remain in the treatment-policy denominator. Completed proposal outcomes are written separately and can be checksum-verified and symbolically replayed. A repair callback that raises still produces a terminal `controller_failure` row, but the current record does not preserve a completed trace for that partial execution.

Every assigned-case row has a deterministic `record_hash`; every completed proposal outcome also links to a full `trace_hash`. `proposal_hash`, `prior_state_hash`, and `final_state_hash` bind the declared proposal and complete canonical states. Changing a reported token, latency, failure, seed, status, or bound hash invalidates the checksum. These are unkeyed SHA-256 integrity checks, not signatures or protection against an attacker who can rewrite both content and checksum. Replay revalidates the recorded symbolic candidates and states; it does not authenticate or re-execute how a repairer generated its next candidate.

Use one trace JSONL path per continuous episode. The writer rejects a shared result/trace destination, mismatched result–outcome pairs, and appends whose prior state does not equal the last state already stored in that trace. Pair writes are flushed with best-effort rollback; callers still own cross-process locking.

Treatment-policy summaries require a manifest frozen before execution. The nine-part key is `(run_id, arm_id, scenario_id, seed, model_id, model_revision, controller_config_hash, assignment_input_hash, prior_state_hash)`. `planned_experiment_assignment` computes it without invoking the adapter; the runner rejects duplicate observed rows, duplicate manifest entries, missing assignments, and unexpected assignments before calculating rates or token totals.

```bash
uv run python examples/recorded_experiment.py
```

Outputs are written under ignored `runs/recorded-experiment/`. Recorded provider latency must not be presented as the current machine's live latency; `runner_latency_ms` is a single-run local diagnostic spanning adapter invocation, validation, and any repair. `provider_response_latency_*` is conditional on receiving a response and reports `latency_observed_cases`; it excludes timeout/API failures. The confirmatory total-latency metric must preregister a deadline-censoring or timeout-cap policy over every assigned case.
