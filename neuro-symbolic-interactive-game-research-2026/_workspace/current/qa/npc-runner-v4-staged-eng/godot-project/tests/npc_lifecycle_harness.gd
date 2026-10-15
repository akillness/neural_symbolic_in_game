extends SceneTree

const MAIN_SCENE := "res://scenes/main_3d.tscn"
func _init() -> void:
	var stale_game: Node = load(MAIN_SCENE).instantiate()
	root.add_child(stale_game)
	await process_frame
	await process_frame

	var initial: Dictionary = stale_game.npc_state_ref()
	stale_game._npc_waiting_action = {
		"operation": "acquire_object",
		"action_id": "stale-callback",
		"context": {
			"expected_revision": int(initial.get("revision", -1)),
			"expected_sha256": str(initial.get("sha256", "")),
		},
	}
	var mutation: Dictionary = stale_game.machine.apply_operation("acquire_object", {"object_id": "signal_lens"})
	var before_stale_writer: Dictionary = stale_game.npc_state_ref()
	stale_game._propose_acquire()
	var after_stale_writer: Dictionary = stale_game.npc_state_ref()
	var stale_blocked: bool = before_stale_writer == after_stale_writer and stale_game._npc_waiting_action.is_empty()
	stale_game.queue_free()
	await process_frame

	var cancel_game: Node = load(MAIN_SCENE).instantiate()
	root.add_child(cancel_game)
	await process_frame
	await process_frame
	var cancel_initial: Dictionary = cancel_game.npc_state_ref()
	cancel_game._npc_waiting_action = {
		"operation": "acquire_object",
		"action_id": "cancelled-directive",
		"context": {"expected_revision": int(cancel_initial.get("revision", -1))},
	}
	cancel_game._on_npc_cancel_requested()
	var before_ordinary: Dictionary = cancel_game.npc_state_ref()
	cancel_game._propose_acquire()
	var after_ordinary: Dictionary = cancel_game.npc_state_ref()
	var ordinary_applied: bool = int(after_ordinary.get("revision", -1)) > int(before_ordinary.get("revision", -1)) and bool(cancel_game.npc_public_observation().get("lens_carried", false))

	print(JSON.stringify({
		"mutation_accepted": bool(mutation.get("accepted", false)),
		"stale_blocked": stale_blocked,
		"ordinary_after_cancel_applied": ordinary_applied,
		"stale_state_ref": after_stale_writer,
		"ordinary_state_ref": after_ordinary,
	}))
	quit(0 if bool(mutation.get("accepted", false)) and stale_blocked and ordinary_applied else 1)
