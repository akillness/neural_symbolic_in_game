class_name ProceduralAudioFeedback
extends Node

## Deterministic, asset-free presentation audio for the 3D slice.
##
## Streams are generated locally from fixed parameters, but playback stays
## locked until `unlock_from_gesture()` is called from a real input callback.
## This node never reads or writes canonical game state.

signal audio_unlocked
signal mute_changed(muted: bool)

const MIX_RATE := 22050
# Five pooled voices: four short-cue rotations plus headroom for the ~2.4 s
# thunder rumble to ring out under normal cue traffic. Streams stay generated.
const MAX_CUE_VOICES := 5
const AMBIENT_SECONDS := 6.0
const AMBIENT_SPLICE_SECONDS := 0.25
# Per-cue playback volumes (dB); anything absent falls back to -13.0.
const CUE_VOLUME_DB := {
	"step_0": -18.0,
	"step_1": -18.0,
	"focus": -16.0,
	"refusal": -14.0,
	"thunder": -16.0,
	"commit_3": -12.0,
	"ending": -10.0,
}
# Per-cue retrigger cooldowns (ms); default 45.
const CUE_COOLDOWN_MS := {
	"focus": 160,
	"thunder": 1200,
	"ending": 800,
}

var _ambient_player: AudioStreamPlayer
var _cue_players: Array[AudioStreamPlayer] = []
var _cue_streams: Dictionary = {}
var _next_voice: int = 0
var _unlocked: bool = false
var _muted: bool = false
var _last_cue_ms: Dictionary = {}


func _ready() -> void:
	_ambient_player = AudioStreamPlayer.new()
	_ambient_player.name = "ProceduralHarborAmbience"
	_ambient_player.volume_db = -30.0
	add_child(_ambient_player)
	for voice_index in range(MAX_CUE_VOICES):
		var voice := AudioStreamPlayer.new()
		voice.name = "ProceduralCueVoice%02d" % voice_index
		voice.volume_db = -13.0
		add_child(voice)
		_cue_players.append(voice)
	_build_streams()


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		if _ambient_player != null:
			_ambient_player.stop()
	elif what == NOTIFICATION_APPLICATION_FOCUS_IN:
		_resume_ambient_if_allowed()


func unlock_from_gesture() -> void:
	if _unlocked:
		_resume_ambient_if_allowed()
		return
	_unlocked = true
	audio_unlocked.emit()
	_resume_ambient_if_allowed()


func is_unlocked() -> bool:
	return _unlocked


func is_muted() -> bool:
	return _muted


func toggle_muted() -> bool:
	set_muted(not _muted)
	return _muted


func set_muted(muted: bool) -> void:
	if _muted == muted:
		return
	_muted = muted
	if _muted:
		_ambient_player.stop()
		for voice in _cue_players:
			voice.stop()
	else:
		_resume_ambient_if_allowed()
	mute_changed.emit(_muted)


func play_cue(cue_id: String, volume_offset_db: float = 0.0) -> void:
	if not _unlocked or _muted or not _cue_streams.has(cue_id):
		return
	var now_ms := Time.get_ticks_msec()
	var cooldown_ms: int = int(CUE_COOLDOWN_MS.get(cue_id, 45))
	if now_ms - int(_last_cue_ms.get(cue_id, -cooldown_ms)) < cooldown_ms:
		return
	_last_cue_ms[cue_id] = now_ms
	var voice := _cue_players[_next_voice]
	_next_voice = (_next_voice + 1) % _cue_players.size()
	voice.stop()
	voice.stream = _cue_streams[cue_id]
	voice.volume_db = float(CUE_VOLUME_DB.get(cue_id, -13.0)) + volume_offset_db
	voice.play()


