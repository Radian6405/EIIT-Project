# Arduino output should be in format:
# <flex1> <flex2> <flex3> <flex4> <flex5> <ir_toggle(1/0)> <ultrasonic_distance>    

# Flex Sensor configuration parameters
INITIAL_VALUES = [300, 300, 300, 300, 300]
MAX_VALUES =     [500, 500, 500, 500, 500]

# approximate MIDI note numbers for our notes (C4=60)
NOTE_TO_MIDI = {"B": 59, "C": 60, "D": 62, "E": 64, "F": 65}
# PIN_TO_NOTE = {0: "C", 1: "D", 2: "E", 3: "F"}
PIN_TO_NOTE =  {0: "C", 1: "D", 2: "E", 3: "F", 4: "C"}

# delta value to trigger note on/off
SENSITIVITY = [4, 4, 4, 4, 4]

# Pitch / MIDI settings
BEND_RANGE = 100.0  
DEFAULT_MIDI_CHANNEL = 0

# Time taken for a note play (used when sustain is on)
NOTE_TIME = 2.0

# Ultrasonic sensor mapping parameters
DISTANCE_MIN = 5.0   # cm
DISTANCE_MAX = 20.0  # cm

