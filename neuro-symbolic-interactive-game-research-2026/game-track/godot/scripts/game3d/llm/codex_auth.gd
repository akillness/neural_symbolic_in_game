class_name CodexAuthSession
extends RefCounted

## Read-only view of the local Codex CLI OAuth session (`~/.codex/auth.json`).
##
## The game never performs the OAuth dance itself and never writes or logs
## tokens: login/refresh stays owned by `codex login`. This mirrors the
## god-tibo-imagen session contract (access_token + account_id headers against
## the private `chatgpt.com/backend-api/codex` path) and shares its limitation:
## the backend is unsupported and optional. The core game must stay fully
## playable without it (see repository rule: no runtime dependency on the
## private backend).

var ok: bool = false
var error: String = ""
var auth_mode: String = ""
var access_token: String = ""
var account_id: String = ""
var last_refresh: String = ""
var expires_at_unix: int = 0


static func auth_file_path() -> String:
	var home := OS.get_environment("CODEX_HOME")
	if home == "":
		home = OS.get_environment("HOME").path_join(".codex")
	return home.path_join("auth.json")


static func load_session() -> CodexAuthSession:
	var session := CodexAuthSession.new()
	var path := auth_file_path()
	if not FileAccess.file_exists(path):
		session.error = "auth.json 없음 — 터미널에서 `codex login`을 실행하세요."
		return session
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not (parsed is Dictionary):
		session.error = "auth.json을 읽을 수 없습니다."
		return session
	var document: Dictionary = parsed
	session.auth_mode = str(document.get("auth_mode", ""))
	session.last_refresh = str(document.get("last_refresh", ""))
	var tokens: Variant = document.get("tokens", {})
	if not (tokens is Dictionary):
		session.error = "auth.json에 tokens 블록이 없습니다."
		return session
	session.access_token = str(tokens.get("access_token", ""))
	session.account_id = str(tokens.get("account_id", ""))
	if session.access_token == "" or session.account_id == "":
		session.error = "토큰이 비어 있습니다 — `codex login`으로 다시 로그인하세요."
		return session
	session.expires_at_unix = _jwt_expiry(session.access_token)
	if session.is_expired():
		session.error = "토큰이 만료되었습니다 — `codex login`으로 갱신하세요."
		return session
	session.ok = true
	return session


func is_expired() -> bool:
	if expires_at_unix <= 0:
		return false
	return Time.get_unix_time_from_system() >= float(expires_at_unix - 60)


func status_line() -> String:
	if not ok:
		return "LLM 오프라인 — " + error
	var summary := account_id.substr(0, 8) + "…" if account_id.length() > 8 else account_id
	return "LLM 연결됨 — Codex OAuth (%s)" % summary


static func _jwt_expiry(token: String) -> int:
	var parts := token.split(".")
	if parts.size() < 2:
		return 0
	var payload := parts[1].replace("-", "+").replace("_", "/")
	while payload.length() % 4 != 0:
		payload += "="
	var raw := Marshalls.base64_to_raw(payload)
	if raw.is_empty():
		return 0
	var decoded: Variant = JSON.parse_string(raw.get_string_from_utf8())
	if decoded is Dictionary and (decoded as Dictionary).has("exp"):
		return int((decoded as Dictionary)["exp"])
	return 0
