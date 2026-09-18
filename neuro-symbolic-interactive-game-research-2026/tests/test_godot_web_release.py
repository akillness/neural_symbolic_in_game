import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
GODOT_PROJECT = ROOT / "game-track" / "godot"
WEB_ROOT = ROOT / "game-track" / "web"


def test_web_release_preserves_the_research_default_scene() -> None:
    project = (GODOT_PROJECT / "project.godot").read_text(encoding="utf-8")
    builder = (ROOT / "scripts" / "build_godot_web.sh").read_text(encoding="utf-8")

    assert 'run/main_scene="res://scenes/headless.tscn"' in project
    assert 'run/main_scene="res://scenes/main_3d.tscn"' not in project
    assert "STAGED_PROJECT" in builder
    assert 'run/main_scene="res://scenes/main_3d.tscn"' in builder
    assert "--exclude 'scripts/game3d/llm/'" in builder
    assert "run_godot_checked" in builder
    assert "SCRIPT ERROR" in builder
    assert "System/Library/Fonts" in builder
    assert "get_system_ca_certificates" in builder
    assert 'python3 "$PROJECT_ROOT/scripts/validate_player_asset.py"' in builder

    runtime_sources = "\n".join(
        path.read_text(encoding="utf-8") for path in GODOT_PROJECT.rglob("*.gd")
    )
    for fragment in (
        "auth.json",
        "access_token",
        "Authorization: Bearer",
        "ChatGPT-Account-ID",
        "chatgpt.com/backend-api/codex",
    ):
        assert fragment not in runtime_sources
    assert not (GODOT_PROJECT / "scripts" / "game3d" / "llm").exists()
    controller_and_ui = "\n".join(
        (GODOT_PROJECT / "scripts" / "game3d" / name).read_text(encoding="utf-8")
        for name in ("game_3d.gd", "harbor_ledger_ui.gd")
    )
    for hook in ("MiraLLM", "sl_llm", "free_question", "set_llm_status", "llm_channel"):
        assert hook not in controller_and_ui

    model_root = GODOT_PROJECT / "assets" / "models"
    model_manifest = json.loads((model_root / "models-manifest.json").read_text(encoding="utf-8"))
    assert model_manifest["generator"] == "blender-procedural"
    assert model_manifest["ai_generated_content"] is False
    assert model_manifest["generation_script_retained"] is False
    assert model_manifest["third_party_inputs"] == []
    assert len(model_manifest["assets"]) == 5
    for filename, receipt in model_manifest["assets"].items():
        model_path = model_root / filename
        assert model_path.stat().st_size == receipt["bytes"]
        assert hashlib.sha256(model_path.read_bytes()).hexdigest() == receipt["sha256"]


def test_web_preset_is_single_threaded_and_includes_authored_json() -> None:
    preset = (WEB_ROOT / "export_presets.cfg").read_text(encoding="utf-8")

    assert 'platform="Web"' in preset
    assert 'include_filter="data/*.json"' in preset
    assert 'exclude_filter="docs/latest/**"' in preset
    assert "variant/thread_support=false" in preset
    assert "variant/extensions_support=false" in preset
    assert "vram_texture_compression/for_mobile=false" in preset


def test_web_release_exposes_the_bundled_font_license() -> None:
    builder = (ROOT / "scripts" / "build_godot_web.sh").read_text(encoding="utf-8")
    license_path = GODOT_PROJECT / "assets" / "fonts" / "OFL.txt"

    assert license_path.is_file()
    assert '"$GODOT_PROJECT/assets/fonts/OFL.txt"' in builder
    assert '"$STAGED_OUTPUT/NanumGothic-OFL.txt"' in builder


def test_vercel_config_does_not_claim_unneeded_cross_origin_isolation() -> None:
    config = (WEB_ROOT / "vercel.json").read_text(encoding="utf-8")

    assert "Cross-Origin-Opener-Policy" not in config
    assert "Cross-Origin-Embedder-Policy" not in config
    assert "X-Content-Type-Options" in config


