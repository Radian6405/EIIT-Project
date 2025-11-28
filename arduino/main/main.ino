// ULTRASONIC SENSOR DEFINITIONS
const int US_TRIG_PIN = 9;  // Trigger pin connected to D9
const int US_ECHO_PIN = 10; // Echo pin connected to D10

//IR SENSOR DEFINITION
const int IR_PIN = 2;       // IR sensor connected to Digital Pin 2

//FLEX SENSOR DEFINITIONS
const int FLEX_PINS[] = {A0, A1, A2, A3, A4};
const int NUM_FLEX_SENSORS = 5;

// GLOBAL STATE & VARIABLES
// State flag: true if US sensor should actively measure/print
boolean measuringActive = false; 
// Stores the previous state of the IR sensor for edge detection
int lastIrReading = HIGH;        

// Ultrasonic variables
long duration;
int distance = 0; 

// Flex sensor variables
int flex_readings[NUM_FLEX_SENSORS];

//TIMING VARIABLES 
unsigned long lastReadTime = 0;
const long READ_INTERVAL = 50; // 500ms = 2 times per second

void setup() {
  Serial.begin(9600); 
  
  // Set pin modes
  pinMode(US_TRIG_PIN, OUTPUT);
  pinMode(US_ECHO_PIN, INPUT);
  pinMode(IR_PIN, INPUT); 
  
  // NOTE: Debug prints removed to keep serial output clean for Python
}

void loop() {
  // 1. IR SENSOR TOGGLE LOGIC 
  int currentIrReading = digitalRead(IR_PIN);
  
  if (currentIrReading == LOW && lastIrReading == HIGH) {
    measuringActive = !measuringActive; 
    delay(50); // Small debounce delay
  }
  lastIrReading = currentIrReading;


  // 2. SENSOR READINGS (Runs every 500ms)
  unsigned long currentMillis = millis();

  if (currentMillis - lastReadTime >= READ_INTERVAL) {
    lastReadTime = currentMillis;

    // --- A. GET FLEX SENSOR DATA ---
    for (int i = 0; i < NUM_FLEX_SENSORS; i++) {
      flex_readings[i] = analogRead(FLEX_PINS[i]);
    }

    // --- B. GET ULTRASONIC DATA ---
    digitalWrite(US_TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(US_TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(US_TRIG_PIN, LOW);

    duration = pulseIn(US_ECHO_PIN, HIGH);
    
    if (duration == 0) {
      distance = -1; // Indicate error
    } else {
      distance = duration * 0.0343 / 2;
    }

    // --- C. PRINT EVERYTHING IN ONE LINE ---
    // Format: <A0> <A1> <A2> <A3> <A4> <ir_toggle> <distance>
    
    // 1. Print Flex Values
    for (int i = 0; i < NUM_FLEX_SENSORS; i++) {
      Serial.print(flex_readings[i]);
      Serial.print(" ");
    }

    // 2. Print IR Toggle State (1 for ON, 0 for OFF)
    Serial.print(measuringActive ? 1 : 0);
    Serial.print(" ");

    // 3. Print Ultrasonic Distance (ends with new line)
    Serial.println(distance);
  }
}
