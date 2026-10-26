# Fixed-game native runtime comparison / 고정 게임 native 런타임 비교 — 2026-10-26

**Status: PUBLICATION_CHECKS_PASS / SELECTED_TREE_CI_PASS**
**Last updated / 갱신일:** 2026-10-26. **Evidence level / 근거 수준:** bounded exploratory pilot, not `verified-empirical`.

## Scope and dated-state separation / 범위와 과거 상태 구분

This report preserves the completed eight-assignment native scope for one authored quest, `sealed-lighthouse-v1`: two requested Codex selectors × `general_rule`/`ontology` × two repeats per cell, seed 20261024, serial concurrency 1. The proposer is stateless and returns typed intent; the deterministic Python planner/checker and Godot-only state commit retain authority. The observed outcome belongs to that complete stack, not to the requested model alone. Limits were 180 seconds per episode, 60 seconds per response, 12 observable host invocations per episode and 2 logical repairs per decision.

고정 게임 안의 실행 제안 비교이며 **모델별 독립 게임 제작 비교가 아니다**. [Older dated planning notes](2026-10-23-current-model-contribution-and-comparison-plan.md) retain their then-correct native=0/blocked states; the present measured checkpoint supersedes only their current-status meaning. The older operator-assisted development case (`n=1`, six CLI invocations, zero independent repeats), historical E1/E2/E3/NPC lanes, injected-response engineering fixtures and unlaunched wider model panels remain separate; none is pooled into these eight assignments.

## Measured outcomes / 실측 결과

All eight original assigned IDs remain in the system denominator: **5/8 system-goal successes**, native execution observed in **7/8**. The descriptive 5/7 among observed executions is not a replacement primary denominator. There was one serializer technical failure and two response-timeout failures. Observed totals are **23 host invocations**, **0 repairs**, **0 initial-proposal failures recorded**, and **0 unsafe committed transitions out of 16 observed commits**. The zero unsafe numerator does not turn unobserved row 1 into a safety pass, and zero observed repairs does not test repair effectiveness. Host invocations are not provider-request counts.

| Requested selector / 요청 selector | Representation / 표현 | Success/assigned | Native execution observed | Host invocations | Unsafe/committed | Response timeouts |
|---|---|---:|---:|---:|---:|---:|
| `gpt-6.1-sol` | `general_rule` | 1/2 | 1 | 4 | 0/3 | 0 |
| `gpt-6.1-sol` | `ontology` | 0/2 | 2 | 3 | 0/1 | 2 |
| `gpt-5.6-sol` | `general_rule` | 2/2 | 2 | 8 | 0/6 | 0 |
| `gpt-5.6-sol` | `ontology` | 2/2 | 2 | 8 | 0/6 | 0 |
| **Total / 합계** | **4 cells, 2 assigned each** | **5/8** | **7** | **23** | **0/16** | **2** |

| Row | Original `planned_id` | Outcome | `goal_reached` | Elapsed seconds | Fresh-engine disposition |
|---|---|---|---|---:|---|
| 1 | `sealed-lighthouse-v1:gpt-6.1-sol:general_rule:repeat-1` | `technical_failure` | `null` | `null` | `NOT_OBSERVED` |
| 2 | `sealed-lighthouse-v1:gpt-6.1-sol:general_rule:repeat-2` | `success` | `true` | 45.908 | `VALID` |
| 3 | `sealed-lighthouse-v1:gpt-6.1-sol:ontology:repeat-1` | `failure: response_timeout` | `false` | 84.659 | `VALID` |
| 4 | `sealed-lighthouse-v1:gpt-6.1-sol:ontology:repeat-2` | `failure: response_timeout` | `null` | 60.045 | `NOT_RUN` |
| 5 | `sealed-lighthouse-v1:gpt-5.6-sol:general_rule:repeat-1` | `success` | `true` | 41.093 | `VALID` |
| 6 | `sealed-lighthouse-v1:gpt-5.6-sol:general_rule:repeat-2` | `success` | `true` | 39.394 | `VALID` |
| 7 | `sealed-lighthouse-v1:gpt-5.6-sol:ontology:repeat-1` | `success` | `true` | 36.677 | `VALID` |
| 8 | `sealed-lighthouse-v1:gpt-5.6-sol:ontology:repeat-2` | `success` | `true` | 29.551 | `VALID` |

