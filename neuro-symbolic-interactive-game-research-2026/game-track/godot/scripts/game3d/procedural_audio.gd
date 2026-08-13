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
const MAX_CUE_VOICES := 4
const AMBIENT_SECONDS := 6.0

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


func play_cue(cue_id: String) -> void:
	if not _unlocked or _muted or not _cue_streams.has(cue_id):
		return
	var now_ms := Time.get_ticks_msec()
	var cooldown_ms := 160 if cue_id == "focus" else 45
	if now_ms - int(_last_cue_ms.get(cue_id, -cooldown_ms)) < cooldown_ms:
		return
	_last_cue_ms[cue_id] = now_ms
	var voice := _cue_players[_next_voice]
	_next_voice = (_next_voice + 1) % _cue_players.size()
	voice.stop()
	voice.stream = _cue_streams[cue_id]
	voice.volume_db = -18.0 if cue_id.begins_with("step") else -13.0
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
	_cue_streams = {
		"start": _make_tone_stream(0.42, [261.63, 392.00], 3.0, 0.018, 11),
		"focus": _make_tone_stream(0.075, [880.00], 16.0, 0.0, 17),
		"dialogue": _make_tone_stream(0.16, [329.63, 493.88], 8.0, 0.006, 23),
		"commit": _make_tone_stream(0.34, [523.25, 659.25, 783.99], 4.0, 0.008, 31),
		"refusal": _make_tone_stream(0.30, [196.00, 146.83], 5.5, 0.025, 43),
		"hint": _make_tone_stream(0.55, [392.00, 523.25, 659.25], 2.8, 0.010, 59),
		"step_0": _make_tone_stream(0.09, [92.50], 22.0, 0.10, 71),
		"step_1": _make_tone_stream(0.085, [103.83], 24.0, 0.09, 83),
	}


func _make_ambient_stream() -> AudioStreamWAV:
	var sample_count := int(AMBIENT_SECONDS * MIX_RATE)
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
		var harbor_hum := sin(TAU * 43.0 * time) * 0.025
		var buoy_envelope := pow(maxf(0.0, sin(TAU * time / AMBIENT_SECONDS)), 8.0)
		var distant_buoy := sin(TAU * 175.0 * time) * buoy_envelope * 0.015
		var sample := clampf(wind * 0.07 * swell + harbor_hum + distant_buoy, -0.7, 0.7)
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
