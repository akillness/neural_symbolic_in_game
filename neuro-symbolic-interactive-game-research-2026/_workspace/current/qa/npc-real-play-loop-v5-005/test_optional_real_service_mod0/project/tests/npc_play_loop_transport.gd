extends "res://scripts/game3d/npc_agent_client.gd"

## Test-only transport seam. It preserves the production envelope, HTTPRequest,
## validation, and signal flow while injecting an ephemeral endpoint when set.
signal request_sent(path: String, envelope: Dictionary)
var requests: Array[Dictionary] = []
var endpoint: String = ""
var transport_mode: String = ""

func setup(game: Node, ui: Node) -> void:
	super.setup(game, ui)
	endpoint = OS.get_environment("NPC_PLAY_LOOP_ENDPOINT").strip_edges()
	transport_mode = "injected_fake_http" if not endpoint.is_empty() else "production_super_send"

func _send(path: String, envelope: Dictionary) -> bool:
	request_sent.emit(path, envelope)
	if path == "/npc/step":
		requests.append({
			"path": path,
			"event_kind": str(envelope.get("body", {}).get("event_kind", "")),
			"session_epoch": int(envelope.get("session_epoch", -1)),
			"request_id": str(envelope.get("request_id", "")),
			"raw_utterance_sha256": str(envelope.get("provenance", {}).get("raw_utterance_sha256", "")),
		})
	if endpoint.is_empty():
		return super._send(path, envelope)
	var payload := JSON.stringify(envelope)
	var headers := PackedStringArray(["Content-Type: application/json", "X-NPC-Capability: Bearer " + _capability])
	var error := _http.request(endpoint + path, headers, HTTPClient.METHOD_POST, payload)
	if error != OK:
		protocol_error.emit("REQUEST_ERROR_%s" % error)
		return false
	return true
