class_name GoldenPathLayout
extends RefCounted

## Single owner of the golden-path interactable layout and the refusal
## next-affordance mapping shared by the playable slice (`game_3d.gd`) and the
## headless balance/archetype probe (`balance_probe_runner.gd`).
##
## Golden-path pacing at WALK_SPEED 4.2 m/s (straight-line, trigger-zone edge
## to trigger-zone edge; real times run slightly longer around props):
##   spawn(0,2) → Mira(3,11)        ≈  6.9 m ≈ 1.6 s
##   Mira → lens(-11,1)             ≈ 11.8 m ≈ 2.8 s
##   lens → mount(7,13.5)           ≈ 16.5 m ≈ 3.9 s   (longest leg, < 6 s)
##   mount → Mira                   overlap  ≈ 0.5 s   (zones adjoin)
##   Mira → tide marks(-8.5,15.5)   ≈  7.2 m ≈ 1.7 s
## Total pure walking ≈ 10–12 s across the 8–12 min episode target.
## Loop shape: S-center → NE → SW → NE → NW; no leg exceeds ~3.9 s and no
## revisit happens without a new commit in between (no dead backtracking).
## The sealed lighthouse_view sits at the NE rail on the mount→Mira return.

const SPAWN_POSITION := Vector3(0.0, 0.2, 2.0)


static func interactable_specs() -> Array:
	return [
		{
			"id": "mira",
			"name": "미라 선장",
			"prompt": "미라 선장에게 말 걸기",
			"position": Vector3(3.0, 1.0, 11.0),
			"radius": 2.6,
		},
		{
			"id": "lens_pickup",
			"name": "신호 렌즈",
			"prompt": "신호 렌즈 조사하기",
			# Prop sits past the dock edge (x=-11 vs planks ending at x=-9):
			# radius 2.8 leaves ≈0.6 m of standable trigger band on the planks
			# instead of the ≈5 cm sliver the old 2.2 radius allowed.
			"position": Vector3(-11.0, 1.0, 1.0),
			"radius": 2.8,
		},
		{
			"id": "lamp_mount",
			"name": "부두 신호등 거치대",
			"prompt": "거치대에 렌즈 설치 제안하기",
			"position": Vector3(7.0, 1.5, 13.5),
			"radius": 2.6,
		},
		{
			"id": "lighthouse_view",
			"name": "봉인된 등대",
			"prompt": "앞바다의 등대 관찰하기",
			# NE rail so it lies on the mount→Mira return leg; radius 2.6 keeps
			# it inside the rail band (W-002: observed, never entered).
			"position": Vector3(5.4, 1.0, 14.8),
			"radius": 2.6,
		},
		{
			"id": "tide_marks",
			"name": "조수 표식",
			"prompt": "조수 표식 살펴보기",
			"position": Vector3(-8.5, 0.6, 15.5),
			"radius": 2.6,
		},
	]


static func site_position(site_id: String) -> Vector3:
	if site_id == "spawn":
		return SPAWN_POSITION
	for spec in interactable_specs():
		if spec["id"] == site_id:
			return spec["position"]
	push_error("unknown golden-path site: %s" % site_id)
	return SPAWN_POSITION


static func walk_distance(from_site: String, to_site: String) -> float:
	# Straight-line XZ proxy between site anchors. This is a pacing estimate,
	# not a measured traversal (props, focus pauses, and reading add time).
	var from_position := site_position(from_site)
	var to_position := site_position(to_site)
	return Vector2(from_position.x, from_position.z).distance_to(
		Vector2(to_position.x, to_position.z)
	)


static func next_affordance(state: Dictionary, met_mira: bool) -> Dictionary:
	# One honest ordering from the committed snapshot (plus the presentation-only
	# met-Mira flag) to the next valid affordance. `game_3d.gd` renders these as
	# the "다음:" refusal line and the repair-hint blink target; the balance
	# probe records the same mapping for refusal-actionability measurement.
	var has_lens: bool = "signal_lens" in state["player"]["inventory"]
	var installed: bool = "signal_lens_installed" in state["facts"]
	var hint_known: bool = "tide_marks_hint" in state["facts"]
	if hint_known:
		return {"target_id": "tide_marks", "text": "서쪽 방파제의 조수 표식을 살펴보자."}
	if installed:
		return {"target_id": "mira", "text": "미라 선장에게 허가된 단서를 묻자."}
	if has_lens:
		return {"target_id": "lamp_mount", "text": "부두 신호등 거치대에 렌즈를 설치하자."}
	if not met_mira:
		return {"target_id": "mira", "text": "부두 끝의 미라 선장에게 말을 걸자."}
	return {"target_id": "lens_pickup", "text": "램프 상점에서 신호 렌즈를 회수하자."}