func get_engineering_snapshot() -> Dictionary:
	return {
		"engineering_only": true,
		"claim_boundary": "Presentation audio instrumentation; not G4, immersion, usability, affect, or efficacy evidence.",
		"gesture_gated": true,
		"unlocked": _unlocked,
		"muted": _muted,
		"ambient_playing": _ambient_player != null and _ambient_player.playing,
		"mix_rate_hz": MIX_RATE,
		"max_cue_voices": MAX_CUE_VOICES,
		"generated_stream_count": _cue_streams.size() + 1,
		"external_audio_assets": [],
		"background_resume_policy": "ambient stops on focus-out and resumes only if gesture-unlocked and unmuted",
	}


func _resume_ambient_if_allowed() -> void:
	if (
		_ambient_player == null
		or not _unlocked
		or _muted
		or _ambient_player.playing
		or _ambient_player.stream == null
	):
		return
	_ambient_player.play()


func _build_streams() -> void:
	_ambient_player.stream = _make_ambient_stream()
	# Cue palette (all deterministic, all generated — no audio files):
	#   commit_1  gentle 2-note brass rise (G3→C4), the explained first commit
	#   commit_2  quicker, brighter rise (C4→E4) — confidence without ceremony
	#   commit_3  quickest rise + third note (E4→G4→C5), later-commit swagger
	#   refusal   soft low thud + damped minor third (G3+B♭3), non-alarming
	#   pickup    bright two-partial chime for the lens acquisition
	#   ending    3-note fanfare resolve (E4→G4→C5, longer tonic)
	#   thunder   low filtered-noise rumble for offshore lightning (delayed)
	_cue_streams = {
		"start": _make_tone_stream(0.42, [261.63, 392.00], 3.0, 0.018, 11),
		"focus": _make_tone_stream(0.075, [880.00], 16.0, 0.0, 17),
		"dialogue": _make_tone_stream(0.16, [329.63, 493.88], 8.0, 0.006, 23),
		"commit_1": _make_sequence_stream([
			{"at": 0.0, "freqs": [196.00], "gain": 0.40, "decay": 5.0},
			{"at": 0.16, "freqs": [261.63], "gain": 0.46, "decay": 3.6},
		], 0.62, 0.006, 31, true),
		"commit_2": _make_sequence_stream([
			{"at": 0.0, "freqs": [261.63], "gain": 0.42, "decay": 6.0},
			{"at": 0.11, "freqs": [329.63], "gain": 0.48, "decay": 4.4},
		], 0.48, 0.005, 37, true),
		"commit_3": _make_sequence_stream([
			{"at": 0.0, "freqs": [329.63], "gain": 0.42, "decay": 7.0},
			{"at": 0.08, "freqs": [392.00], "gain": 0.45, "decay": 6.0},
			{"at": 0.16, "freqs": [523.25], "gain": 0.50, "decay": 4.6},
		], 0.52, 0.005, 41, true),
		"refusal": _make_sequence_stream([
			{"at": 0.0, "freqs": [72.0, 98.0], "gain": 0.55, "decay": 11.0, "noise": 0.20},
			{"at": 0.12, "freqs": [196.00, 233.08], "gain": 0.30, "decay": 6.5},
		], 0.55, 0.0, 43, false),
		"pickup": _make_sequence_stream([
			{"at": 0.0, "freqs": [1046.50, 2093.00], "gain": 0.34, "decay": 9.0},
			{"at": 0.07, "freqs": [1318.51, 2637.02], "gain": 0.30, "decay": 7.5},
		], 0.42, 0.0, 47, false),
		"hint": _make_tone_stream(0.55, [392.00, 523.25, 659.25], 2.8, 0.010, 59),
		"ending": _make_sequence_stream([
			{"at": 0.0, "freqs": [329.63], "gain": 0.40, "decay": 4.0},
			{"at": 0.22, "freqs": [392.00], "gain": 0.44, "decay": 3.6},
			{"at": 0.44, "freqs": [523.25, 659.25], "gain": 0.52, "decay": 1.9},
		], 1.55, 0.004, 61, true),
		"thunder": _make_thunder_stream(2.4, 67),
		"step_0": _make_tone_stream(0.09, [92.50], 22.0, 0.10, 71),
		"step_1": _make_tone_stream(0.085, [103.83], 24.0, 0.09, 83),
	}


