import serial
import time

def setup():
    global arduino

    # arduino = serial.Serial('/dev/ttyACM0', 9600)  # Linux
    arduino = serial.Serial('COM7', 9600)       # Windows
    time.sleep(5)  # wait for Arduino reset

def update_state(state, sustain_threshold):
    line = arduino.readline().decode(errors="ignore").strip()

    if not line:
        return

    parts = line.split()
    numbers = []

    for p in parts:
        try:
            numbers.append(int(p))
        except ValueError:
            print(f"Skipping invalid value: {p}")
            return

    # If all parts are valid integers
    print("Numbers list:", numbers)

    # sustain logic
    state["dist"] = numbers[-1]
    if numbers[-1] < sustain_threshold:
        state["sustain"] = True
    else:
        state["sustain"] = False
    numbers = numbers[:-1]

    # flex sensor values
    state["pending"] = numbers
    state["last_change"] = time.time()
