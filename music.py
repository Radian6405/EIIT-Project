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
sustain_mode = False   # track sustain state
note_release_times = {}  # note -> timestamp when retrigger allowed

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

    # compute semitone offset from global controller
    semitones_global = dist_val * float(bend_range)

    # apply pitch-bend immediately to the channel (affects all sounding notes)
    try:
        pb = semitones_to_midi_pitchbend(semitones_global, bend_range=bend_range)
        synth.pitch_bend(config.DEFAULT_MIDI_CHANNEL, pb)
    except Exception as e:
        print("Failed to apply pitch bend:", e)

    # CALCULATE DELTAS
    deltas = [vals[i] - prevs[i] for i in range(5)]
    if deltas is not None and deltas[0] < -4 and deltas[1] < -4 and deltas[2] < -4 and deltas[3] < -4:
        print("Deltas:", deltas)
        print(f"raw_dist={raw_dist} -> dist_val={dist_val:.3f} -> semitones_global={semitones_global:.3f}")

    # mapping = {0: "C", 1: "D", 2: "E", 3: "F", 4: "B"}
    mapping = {0: "C", 1: "D", 2: "E", 3: "F"}

    for i, delta in enumerate(deltas):
        note = mapping.get(i)
        if note is None:
            continue

        if delta < -sensitivity[i]:
            print("START PLAYING: ", note)
            start_note(note, semitone_offset=semitones_global)
        elif delta > sensitivity[i]:
            print("STOP PLAYING: ", note)
            stop_note(note)
        else:
            pass
    
    for note in mapping.values():
        if note_release_times.get(note):
            last_released_time =  note_release_times[note]
            # print(last_released_time, time.time(), time.time() - last_released_time , config.NOTE_TIME)
            if time.time() - last_released_time < config.NOTE_TIME:
                print("Note", note, "is still in release time, cannot retrigger yet.")
                return
            else:
                print("Note", note, "release time passed, can retrigger now.")
                print(playing_notes)
                print(active_channels)
                force_stop_note(note)
                note_release_times.pop(note, None)

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
        "dist": 0.0,   # global pitch controller: -1.0 .. +1.0 -> Â±BEND_RANGE semitones
        "sustain": False,
    }
    sens = [0.05, 0.05, 0.05, 0.05, 0.05]

    try:
        
        print("Play B")
        start_note("B", semitone_offset=-90.0)
        time.sleep(0.5)
        # stop_note("B")
        # print("Demo: start C")
        # start_note("C", semitone_offset=0.0)
        # time.sleep(0.5)

        print("change pitch")
        pb = semitones_to_midi_pitchbend(90.0, bend_range=config.BEND_RANGE)
        synth.pitch_bend(config.DEFAULT_MIDI_CHANNEL, pb)
        time.sleep(3.0)
        # stop_note("B")

        # start_note("C", semitone_offset=0.0)
        # time.sleep(3)
        # start_note("D", semitone_offset=0.0)
        # time.sleep(3)
        
        # print("Now simulate a trigger to start C via generate_music and bend up")
        # sample_state["prev_values"] = [0.0, 0.0, 0.0, 0.0, 0.0]
        # sample_state["values"] = [-1.0, 0.0, 0.0, 0.0, 0.0]  # start C
        # sample_state["dist"] = 0.7
        # generate_music(sample_state, sens)
        # time.sleep(0.5)

        # print("Bend globally down while keeping C playing")
        # sample_state["prev_values"] = sample_state["values"].copy()
        # sample_state["values"] = sample_state["prev_values"]
        # sample_state["dist"] = -0.6
        # generate_music(sample_state, sens)
        # time.sleep(0.5)

        # print("Stop C using generate_music logic (simulate release)")
        # sample_state["prev_values"] = sample_state["values"].copy()
        # sample_state["values"] = [1.0, 0.0, 0.0, 0.0, 0.0]
        # sample_state["dist"] = 0.0
        # generate_music(sample_state, sens)
        # time.sleep(0.3)

    finally:
        print("Cleaning up synth")
        shutdown()