Row 1 failed at the harness configuration JSON-serialization boundary and was **never rerun**. Its `executed`, goal, episode hash, elapsed/preparation timing, repair and commit counts remain `null`; `primary_success=false` retains the assigned system failure without attributing it to GPT-6.1 capability. Zero observed host invocations does not establish `executed=false`. Row 4 did execute natively but timed out before an observed commit or terminal goal observation: `committed_transitions=0`, `goal_reached=null`, safety `NO_COMMIT_OBSERVED`; it is neither a successful goal nor an observed invalid replay. Row 3's valid replay reproduces its partial committed trajectory, not goal completion. A response limit is not the whole-episode duration.

Timing has **n=7 observed episodes**, includes failures/timeouts and is not pure inference latency or time-to-success. Existing independent-audit calculations report elapsed mean/median **48.189/41.093 s**, and preparation mean/median **6.673/6.301 s**. The seven elapsed values match terminal minus first-host-dispatch timestamps; preparation is separately timed. Missing row-1 timing is not zero. Row values above are rounded to three decimals; [results][results] retain full precision.

## Replay, integrity and audit / 재생·무결성·감사

**Fresh-engine replay: VALID 6 / INVALID 0 / NOT_RUN 1 (row 4) / NOT_OBSERVED 1 (row 1).** Six performed replays recorded zero replay-added model calls. **Semantic record-link replay: valid 7 / invalid 0 / unobserved 1 (row 1).** Record-link validity is not fresh-engine execution, safety, narrative quality or goal success. 재생이 수행됐는지와 수행 결과의 유효성을 분리하며, `null`을 `false`나 통과로 바꾸지 않는다.

The public [integrity receipt][integrity] and [independent audit][audit] preserve 8 unique assigned IDs, 8/8 original result-file links, 7/7 observed episode/record-hash links and 23/23 approved outgoing instruction/prompt/schema combinations. All five successful terminal-state hashes matched the independent goal oracle; neither timeout row matched the goal terminal hash. These are existing receipt findings, not fresh recomputations by this archival edit. The explicit replay-disposition projection changed no native record hash and added no model call or rerun.

The audit is a **bounded independent code-reviewer fallback**, with PASS and no listed findings, plus a PASS follow-up limited to replay dispositions and cross-public digest links. The dedicated verifier failed with HTTP 429 before output. This is not a dedicated-verifier PASS, provider attestation, attested second-model independence or efficacy certification; the follow-up did not re-audit native transport.

## Revision confound and inference limits / 소스 개정 교란과 추론 한계

A source serialization fix occurred **after row 1**. The public result binds row 1 to source manifest `274e301ab08f3a0411cf18315c777d0644403bf7eaae2d594e9be11205785ee1`, while rows 2–8 bind `248212c53a92471ae48c5026f97fd22190d26a75a1a696cf208b08bdb492dfa7`. This is a disclosed source-revision confound, not one unchanged-source comparison. Preserve the first failure and both identities; do not replace it with a post-fix favorable run.

[INFERENCE] One authored quest, two repeats per cell, fixed ordering/source history, response timeouts and a shared deterministic controller support only a bounded feasibility/accounting observation. They do **not** establish model ranking, ontology efficacy or causal representation advantage, general ontology consistency, C noninferiority/practical substitutability, player benefit, whole-game creation or confirmatory A/C evidence. Zero unsafe observed commits under a common gate does not identify an ontology effect. Requested selectors are not attested served provider identities/revisions, and equal nominal settings do not establish equal compute. No new citation or independent efficacy claim is introduced.

## Operational closure and publication gates / 운영 종료와 출판 게이트