func _make_ambient_stream() -> AudioStreamWAV:
	var sample_count := int(AMBIENT_SECONDS * MIX_RATE)
	# Lapping-water layer: seeded low-pass filtered noise, spliced with a short
	# equal-power crossfade so the loop seam stays inaudible while the periodic
	# sine layers below join exactly (integer multiples of the loop period).
	var lap := PackedFloat32Array()
	lap.resize(sample_count)
	var lap_seed := 97
	var lap_low := 0.0
	var lap_mid := 0.0
	for sample_index in range(sample_count):
		lap_seed = int((lap_seed * 1103515245 + 12345) & 0x7fffffff)
		var white := (float(lap_seed) / 1073741824.0) - 1.0
		# Two cascaded one-pole low-passes ≈ gentle 300 Hz wash.
		lap_low += 0.082 * (white - lap_low)
		lap_mid += 0.082 * (lap_low - lap_mid)
		lap[sample_index] = lap_mid
	var splice_count := int(AMBIENT_SPLICE_SECONDS * MIX_RATE)
	for splice_index in range(splice_count):
		var weight := float(splice_index) / float(splice_count)
		var head := lap[splice_index]
		var tail := lap[sample_count - splice_count + splice_index]
		lap[splice_index] = head * sqrt(weight) + tail * sqrt(1.0 - weight)
	var bytes := PackedByteArray()
	bytes.resize(sample_count * 2)
	for sample_index in range(sample_count):
		var time := float(sample_index) / float(MIX_RATE)
		# Frequencies are integer multiples of the six-second loop period, so the
		# generated harbor bed joins without an asset seam or random-state click.
		var wind := (
			sin(TAU * (7.0 / AMBIENT_SECONDS) * time + 0.4)
			+ 0.55 * sin(TAU * (13.0 / AMBIENT_SECONDS) * time + 1.7)
			+ 0.32 * sin(TAU * (29.0 / AMBIENT_SECONDS) * time + 2.4)
			+ 0.18 * sin(TAU * (47.0 / AMBIENT_SECONDS) * time + 0.9)
		) / 2.05
		var swell := 0.56 + 0.24 * sin(TAU * time / AMBIENT_SECONDS - PI * 0.5)
		# Waves lap twice per loop, offset from the swell so the wash breathes.
		var lap_envelope := 0.35 + 0.65 * pow(
			0.5 + 0.5 * sin(TAU * 2.0 * time / AMBIENT_SECONDS + 1.1), 2.0
		)
		var water := lap[sample_index] * lap_envelope * 0.16
		var harbor_hum := sin(TAU * 43.0 * time) * 0.025
		var buoy_envelope := pow(maxf(0.0, sin(TAU * time / AMBIENT_SECONDS)), 8.0)
		var distant_buoy := sin(TAU * 175.0 * time) * buoy_envelope * 0.015
		var sample := clampf(
			wind * 0.07 * swell + water + harbor_hum + distant_buoy, -0.7, 0.7
		)
		bytes.encode_s16(sample_index * 2, int(round(sample * 32767.0)))
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = MIX_RATE
	stream.stereo = false
	stream.data = bytes
	stream.loop_begin = 0
	stream.loop_end = sample_count
	stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
	return stream


