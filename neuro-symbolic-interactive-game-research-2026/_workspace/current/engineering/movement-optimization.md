# Movement optimization / 이동 최적화

Run ID: `20260813-sealed-lighthouse-cycle-3`
Status: `[OBSERVED structure] playable 3D locomotion implemented; browser input latency unmeasured`

## Current movement surface

`game-track/godot/scripts/game3d/player_3d.gd` implements a third-person
`CharacterBody3D` presentation controller for `scenes/main_3d.tscn`:

| Concern | Implemented structure | Claim boundary |
|---|---|---|
| Translation | physical `W/A/S/D`, `WALK_SPEED=4.2`, acceleration `10.0`, gravity `18.0`, `move_and_slide()` | no human handling/usability result |
| Camera | `SpringArm3D` length `5.2`, FOV `62`, clamped pitch, captured-mouse look | no browser input-latency result |
| Resolution stability | mouse look uses `InputEventMouseMotion.screen_relative` | static implementation observation only |
| Focus | nearest enabled `Interactable3D` inside its authored sphere radius | focus readability remains human/browser QA |
| Interaction | `[E]` emits `interact_requested(interaction_id)` | signal cannot write canonical state directly |
| Footsteps | distance-paced request every `1.65` moved units | procedural audio feedback only |
| Browser entry | start button captures pointer and unlocks audio from the same user gesture; `Esc` releases and click recaptures | clean-browser execution still required |

## Hard boundary

Movement, camera, focus, footsteps, and interaction markers are presentation. Every world-changing
intent is emitted to `game_3d.gd`, converted into a proposal, and committed only through
`SealedLighthouseMachine.apply_operation` after hard validation. Locomotion never changes quest,
fact, inventory, disclosure, relationship, or research state directly.

## Optimization posture

- Physics remains one kinematic player and static authored collision surfaces; decorative repeated
  harbor meshes use instancing and no decorative collision.
- Focus uses the small `sl_interactables` group rather than a world-wide physics query.
- Mouse movement is ignored unless the pointer is captured; movement is disabled in smoke,
  evaluation, and screenshot modes.
- Footstep sound generation is event-paced by distance, not emitted every physics frame.

[TARGET] Before G6 can change, measure warmed input-to-visible feedback, long-frame rate, and memory
in a real Web session. The current public-safe smoke `8/8` proves authored state-path conformance,
not movement feel or input performance.
