"""Original-commit sources for strict, historical-only NPC evidence validation."""

import io
import subprocess
import tarfile
from pathlib import Path


def archive_historical_npc_sources(project_root: Path, destination: Path) -> None:
    """Read fa9fb8a without changing the checkout or rewriting evidence receipts."""
    archive = subprocess.run(
        [
            "git",
            "archive",
            "--format=tar",
            "fa9fb8a",
            f"{project_root.name}/configs/npc-goal-recovery.json",
            f"{project_root.name}/game-track/godot/project.godot",
            f"{project_root.name}/game-track/schemas/npc-goal-recovery.schema.json",
            f"{project_root.name}/data/fixtures/npc-goal-recovery/validated-v5",
            f"{project_root.name}/src/nesy_game/npc_goal.py",
            f"{project_root.name}/scripts/codex_oauth_llm.py",
            f"{project_root.name}/scripts/run_npc_goal_experiment.py",
            f"{project_root.name}/game-track/godot/scripts/game3d/game_3d.gd",
            f"{project_root.name}/game-track/godot/scripts/game3d/npc_agent_client.gd",
            f"{project_root.name}/game-track/godot/scripts/sealed_lighthouse_machine.gd",
            f"{project_root.name}/game-track/godot/scripts/canonical_state.gd",
            f"{project_root.name}/game-track/godot/data/npc-goal-recovery.json",
            f"{project_root.name}/game-track/godot/data/sealed_lighthouse.json",
            f"{project_root.name}/game-track/godot/scenes/main_3d.tscn",
        ],
        cwd=project_root.parent,
        check=True,
        capture_output=True,
    ).stdout
    prefix = f"{project_root.name}/"
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        for member in tar.getmembers():
            if not member.name.startswith(prefix) or member.name == prefix:
                continue
            target = destination / member.name[len(prefix) :]
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                extracted = tar.extractfile(member)
                assert extracted is not None
                target.write_bytes(extracted.read())
