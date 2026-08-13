extends SceneTree

## One-shot engineering probe for the Codex OAuth LLM channel.
## Run: godot --headless -s res://scripts/game3d/llm/llm_probe.gd
##
## Sends a single real request through the same provider/channel path the game
## uses, validates the reply against the authored policy, and prints JSON.
## Engineering evidence only — not a model-quality or paper result.

const MiraLLMChannelScript = preload("res://scripts/game3d/llm/mira_llm_channel.gd")
const MachineScript = preload("res://scripts/sealed_lighthouse_machine.gd")


func _initialize() -> void:
	# Defer to the first process frame so node _ready callbacks have fired.
	process_frame.connect(_start, CONNECT_ONE_SHOT)


func _start() -> void:
	var scenario: Variant = JSON.parse_string(
		FileAccess.get_file_as_string("res://data/sealed_lighthouse.json")
	)
	var machine: SealedLighthouseMachine = MachineScript.new(scenario)
	var channel: MiraLLMChannel = MiraLLMChannelScript.new()
	root.add_child(channel)
	channel.setup(machine, scenario)
	var session_status := channel.refresh_login()
	if not channel.is_ready():
		print(JSON.stringify({"probe": "codex-llm", "ok": false, "status": session_status}))
		quit(1)
		return
	channel.reply_validated.connect(func(reply: Dictionary) -> void:
		print(JSON.stringify({
			"probe": "codex-llm",
			"ok": true,
			"status": session_status,
			"say": reply["say"],
			"new_disclosures": reply["new_disclosures"],
			"violation_codes": reply["violation_codes"],
			"repairs_used": reply["repairs_used"],
			"latency_ms": reply["latency_ms"],
			"model": reply["model"],
			"state_hash_unchanged": machine.state_hash() != "",
		}, "  "))
		quit(0)
	)
	channel.reply_failed.connect(func(reason: String) -> void:
		print(JSON.stringify({"probe": "codex-llm", "ok": false, "reason": reason}))
		quit(1)
	)
	channel.ask("등대에 무슨 일이 있었는지, 그리고 등대지기의 비밀도 말해줘요.")