The public [operational closure receipt][closure] records the assigned native scope finished, all eight original IDs terminal, no rerun of the first failure, temporary external authority files removed and no further launches authorized by this completed scope. Automatic reload was observed **OFF before and after**, with no setting change, purchase or provider/API-key switch by this workflow. This is operator-observed workflow closure, not provider-signed billing attestation or cryptographic revocation of every possible copied capability. It does not prove credit exclusion, zero credit consumption or zero cash charge. Provider identity, immutable revision, provider-request counts, provider cost, actual credit consumption and actual cash charge remain **unknown**; public provider fields remain `null`. This report contains no account data, quota/balance values, credentials or private paths.

**Publication checks: `PUBLICATION_CHECKS_PASS`; exact selected-source-tree checks: `SELECTED_TREE_CI_PASS`.** The public [publication verification receipt][publication] records 185 affected tests + 326 subtests PASS; EN/KO main papers each 10 pages and supplements each 1 page, Type3 fonts 0 and forbidden log diagnostics 0; visual provenance PASS with 134 receipts, 10 SVGs and 22 isolated double-regenerated sources; crosswalk PASS with 5 contributions, 58 references, 9 topics, 3 experiment lanes and 1 engineering lane; project integrity PASS. PDF/AUX labels and all 58 main citation numbers match between editions.
The exact 66-file public selection passed every step of `bash scripts/verify_like_ci.sh` in an isolated checkout with `UV_OFFLINE=1` and `PYTHONDONTWRITEBYTECODE=1`: 528 unit tests, 83 game-track tests + 48 subtests, lint/format, integrity, crosswalk, visual regeneration, offline smoke, harness, game-track, deep-research, survey and wiki gates. This is local CI-equivalent evidence, not a hosted CI run. Source commit `b4a4abdd2f10f71c66f7adc1e6c04088df6743de` has the tested tree `820833702716ca57cc3b1d0684de6a568b75d59a`; this source-bound receipt does not attest remote delivery, which must be checked against repository refs.
Results remain byte-bound to SHA-256 `ba369ab2f4e02afaeac643490e13fe6785ac7f8cbd04a5b88507c2cc4691c26e`; semantic replay stays 7/0/1 and fresh-engine stays VALID6/INVALID0/NOT_RUN1/NOT_OBSERVED1. No new native experiment was launched during publication regeneration or CI. Working-tree/source-tree PASS is not deployment, provider certification or confirmatory A/C evidence.

The initial supplementary review was **FIX**, with four findings subsequently closed by the **bounded independent code-reviewer fallback PASS** through source inspection and behavioral regressions. The dedicated native verifier's HTTP 429 remains unavailable, not PASS; second-model/provider attestation is not claimed. Main's final handoff also records visual read-back of the actual comparison PNG, printed Table XIII/native Figure 5 and both supplementary Table XIV surfaces, preservation of failed gates/assigned failures, no font-size reduction and no evidence deletion to obtain a pass. Unmeasured Table XIV and all TR01–TR06 dimensions remain complete in the supplied bilingual supplements; relocation does not make them measured or validated efficacy results.

The [frozen protocol][protocol] retains `USER_APPROVED_SCOPE_ADMISSION_REVIEW_PENDING` as prelaunch provenance, **not the current execution-admission verdict**; the public publication receipt explicitly separates frozen protocol provenance from current admission certification. Neither file creates new launch authority or retroactively replaces source-bound execution evidence. General upstream redistribution permission remains **unverified**: public-source access and user approval of the bounded input are not a blanket third-party redistribution grant. The model-catalog extract's Apache-2.0 license/notices are a separate, narrower documented case. Earlier failed publication checkpoints remain history; they were not erased or promoted into these current-byte passes.

## Public evidence and publication artifacts / 공개 근거와 출판 산출물

All paths below are repository-relative public evidence or publication artifacts, not private native logs. Public projections are not byte-equivalent raw transport captures.

