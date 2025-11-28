# Arduino output should be in format:
# <flex1> <flex2> <flex3> <flex4> <flex5> <ir_toggle(1/0)> <ultrasonic_distance>    

# Sensor configuration parameters
INITIAL_VALUES = [300, 300, 300, 300, 300]
MAX_VALUES =     [500, 500, 500, 500, 500]

# delta value to trigger note on/off
SENSITIVITY = [4, 4, 4, 4, 4]

# Pitch / MIDI settings
# semitones for dist=Â±1.0
BEND_RANGE = 2.0  
DEFAULT_MIDI_CHANNEL = 0

# approximate MIDI note numbers for our notes (C4=60)
NOTE_TO_MIDI = {"C": 60, "D": 62, "E": 64, "F": 65, "B": 59}