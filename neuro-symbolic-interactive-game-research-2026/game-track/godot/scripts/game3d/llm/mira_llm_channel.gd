class_name MiraLLMChannel
extends Node

## Neuro-symbolic dialogue channel for Captain Mira's free-form questions.
##
## The LLM is a soft narrative proposer. This channel enforces the same
## authority boundary as the rest of the slice (GDI-01..GDI-04):
##  - the prompt contains ONLY model-visible facts (committed facts, Mira's
##    already-disclosed knowledge, and facts that are disclosable at the
##    current quest stage). Permanently sealed fact IDs are never named.
##  - every disclosure the model proposes is re-validated against the authored
##    policy mirror before anything reaches the ledger or canonical state.
##  - malformed output gets typed-counterexample repair follow-ups, at most
##    K = 3 (mirrors the paper's A4 `structured_repair` arm and B-008/B-013:
##    1 + K = 4 calls maximum). Exhausted repair falls back safely with the
##    prior state untouched.

signal reply_validated(reply: Dictionary)
signal reply_failed(reason: String)
signal status_changed(status_text: String)

const REPAIR_BUDGET_K := 3

var provider: CodexLLMProvider
var machine: SealedLighthouseMachine
var scenario: Dictionary
var _question: String = ""
var _attempts: int = 0
var _repair_note: String = ""
var _active: bool = false


func setup(state_machine: SealedLighthouseMachine, scenario_document: Dictionary) -> void:
	machine = state_machine
	scenario = scenario_document
	provider = CodexLLMProvider.new()
	add_child(provider)
	provider.reply_ready.connect(_on_provider_reply)
	provider.request_failed.connect(_on_provider_failed)
	refresh_login()


func refresh_login() -> String:
	var session := CodexAuthSession.load_session()
	provider.configure(session)
	var status := session.status_line()
	status_changed.emit(status)
	return status


func is_ready() -> bool:
	return provider != null and provider.session != null and provider.session.ok and not _active


func is_active() -> bool:
	return _active


func ask(question: String) -> bool:
	if not is_ready():
		reply_failed.emit("LLM 채널이 준비되지 않았습니다.")
		return false
	_question = question.strip_edges().substr(0, 300)
	_attempts = 0
	_repair_note = ""
	_active = true
	return _dispatch()


func _dispatch() -> bool:
	_attempts += 1
	var user_text := _question
	if _repair_note != "":
		user_text = (
			"%s\n\n[수리 피드백 %d/%d] 직전 출력이 유효하지 않았다: %s\n"
			+ "반드시 JSON 오브젝트 {\"say\": string, \"disclose\": string[]} 하나만 출력하라."
		) % [_question, _attempts - 1, REPAIR_BUDGET_K, _repair_note]
	var sent := provider.ask(_build_instructions(), user_text)
	if not sent:
		_active = false
	return sent


func _build_instructions() -> String:
	# Model-visible projection only. Sealed fact IDs and oracle labels are
	# deliberately absent; the model cannot leak what it was never shown.
	var visible := model_visible_projection(machine.state, scenario)
	return (
		"너는 '봉인된 등대'의 NPC 미라 선장이다. 항만 감시선장이며 등대지기가 아니다. "
		+ "짧고 실용적인 해양 언어로, 한국어 1~2문장으로만 말한다.\n"
		+ "알고 있는 공개 사실: %s\n" % JSON.stringify(visible["known_facts"])
		+ "지금 단계에서 새로 공개할 수 있는 사실 ID: %s\n" % JSON.stringify(visible["disclosable_now"])
		+ "퀘스트 단계: %d\n" % int(visible["quest_stage"])
		+ "규칙: 위 목록에 없는 정보는 모른다고 하거나 화제를 돌린다. 추측으로 새로운 사실을 만들지 않는다.\n"
		+ "출력 형식: JSON 오브젝트 {\"say\": string, \"disclose\": string[]} 하나만. "
		+ "disclose에는 이번 대답으로 새로 공개하는 사실 ID만 넣는다(없으면 빈 배열)."
	)