func _make_sequence_stream(
	notes: Array,
	duration: float,
	noise_amount: float,
	initial_seed: int,
	brassy: bool
) -> AudioStreamWAV:
	# Renders timed note events into one deterministic buffer. `brassy` adds a
	# soft odd-harmonic stack and a slower attack for the warm rise stingers.
	var sample_count := maxi(1, int(duration * MIX_RATE))
	var bytes := PackedByteArray()
	bytes.resize(sample_count * 2)
	var seed := initial_seed
	var attack_time := 0.022 if brassy else 0.006
	for sample_index in range(sample_count):
		var time := float(sample_index) / float(MIX_RATE)
		var mixed := 0.0
		for note in notes:
			var note_time: float = time - float(note["at"])
			if note_time < 0.0:
				continue
			var attack := minf(1.0, note_time / attack_time)
			var envelope := attack * exp(-float(note["decay"]) * note_time)
			var tonal := 0.0
			for frequency in note["freqs"]:
				tonal += sin(TAU * float(frequency) * note_time)
				if brassy:
					tonal += 0.34 * sin(TAU * float(frequency) * 2.0 * note_time)
					tonal += 0.12 * sin(TAU * float(frequency) * 3.0 * note_time)
			tonal /= maxf(1.0, float((note["freqs"] as Array).size()) * (1.46 if brassy else 1.0))
			var note_noise: float = float(note.get("noise", 0.0))
			if note_noise > 0.0 or noise_amount > 0.0:
				seed = int((seed * 1103515245 + 12345) & 0x7fffffff)
				var white := (float(seed) / 1073741824.0) - 1.0
				tonal += white * (note_noise + noise_amount)
			mixed += tonal * float(note["gain"]) * envelope
		bytes.encode_s16(sample_index * 2, int(round(clampf(mixed, -0.92, 0.92) * 32767.0)))
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = MIX_RATE
	stream.stereo = false
	stream.data = bytes
	stream.loop_mode = AudioStreamWAV.LOOP_DISABLED
	return stream


func _make_thunder_stream(duration: float, initial_seed: int) -> AudioStreamWAV:
	# Distant offshore rumble: cascaded low-passed noise with a slow bloom and
	# a long tail. Soft by construction — storm mood, never an alarm.
	var sample_count := maxi(1, int(duration * MIX_RATE))
	var bytes := PackedByteArray()
	bytes.resize(sample_count * 2)
	var seed := initial_seed
	var stage_a := 0.0
	var stage_b := 0.0
	var stage_c := 0.0
	for sample_index in range(sample_count):
		var time := float(sample_index) / float(MIX_RATE)
		seed = int((seed * 1103515245 + 12345) & 0x7fffffff)
		var white := (float(seed) / 1073741824.0) - 1.0
		# Three one-pole stages ≈ deep rumble below ~150 Hz.
		stage_a += 0.042 * (white - stage_a)
		stage_b += 0.042 * (stage_a - stage_b)
		stage_c += 0.042 * (stage_b - stage_c)
		var bloom := minf(1.0, time / 0.35)
		var tail := exp(-1.6 * maxf(0.0, time - 0.35))
		# A second, weaker roll keeps the rumble from reading as one thump.
		var roll := 0.72 + 0.28 * sin(TAU * 1.7 * time + 0.8)
		var sample := clampf(stage_c * 5.2 * bloom * tail * roll, -0.85, 0.85)
		bytes.encode_s16(sample_index * 2, int(round(sample * 32767.0)))
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = MIX_RATE
	stream.stereo = false
	stream.data = bytes
	stream.loop_mode = AudioStreamWAV.LOOP_DISABLED
	return stream


func _make_tone_stream(
	duration: float,
	frequencies: Array,
	decay: float,
	noise_amount: float,
	initial_seed: int
) -> AudioStreamWAV:
	var sample_count := maxi(1, int(duration * MIX_RATE))
	var bytes := PackedByteArray()
	bytes.resize(sample_count * 2)
	var seed := initial_seed
	for sample_index in range(sample_count):
		var time := float(sample_index) / float(MIX_RATE)
		var attack := minf(1.0, time / 0.008)
		var envelope := attack * exp(-decay * time)
		var tonal := 0.0
		for frequency in frequencies:
			tonal += sin(TAU * float(frequency) * time)
		tonal /= maxf(1.0, float(frequencies.size()))
		seed = int((seed * 1103515245 + 12345) & 0x7fffffff)
		var noise := (float(seed) / 1073741824.0) - 1.0
		var sample := clampf((tonal * 0.42 + noise * noise_amount) * envelope, -0.92, 0.92)
		bytes.encode_s16(sample_index * 2, int(round(sample * 32767.0)))
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = MIX_RATE
	stream.stereo = false
	stream.data = bytes
	stream.loop_mode = AudioStreamWAV.LOOP_DISABLED
	return stream
