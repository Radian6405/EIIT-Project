import time
import config

# FluidSynth configuration
SOUNDFONT = "soundfonts/SalC5Light2.sf2"
try:
    from fluidsynth import Synth
except Exception as e:
    raise ImportError(
        "fluidsynth is required for this script. Install with: pip install pyfluidsynth\n"
        f"Original error: {e}"
    )

# Initialize FluidSynth
synth = Synth()
try:
    synth.start()
except Exception as e:
    synth.delete()
    raise RuntimeError(f"Failed to start FluidSynth audio driver: {e}")

# Load soundfont
try:
    sfid = synth.sfload(SOUNDFONT)
    synth.program_select(0, sfid, 0, 0)  # use channel 0, bank 0, preset 0
except Exception as e:
    synth.delete()
    raise RuntimeError(f"Failed to load SoundFont '{SOUNDFONT}': {e}")

# Runtime global state
active_channels = {}
playing_notes = set()
sustain_mode = False
note_release_times = {}

# Helpers
def semitones_to_midi_pitchbend(semitones, bend_range=config.BEND_RANGE):
    """
    Map semitone offset in [-bend_range, +bend_range] to MIDI pitch-bend value 0..16383 (center=8192).
    """
    center = 8192
    max_val = 16383
    # clamp
    if semitones > bend_range:
        semitones = bend_range
    if semitones < -bend_range:
        semitones = -bend_range
    val = int(center + (semitones / bend_range) * center)
    if val < 0:
        val = 0
    if val > max_val:
        val = max_val
    return val

def map_distance_to_pitchbend(distance, in_min=5.0, in_max=20.0):
    """
    Map a distance value (expected in range in_min..in_max) to MIDI pitch-bend 0..16383.
    Values outside the range are clamped.
    """
    try:
        d = float(distance)
    except Exception:
        d = in_min

    if d <= in_min:
        return 0
    if d >= in_max:
        return 16383

    span = in_max - in_min
    frac = (d - in_min) / span
    pb = int(round(frac * 16383))
    if pb < 0:
        pb = 0
    if pb > 16383:
        pb = 16383
    return pb

# Start / Stop using only FluidSynth
def start_note(note, semitone_offset=0.0, velocity=127):       
    if not note_release_times.get(note):
        note_release_times[note] = time.time()
    
    global sustain_mode

    midi_note = config.NOTE_TO_MIDI.get(note)
    if midi_note is None:
        print("Unknown note (no MIDI mapping):", note)
        return

    # If currently playing, do not retrigger
    if note in playing_notes:
        return

    try:
        synth.noteon(config.DEFAULT_MIDI_CHANNEL, midi_note, int(velocity))
        # apply pitch bend on the channel (global)
        pb = semitones_to_midi_pitchbend(semitone_offset, bend_range=config.BEND_RANGE)
        synth.pitch_bend(config.DEFAULT_MIDI_CHANNEL, pb)
        active_channels[note] = midi_note
        playing_notes.add(note)
    except Exception as e:
        print("FluidSynth noteon failed for", note, ":", e)

def force_stop_note(note):
    midi_note = active_channels.get(note)
    if midi_note is None:
        playing_notes.discard(note)
        active_channels.pop(note, None)
        return

    try:
        synth.noteoff(config.DEFAULT_MIDI_CHANNEL, midi_note)
    except Exception as e:
        print("FluidSynth noteoff failed for", note, ":", e)

    # remove from active sets
    playing_notes.discard(note)
    active_channels.pop(note, None)

def stop_note(note):
    if note not in playing_notes:
        return

    midi_note = active_channels.get(note)
    if midi_note is None:
        playing_notes.discard(note)
        active_channels.pop(note, None)
        return

    if (not sustain_mode):
        force_stop_note(note)

# main function
def generate_music(state, sensitivity, bend_range=None):
    if bend_range is None:
        bend_range = config.BEND_RANGE

    # GET STATE VALUES
    vals = state.get("values", [])
    prev_values = state.get("prev_values", [])
    prevs = prev_values[-5] if len(prev_values) > 4 else vals
    raw_dist = state.get("distance", 0.0)

    global sustain_mode
    sustain_mode = state.get("sustain", False)

    # normalize raw_dist to a scalar controller
    try:
        dist_val = float(raw_dist)
    except Exception:
        dist_val = 0.0

    # apply pitch-bend immediately to the channel (affects all sounding notes)
    try:
        pb = map_distance_to_pitchbend(dist_val, in_min= config.DISTANCE_MIN, in_max=config.DISTANCE_MAX)
        synth.pitch_bend(config.DEFAULT_MIDI_CHANNEL, pb)
    except Exception as e:
        print("Failed to apply pitch bend:", e)

    # calculate deltas
    deltas = [vals[i] - prevs[i] for i in range(5)]
    print("Deltas:", deltas)
    print(f"raw_dist={raw_dist} -> dist_val={dist_val:.3f} -> pitchbend={pb}")

    # process each sensor
    for i, delta in enumerate(deltas):
        note = config.PIN_TO_NOTE.get(i)
        if note is None:
            continue

        if delta < -sensitivity[i]:
            print("START PLAYING: ", note)
            start_note(note, semitone_offset=0.0)
        elif delta > sensitivity[i]:
            print("STOP PLAYING: ", note)
            stop_note(note)
        else:
            pass
    
    # resets after note time if sustain is on
    # this is required to allow retriggering of notes after a delay
    for note in config.PIN_TO_NOTE.values():
        if note_release_times.get(note):
            last_released_time =  note_release_times[note]
            if time.time() - last_released_time < config.NOTE_TIME:
                return
            else:
                force_stop_note(note)
                note_release_times.pop(note, None)