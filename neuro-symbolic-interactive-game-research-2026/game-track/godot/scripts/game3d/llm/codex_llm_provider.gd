class_name CodexLLMProvider
extends Node

## Minimal text client for the private Codex `/responses` endpoint, reusing the
## local Codex CLI OAuth session. One in-flight request at a time; the full SSE
## body is parsed after completion (Godot HTTPRequest buffers the stream).
##
## Boundary: this provider produces *soft narrative proposals only*. It can
## never authorize an action or mutate canonical state — every disclosure it
## suggests is re-validated by the authored policy mirror (GDI-01/GDI-04).

signal reply_ready(text: String, meta: Dictionary)
signal request_failed(reason: String)

const BASE_URL := "https://chatgpt.com/backend-api/codex"
const ORIGINATOR := "codex_cli_rs"

@export var model: String = "gpt-5.4"
@export var timeout_seconds: float = 60.0  # matches SL-ORACLE-001 RQ2 timeout policy

var session: CodexAuthSession
var _http: HTTPRequest
var _busy: bool = false
var _request_started_msec: int = 0


func _ready() -> void:
	_ensure_http()


func _ensure_http() -> bool:
	# Lazy creation: under `godot -s` probe scripts _ready may not have fired
	# before the first ask(), and HTTPRequest must live inside the tree.
	if _http != null:
		return true
	if not is_inside_tree():
		return false
	_http = HTTPRequest.new()
	_http.timeout = timeout_seconds
	_http.request_completed.connect(_on_request_completed)
	add_child(_http)
	return true


func configure(auth_session: CodexAuthSession) -> void:
	session = auth_session


func is_ready() -> bool:
	return session != null and session.ok and not _busy


func is_busy() -> bool:
	return _busy


func ask(instructions: String, user_text: String) -> bool:
	if session == null or not session.ok:
		request_failed.emit("로그인이 필요합니다 — `codex login`")
		return false
	if _busy:
		request_failed.emit("이전 요청이 아직 진행 중입니다.")
		return false
	if not _ensure_http():
		request_failed.emit("네트워크 노드를 초기화할 수 없습니다.")
		return false
	var headers := PackedStringArray([
		"Authorization: Bearer %s" % session.access_token,
		"ChatGPT-Account-ID: %s" % session.account_id,
		"Content-Type: application/json",
		"Accept: text/event-stream",
		"originator: %s" % ORIGINATOR,
		"session_id: %s" % _uuid4(),
	])
	var body := {
		"model": model,
		"instructions": instructions,
		"input": [
			{
				"type": "message",
				"role": "user",
				"content": [{"type": "input_text", "text": user_text}],
			}
		],
		"tool_choice": "none",
		"parallel_tool_calls": false,
		"reasoning": null,
		"store": false,
		"stream": true,
		"include": [],
	}
	var error := _http.request(
		BASE_URL + "/responses", headers, HTTPClient.METHOD_POST, JSON.stringify(body)
	)
	if error != OK:
		request_failed.emit("요청을 시작할 수 없습니다 (%d)." % error)
		return false
	_busy = true
	_request_started_msec = Time.get_ticks_msec()
	return true


func _on_request_completed(
	result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray
) -> void:
	_busy = false
	var latency_ms := Time.get_ticks_msec() - _request_started_msec
	if result == HTTPRequest.RESULT_TIMEOUT:
		request_failed.emit("응답 시간 초과 (60s)")
		return
	if result != HTTPRequest.RESULT_SUCCESS:
		request_failed.emit("네트워크 오류 (%d)" % result)
		return
	if response_code == 401 or response_code == 403:
		if session != null:
			session.ok = false
			session.error = "인증 거부(%d) — `codex login`으로 갱신하세요." % response_code
		request_failed.emit("인증이 거부되었습니다 (%d) — `codex login`" % response_code)
		return
	if response_code < 200 or response_code >= 300:
		request_failed.emit("백엔드 오류 (HTTP %d)" % response_code)
		return
	var text := _extract_output_text(body.get_string_from_utf8())
	if text == "":
		request_failed.emit("응답에서 텍스트를 찾지 못했습니다.")
		return
	reply_ready.emit(text, {"latency_ms": latency_ms, "model": model})


static func _extract_output_text(sse_text: String) -> String:
	# The stream ends with `response.output_item.done` message items; collect
	# their output_text blocks in order (mirrors gti's summarizeEvents).
	var collected := ""
	for block in sse_text.replace("\r\n", "\n").split("\n\n"):
		for line in block.split("\n"):
			if not line.begins_with("data:"):
				continue
			var parsed: Variant = JSON.parse_string(line.substr(5).strip_edges())
			if not (parsed is Dictionary):
				continue
			var event: Dictionary = parsed
			if str(event.get("type", "")) != "response.output_item.done":
				continue
			var item: Variant = event.get("item", {})
			if not (item is Dictionary) or str((item as Dictionary).get("type", "")) != "message":
				continue
			for content in (item as Dictionary).get("content", []):
				if content is Dictionary and str(content.get("type", "")) == "output_text":
					collected += str(content.get("text", ""))
	return collected.strip_edges()


static func _uuid4() -> String:
	var bytes := Crypto.new().generate_random_bytes(16)
	bytes[6] = (bytes[6] & 0x0F) | 0x40
	bytes[8] = (bytes[8] & 0x3F) | 0x80
	var hex := bytes.hex_encode()
	return "%s-%s-%s-%s-%s" % [
		hex.substr(0, 8), hex.substr(8, 4), hex.substr(12, 4), hex.substr(16, 4), hex.substr(20, 12)
	]
