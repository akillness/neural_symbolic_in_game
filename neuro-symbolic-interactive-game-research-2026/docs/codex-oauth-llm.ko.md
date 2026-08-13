# 로컬 Codex OAuth LLM 컴패니언

이 선택 기능은 인증과 모델 실행을 공식 Codex CLI에 위임한다. 별도 브라우저 OAuth client를
구현하거나 API key를 노출하지 않으며 Godot/Vercel 빌드에도 인증 기능을 포함하지 않는다.
OpenAI 공식 문서는 headless 환경 또는 localhost callback이 막힌 환경에서 device-code 인증을
권장하고, 활성 인증 방식 확인에는 `codex login status`를 안내한다:
[Codex 인증](https://developers.openai.com/codex/auth/).

## 경계

- `login`은 terminal stream을 그대로 상속해 정확히 `codex login --device-auth`를 실행한다.
  일회용 URL/code는 공식 CLI가 화면에 표시하며 wrapper는 이를 캡처하거나 기록하지 않는다.
- `status`는 `codex login status` 결과를 비밀정보가 없는 JSON 상태로만 투영한다. Codex credential
  파일을 직접 읽지 않는다.
- `prompt`는 ChatGPT 인증 상태만 허용하고, 빈 임시 디렉터리에서 `codex exec`를
  `--ephemeral`, `--sandbox read-only`, 명시적 output schema, project rule 무시, session 비저장
  조건으로 실행한다.
- 성공 결과는 항상 `candidate_soft_proposal_only`, `authorization_effect: none`,
  `canonical_state_mutated: false`, `hard_validation_required: true`를 포함한다.
- 이 경로는 hard policy writer를 호출하거나 game action을 commit하거나 정식 상태를 수정하거나
  연구 근거를 만들지 않는다. game action으로 사용할 후보는 별도 결정론적 hard validator를
  통과해야 한다.

이 명령을 공개 Web endpoint로 노출하지 않는다. OpenAI 공식 문서도 신뢰할 수 없거나 공개된
환경에 Codex 실행을 노출하지 말라고 경고한다.

## 사용법

```bash
# 로그인이 필요할 때만 실행하는 공식 대화형 device-code 흐름
python3 scripts/codex_oauth_llm.py login

# 기계 판독 JSON. ChatGPT OAuth prompt 준비 상태일 때만 exit 0
python3 scripts/codex_oauth_llm.py status

# request ID가 출력과 동일한지 다시 검사하는 격리 소프트 제안
python3 scripts/codex_oauth_llm.py prompt \
  --request-id scene-dialogue:001 \
  "항구 관리인의 짧은 응답을 제안해 줘."

# 명시적으로만 수행하는 live smoke. 서비스에 접속하며 계정 quota를 사용할 수 있음
python3 scripts/codex_oauth_llm.py smoke --request-id oauth-smoke:001
```

계정에서 정확한 모델 사용 권한이 확인된 경우에만 `--model <model>`을 사용한다. 생략하면 설치된
Codex CLI가 모델을 선택한다. 정적 검증은 로그인이나 네트워크 호출을 수행하지 않는다.

```bash
./scripts/validate_codex_oauth_llm.sh
```