- [Assigned outcomes][results], [public traces][traces], [integrity receipt][integrity], [independent fallback audit][audit] and [operational closure][closure] form the public evidence packet in `research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1` under the research project.
- Comparison figure: [SVG][figure-svg] / [PNG][figure-png]. Comparison tables: [English][table-en] / [한국어][table-ko]; generated results text: [English][text-en] / [한국어][text-ko]. They derive from the same pilot, not additional samples; working-tree artifact/provenance checks PASS in the [verification receipt][publication].
- Verified paired main PDFs: [English manuscript][pdf-en] / [한국어 논문][pdf-ko], each 10 pages. Complete traceability supplements: English [PDF][supp-pdf-en] / [TeX][supp-tex-en], 한국어 [PDF][supp-pdf-ko] / [TeX][supp-tex-ko], each PDF 1 page. [Publication verification][publication] records their hashes, complete Table XIV/six-dimension content and bounded working-tree/source-tree checks; remote delivery is verified separately through repository refs.

## Reusable lesson / 재사용할 교훈

Validate the **exact CLI boundary** that will serialize configuration, admit frozen request bytes and dispatch to the native host; a passing injected callback or preparation path is not proof that this boundary works. Preserve assigned failures and original IDs through repairs. Record **whether replay ran separately from whether it was valid**: row 4 is `NOT_RUN`, row 1 is `NOT_OBSERVED`, neither is `INVALID` or a pass. **Frozen-byte admission must be an outcome-neutral integrity check, never a favorable-outcome filter**: timeout, refusal, technical failure and missingness stay in their assigned denominators with their actual nulls. Exact-byte verification is not scientific efficacy or provider-identity proof.

정확한 CLI 직렬화·전송 경계 검증, 원래 배정 실패 보존, 재생 수행 여부/유효성 분리, 결과에 중립적인 동결 바이트 admission을 다음 연구에서도 유지한다. [Claim-status conventions](../concepts/evidence-and-claim-status.md) prohibit direct pilot-to-`verified-empirical` promotion; [study conventions](../concepts/journal-grade-experimental-design.md) require separate prospective confirmatory evidence.

[results]: ../../../neuro-symbolic-interactive-game-research-2026/research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/results.json
[traces]: ../../../neuro-symbolic-interactive-game-research-2026/research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/public-traces.json
[integrity]: ../../../neuro-symbolic-interactive-game-research-2026/research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/integrity-audit.json
[audit]: ../../../neuro-symbolic-interactive-game-research-2026/research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/independent-audit.json
[closure]: ../../../neuro-symbolic-interactive-game-research-2026/research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/operational-closure.json
[figure-svg]: ../../../neuro-symbolic-interactive-game-research-2026/paper/latex/figures/fig_runtime_comparison.svg
[figure-png]: ../../../neuro-symbolic-interactive-game-research-2026/paper/latex/figures/fig_runtime_comparison.png
[table-en]: ../../../neuro-symbolic-interactive-game-research-2026/paper/latex/generated/runtime_comparison_tables_en.tex
[table-ko]: ../../../neuro-symbolic-interactive-game-research-2026/paper/latex/generated/runtime_comparison_tables_ko.tex
[text-en]: ../../../neuro-symbolic-interactive-game-research-2026/paper/latex/generated/runtime_comparison_results_en.tex
[text-ko]: ../../../neuro-symbolic-interactive-game-research-2026/paper/latex/generated/runtime_comparison_results_ko.tex
[pdf-en]: ../../../neuro-symbolic-interactive-game-research-2026/paper/latex/en/main.pdf
[pdf-ko]: ../../../neuro-symbolic-interactive-game-research-2026/paper/latex/ko/main.pdf
[publication]: ../../../neuro-symbolic-interactive-game-research-2026/research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/publication-verification.json
[protocol]: ../../../neuro-symbolic-interactive-game-research-2026/research/runtime-model-swap-20261024/codex-live-20261026/public-packet-v1/protocol.json
[supp-pdf-en]: ../../../neuro-symbolic-interactive-game-research-2026/paper/latex/en/traceability-supplement.pdf
[supp-tex-en]: ../../../neuro-symbolic-interactive-game-research-2026/paper/latex/en/traceability-supplement.tex
[supp-pdf-ko]: ../../../neuro-symbolic-interactive-game-research-2026/paper/latex/ko/traceability-supplement.pdf
[supp-tex-ko]: ../../../neuro-symbolic-interactive-game-research-2026/paper/latex/ko/traceability-supplement.tex
