import hashlib
import json
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
