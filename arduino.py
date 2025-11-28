import serial
import time

arduino = serial.Serial('/dev/ttyACM0', 9600)  # Linux
# arduino = serial.Serial('COM7', 9600)       # Windows
time.sleep(5)  # wait for Arduino reset

def update_state(state):
    line = arduino.readline().decode(errors="ignore").strip()

    if not line:
        return  # empty line, skip

    parts = line.split()
    numbers = []

    for p in parts:
        try:
            numbers.append(int(p))
        except ValueError:
            print(f"Skipping invalid value: {p}")
            return  # skip the whole line safely

    # If all parts are valid integers
    print("Numbers list:", numbers)
    state["pending"] = numbers
    state["last_change"] = time.time()
