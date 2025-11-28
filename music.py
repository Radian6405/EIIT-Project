import pygame

pygame.mixer.init()

# Load samples
notes = {
    "B": pygame.mixer.Sound("samples/B.wav"),
    "C": pygame.mixer.Sound("samples/C.wav"),
    "D": pygame.mixer.Sound("samples/D.wav"),
    "E": pygame.mixer.Sound("samples/E.wav"),
    "F": pygame.mixer.Sound("samples/F.wav"),
}

active_channels = {}
playing_notes = set()

def clean_finished():
    to_remove = []
    for note, ch in list(active_channels.items()):
        try:
            if not ch.get_busy():  # finished naturally
                to_remove.append(note)
        except Exception:
            # if channel invalid for any reason, remove it
            to_remove.append(note)

    for note in to_remove:
        active_channels.pop(note, None)
        playing_notes.discard(note)


def start_note(note):
    clean_finished()

    if note not in notes:
        print("Unknown note:", note)
        return

    if note in playing_notes:
        # already playing
        return

    channel = notes[note].play()
    if channel is not None:
        active_channels[note] = channel
        playing_notes.add(note)
    else:
        ch = pygame.mixer.find_channel()
        if ch:
            ch.play(notes[note])
            active_channels[note] = ch
            playing_notes.add(note)
        else:
            print("No free channel to play", note)


def stop_note(note):
    clean_finished()

    if note not in playing_notes:
        # already stopped
        return

    ch = active_channels.get(note)
    if ch:
        ch.stop()
    active_channels.pop(note, None)
    playing_notes.discard(note)


def generate_music(state, sensitivity):
    clean_finished()

    deltas = [state["values"][i] - state["prev_values"][i] for i in range(len(state["values"]))]
    if state["values"] == state["prev_values"]:
        return
    
    print("Deltas:", deltas)

    for (i, delta) in enumerate(deltas):
        note = None
        if i == 0:
            note = "C"
        elif i == 1:
            note = "D"
        elif i == 2:
            note = "E"
        elif i == 3:
            note = "F"
        elif i == 4:
            note = "B"

        if note is not None:
            if delta > sensitivity:
                stop_note(note)
            elif delta < -sensitivity:
                start_note(note)


if __name__ == "__main__":
    import time

    print("Playing C")
    start_note("C")
    time.sleep(0.5)

    print("Attempting to play C again (should do nothing)")
    start_note("C")
    time.sleep(1.5)

    print("Stopping C")
    stop_note("C")

    print("Done")
