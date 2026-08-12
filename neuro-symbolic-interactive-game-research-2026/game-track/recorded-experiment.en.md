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

`run_experiment_case` emits one schema- and semantic-contract-validated assigned-case record. Missing, malformed, timeout, and invalid adapter responses leave state unchanged and remain in the treatment-policy denominator. Proposal traces are written separately and can be checksum-verified and semantically replayed.

Every assigned-case row has a deterministic `record_hash`; every proposal outcome also links to a full `trace_hash`. Changing a reported token, latency, failure, seed, or status invalidates the checksum. These are unkeyed SHA-256 integrity checks, not signatures or protection against an attacker who can rewrite both content and checksum.

Use one trace JSONL path per continuous episode. The writer rejects a shared result/trace destination, mismatched result–outcome pairs, and appends whose prior state does not equal the last state already stored in that trace. Pair writes are flushed with best-effort rollback; callers still own cross-process locking.

Treatment-policy summaries require the frozen assignment manifest. The runner rejects duplicate observed rows, duplicate manifest entries, missing assignments, and unexpected assignments before calculating rates or token totals.

```bash
uv run python examples/recorded_experiment.py
```

Outputs are written under ignored `runs/recorded-experiment/`. Recorded provider latency must not be presented as the current machine's live latency; `runner_latency_ms` measures only local adapter overhead. `provider_response_latency_*` is conditional on receiving a response and reports `latency_observed_cases`; it excludes timeout/API failures. The confirmatory total-latency metric must preregister a deadline-censoring or timeout-cap policy over every assigned case.
