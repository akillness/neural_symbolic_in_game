# Stage 7 Cross-Model Verification / 7단계 교차 모델 검증

Status: **NOT_ACTIVATED**

Date: 2026-08-13

## Activation gate / 활성화 조건

Stage 7 is optional and activates only when `ARS_CROSS_MODEL=1` is set together with an
OpenAI-compatible endpoint. The specification is explicit that the pipeline must never silently
downgrade to single-model when the variable is set.

At execution time:

| Condition | Observed |
| --- | --- |
| `ARS_CROSS_MODEL` | unset |
| `OPENAI_BASE_URL` | unset |
| `OPENAI_API_KEY` | unset |
| LM Studio `127.0.0.1:1234` | no listener |
| Local `:8000` OpenAI-compatible | no listener |
| Ollama `127.0.0.1:11434` | reachable; `qwen2.5:{0.5b,1.5b,3b,7b}`, `deepseek-r1:1.5b` |

The activation variable is unset, so **Stage 7 did not run**. A reachable local endpoint does not
satisfy the gate on its own, and treating it as satisfaction would misreport an optional stage as
executed.

활성화 변수가 설정되지 않았으므로 Stage 7은 실행되지 않았다. 로컬 엔드포인트가 접근
가능하다는 사실만으로는 게이트가 충족되지 않으며, 이를 충족으로 처리하면 선택 단계를
실행된 것처럼 잘못 보고하게 된다.

## Capability note / 역량 판단

Even had the variable been set, the locally available models are 0.5B–7B parameter instances. The
Stage 6 Devil's Advocate findings required reading a 2{,}298-line pilot harness, tracing a repair
callback's body, recognizing that a loader precondition made a reported ratio vacuous, and
following schema `const` declarations into generated prose. A 7B local instance is not a credible
independent verifier for findings of that kind, and reporting its agreement or disagreement as
cross-model verification would overstate the check.

The recommended activation for this manuscript is a frontier-class independent endpoint, which is
not configured in this environment.

## Effect on the pipeline / 파이프라인 영향

None. Stage 7 is optional, its findings are advisory, and Stage 8 proceeds from the Stage 6
reviewer reports directly. The three integrity findings that drive the revision were each
reproduced by direct inspection of the repository rather than accepted on a single reviewer's
authority, so the absence of cross-model verification does not leave them unchecked.

Stage 7은 선택 단계이며 결과는 자문 성격이다. 개정을 이끄는 세 무결성 지적은 모두 저장소를
직접 검사해 재현했으므로 교차 모델 검증 부재가 이를 미검증 상태로 남기지 않는다.