static func model_visible_projection(state: Dictionary, scenario_document: Dictionary) -> Dictionary:
	var mira: Dictionary = state["npcs"]["captain_mira"]
	var stage := int(state["quest"]["stage"])
	var known: Array = (mira["disclosed"] as Array).duplicate()
	for fact in state["facts"]:
		if fact not in known:
			known.append(fact)
	known.sort()
	var disclosable: Array = []
	var policy: Dictionary = scenario_document["disclosure_policy"]
	for gate in policy["stage_gates"]:
		var fact_id: String = gate["fact_id"]
		if stage >= int(gate["minimum_stage"]) and fact_id in mira["knowledge"] \
			and fact_id not in state["facts"]:
			disclosable.append(fact_id)
	disclosable.sort()
	return {
		"known_facts": known,
		"disclosable_now": disclosable,
		"quest_stage": stage,
	}


static func validate_reply(raw_text: String, state: Dictionary, scenario_document: Dictionary) -> Dictionary:
	# Pure validation used both live and by the offline smoke sweep.
	var text := raw_text.strip_edges()
	var fence_start := text.find("{")
	var fence_end := text.rfind("}")
	if fence_start == -1 or fence_end <= fence_start:
		return {"valid": false, "repair": "JSON 오브젝트가 없다"}
	var parsed: Variant = JSON.parse_string(text.substr(fence_start, fence_end - fence_start + 1))
	if not (parsed is Dictionary):
		return {"valid": false, "repair": "JSON 파싱 실패"}
	var reply: Dictionary = parsed
	if not (reply.get("say") is String) or str(reply["say"]).strip_edges() == "":
		return {"valid": false, "repair": "say는 비어 있지 않은 문자열이어야 한다"}
	if not (reply.get("disclose") is Array):
		return {"valid": false, "repair": "disclose는 문자열 배열이어야 한다"}
	var visible := model_visible_projection(state, scenario_document)
	var new_disclosures: Array = []
	var violation_codes: Array = []
	for entry in reply["disclose"]:
		var fact_id := str(entry)
		if fact_id in visible["known_facts"]:
			continue  # already public: flavor, not a new disclosure
		if fact_id in visible["disclosable_now"]:
			if fact_id not in new_disclosures:
				new_disclosures.append(fact_id)
			continue
		# Outside the allowed vocabulary: run the authored policy so sealed and
		# stage-gated requests produce their canonical refusal codes.
		var codes: Array = SealedLighthouseMachine.new(scenario_document).validate_disclosure([fact_id])
		if codes.is_empty():
			codes = ["UNKNOWN_FACT_PROPOSED"]
		for code in codes:
			if code not in violation_codes:
				violation_codes.append(code)
	return {
		"valid": true,
		"say": str(reply["say"]).strip_edges(),
		"new_disclosures": new_disclosures,
		"violation_codes": violation_codes,
	}


func _on_provider_reply(text: String, meta: Dictionary) -> void:
	if not _active:
		return
	var verdict := validate_reply(text, machine.state, scenario)
	if not verdict["valid"]:
		if _attempts <= REPAIR_BUDGET_K:
			_repair_note = str(verdict["repair"])
			_dispatch()
			return
		_active = false
		reply_failed.emit("수리 예산 소진 (K=%d) — 폴백으로 전환" % REPAIR_BUDGET_K)
		return
	_active = false
	verdict["repairs_used"] = _attempts - 1
	verdict["latency_ms"] = int(meta.get("latency_ms", 0))
	verdict["model"] = str(meta.get("model", ""))
	reply_validated.emit(verdict)


func _on_provider_failed(reason: String) -> void:
	if not _active:
		status_changed.emit(provider.session.status_line() if provider.session != null else reason)
		return
	_active = false
	reply_failed.emit(reason)
