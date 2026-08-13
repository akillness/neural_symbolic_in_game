# Blinded Evaluation UI Specification

Status: `[TARGET]`; no participant data collected

## Player/annotator surface

- anonymous item ID, localized scene observation, candidate response/action, committed consequence;
- Likert or ordinal fields only after independent encoded/semantic oracle labels are locked;
- no model, arm, repair count, validator result, prompt, policy, or file path;
- randomized presentation order and optional attention-check field;
- explicit skip/withdraw controls and no free-text personal data prompt.

## Research inspector surface

- assignment key, build/content/image-pack hashes, model revision, arm, prompt/policy/oracle hashes;
- every proposal/validation/repair/terminal record; state before/after and replay result;
- latency/tokens/cost/failure class and adjudication status.

The two surfaces must use separate routes/build flags, not a hideable panel in the same blinded
DOM/tree. Screenshots used for VLM input may never contain inspector pixels.
