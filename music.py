import time
import config

# FluidSynth-only configuration
SOUNDFONT = "soundfonts/SalC5Light2.sf2"

try:
    from fluidsynth import Synth
except Exception as e:
    raise ImportError(
        "fluidsynth is required for this script. Install with: pip install pyfluidsynth\n"
        f"Original error: {e}"
    )

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

# Runtime state
active_channels = {}
playing_notes = set()

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


# Start / Stop using only FluidSynth
def start_note(note, semitone_offset=0.0, velocity=120):
    """
    Start playing a note via FluidSynth and apply the current global pitch-bend.
    - note: one of keys present in config.NOTE_TO_MIDI
    - semitone_offset: float, offset in semitones applied on channel pitch wheel
    - velocity: MIDI velocity (0-127)
    """
    if note in playing_notes:
        return

    midi_note = config.NOTE_TO_MIDI.get(note)
    if midi_note is None:
        print("Unknown note (no MIDI mapping):", note)
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


def stop_note(note):
    """
    Stop a note via FluidSynth (send noteoff).
    Does NOT reset the channel pitch wheel globally (so other notes won't be affected).
    If you want the pitch wheel reset when all notes stop, call reset_pitch_wheel() separately.
    """
    if note not in playing_notes:
        return

    midi_note = active_channels.get(note)
    if midi_note is None:
        playing_notes.discard(note)
        active_channels.pop(note, None)
        return

    try:
        synth.noteoff(config.DEFAULT_MIDI_CHANNEL, midi_note)
    except Exception as e:
        print("FluidSynth noteoff failed for", note, ":", e)

    playing_notes.discard(note)
    active_channels.pop(note, None)


def reset_pitch_wheel():
    """Reset global pitch wheel (center) on the MIDI channel."""
    try:
        synth.pitch_bend(config.DEFAULT_MIDI_CHANNEL, 8192)
    except Exception as e:
        print("Failed to reset pitch wheel:", e)


# generate_music (global pitch via state["dist"])
def generate_music(state, sensitivity, bend_range=None):
    if bend_range is None:
        bend_range = config.BEND_RANGE

    vals = state.get("values", [])
    prevs = state.get("prev_values", [])
    raw_dist = state.get("dist", 0.0)

    # normalize raw_dist to a scalar controller
    if isinstance(raw_dist, (list, tuple)):
        if len(raw_dist) == 0:
            dist_val = 0.0
        elif len(raw_dist) == 1:
            dist_val = float(raw_dist[0])
        else:
            dist_val = float(sum(raw_dist) / len(raw_dist))
    else:
        try:
            dist_val = float(raw_dist)
        except Exception:
            dist_val = 0.0

    # compute semitone offset from global controller
    semitones_global = dist_val * float(bend_range)

    # apply pitch-bend immediately to the channel (affects all sounding notes)
    try:
        pb = semitones_to_midi_pitchbend(semitones_global, bend_range=bend_range)
        synth.pitch_bend(config.DEFAULT_MIDI_CHANNEL, pb)
    except Exception as e:
        print("Failed to apply pitch bend:", e)

    # if lengths mismatch, operate on min length
    deltas = [vals[i] - prevs[i] for i in range(5)]
    if vals != prevs:
        print("Deltas:", deltas)
    print(f"raw_dist={raw_dist} -> dist_val={dist_val:.3f} -> semitones_global={semitones_global:.3f}")

    mapping = {0: "C", 1: "D", 2: "E", 3: "F", 4: "B"}

    for i, delta in enumerate(deltas):
        note = mapping.get(i)
        if note is None:
            continue

        if delta < -sensitivity[i]:
            start_note(note, semitone_offset=semitones_global)
        elif delta > sensitivity[i] and not state.get("sustain", False):
            stop_note(note)
        else:
            pass


# Shutdown helper
def shutdown():
    try:
        synth.delete()
    except Exception:
        pass


# Demo when run as main
if __name__ == "__main__":
    # demo state and sensitivity
    sample_state = {
        "values": [0.0, 0.0, 0.0, 0.0, 0.0],
        "prev_values": [0.0, 0.0, 0.0, 0.0, 0.0],
        "dist": 0.0,   # global pitch controller: -1.0 .. +1.0 -> ±BEND_RANGE semitones
        "sustain": False,
    }
    sens = [0.05, 0.05, 0.05, 0.05, 0.05]

    try:
        print("Demo: start C")
        start_note("C", semitone_offset=0.0)
        
        print("Now simulate a trigger to start C via generate_music and bend up")
        sample_state["prev_values"] = [0.0, 0.0, 0.0, 0.0, 0.0]
        sample_state["values"] = [-1.0, 0.0, 0.0, 0.0, 0.0]  # start C
        sample_state["dist"] = 0.7
        generate_music(sample_state, sens)
        time.sleep(0.5)

        print("Bend globally down while keeping C playing")
        sample_state["prev_values"] = sample_state["values"].copy()
        sample_state["values"] = sample_state["prev_values"]
        sample_state["dist"] = -0.6
        generate_music(sample_state, sens)
        time.sleep(0.5)

        print("Stop C using generate_music logic (simulate release)")
        sample_state["prev_values"] = sample_state["values"].copy()
        sample_state["values"] = [1.0, 0.0, 0.0, 0.0, 0.0]
        sample_state["dist"] = 0.0
        generate_music(sample_state, sens)
        time.sleep(0.3)

    finally:
        print("Cleaning up synth")
        shutdown()