def test_dashboard_reference_matches_engine_gate_codes_and_links_papers() -> None:
    game = (GODOT_PROJECT / "scripts" / "game3d" / "game_3d.gd").read_text(encoding="utf-8")
    mapping_body = game.split("const GATE_BY_CODE := {", 1)[1].split("}\n", 1)[0]
    gate_by_code = dict(re.findall(r'"([A-Z][A-Z0-9_]+)":\s*"([A-Z/ ]+)"', mapping_body))
    reference = json.loads(
        (WEB_ROOT / "dashboard" / "paper-reference.json").read_text(encoding="utf-8")
    )

    reference_pairs = {
        (code, predicate["family"])
        for predicate in reference["paper_predicates"]
        for code in predicate["engine_codes"]
    }
    engine_pairs = {
        (code, family) for code, gate in gate_by_code.items() for family in gate.split("/")
    }
    assert reference_pairs == engine_pairs

    html = (WEB_ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
    assert 'href="/paper/en.pdf"' in html
    assert 'href="/paper/ko.pdf"' in html


def test_dashboard_renders_the_engine_trace_contract_not_a_schematic() -> None:
    # D-073: the commit-gate card is a per-node evaluation trace driven by the
    # engine's payload.trace (family_states has no default state); the old
    # "schematic" disclaimer must not survive anywhere in the served dashboard.
    dashboard = WEB_ROOT / "dashboard"
    html = (dashboard / "index.html").read_text(encoding="utf-8")
    script = (dashboard / "dashboard.js").read_text(encoding="utf-8")
    game = (GODOT_PROJECT / "scripts" / "game3d" / "game_3d.gd").read_text(encoding="utf-8")

    for text in (html, script):
        assert "not a per-node evaluation trace" not in text
        assert "paper pipeline diagram" not in text
    assert "Commit gate - live per-node evaluation trace" in html
    assert 'id="legend-rows"' in html and 'id="last-trace"' in html
    assert "This is engineering demonstration, not efficacy or" in html

    for field in (
        "family_states",
        "evaluated_gates",
        "held_at",
        "short_circuit",
        "skipped",
        "out_of_scope",
    ):
        assert f'"{field}"' in game
        assert field in script
    assert "legacy: schema-only" in script
    assert 'id: "hatch-oos"' in script
    assert "== short-circuit here: remaining in-scope checks were not run ==" in script
    assert "This is a per-proposal evaluation trace, not a schematic." in script


def test_public_play_recovers_from_falling_outside_the_dock() -> None:
    player = (GODOT_PROJECT / "scripts/game3d/player_3d.gd").read_text(encoding="utf-8")
    controller = (GODOT_PROJECT / "scripts/game3d/game_3d.gd").read_text(encoding="utf-8")

    assert "FALL_RECOVERY_Y" in player
    assert "FALL_RECOVERY_POSITION" in player
    assert "fall_recovered.emit()" in player
    assert "recover_from_fall_if_needed()" in player
    assert "presentation_sync_and_fall_recovery" in controller
    assert "machine.state_hash() == state_before_fall" in controller


def test_public_player_asset_is_curated_and_animation_bound() -> None:
    player = (GODOT_PROJECT / "scripts/game3d/player_3d.gd").read_text(encoding="utf-8")
    builder = (GODOT_PROJECT / "scripts/game3d/world_builder.gd").read_text(encoding="utf-8")

    assert 'TRACKED_PLAYER_RIG_PATH := "res://assets/player/higgsfield-player.glb"' in builder
    assert "movement_state_changed.connect(_on_movement_state_changed)" in player
    assert 'RIG_IDLE_ANIMATION := &"Idle"' in player
    assert 'RIG_WALK_ANIMATION := &"Casual_Walk"' in player
    assert "_play_rig_animation(active, motion_reduced)" in player
    assert '"player_rig_engine_animation"' in player
    assert '"player_rig_animation_playing"' in player

    provenance = json.loads(
        (GODOT_PROJECT / "assets/player/higgsfield-player.glb.provenance.json").read_text()
    )
    assert any(
        source.get("url") == "https://higgsfield.ai/terms-of-use-agreement"
        and source.get("section") == "4.4"
        for source in provenance["rights_sources"]
    )

    runtime_literals = []
    for script_path in (GODOT_PROJECT / "scripts" / "game3d").glob("*.gd"):
        source = script_path.read_text(encoding="utf-8")
        source_without_shaders = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
        runtime_literals.extend(re.findall(r'"(?:\\.|[^"\\])*"', source_without_shaders))
    assert runtime_literals
    assert all(literal.isascii() for literal in runtime_literals)

    validator = ROOT / "scripts" / "validate_player_asset.py"
    namespace: dict[str, object] = {
        "__file__": str(validator),
        "__name__": "validate_player_asset",
    }
    exec(  # noqa: S102 - execute the checked-in validator in an isolated namespace.
        compile(validator.read_text(encoding="utf-8"), str(validator), "exec"), namespace
    )
    assert namespace["main"]() == 0
