#include "HX711.h"
// #include <PID_v1.h>

// pin numbers
#define LOADCELL_SCK_PIN  2
#define LOADCELL_DOUT_PIN  3

const int solenoid_In1 = 5;
const int solenoid_In2 = 6;

const int dirPin = 8;
const int stepPin = 9;

HX711 scale;
float calibration_factor = -43765 / 9.81;
// serial info
const char *names[] = {"Off", "Stand", "Walk", "Run"};

const int off = 0;
const int stand = 1;
const int walk = 2;
const int run = 3;

// serial packets
const int maxCycles = 20;
int movements[maxCycles];
unsigned long durations[maxCycles];
int totalSteps = 0;
int currentStep = 0;
unsigned long stepStartTime = 0;
bool programLoaded = false;
bool running = false;
bool paused = false;
const byte numChars = 128;
char receivedChars[numChars];
char tempChars[numChars];   // temporary array for use when parsing
boolean newData = false;


// function prototypes
void recvWithStartEndMarkers(); // receive + copy new data
void parseData(); // strip the markers into movement cycles
void showParsedData(); // format the data into individual cycles
void runProgram(); // main loop with each cycle to check for stop commands
void movementCycle(int); // cycle logic
void stepWithRamp(int, int, int); // for stepper rotation

/*
void offCycle(unsigned long);
void standCycle(unsigned long);
void walkCycle(unsigned long);
void runCycle(unsigned long);
*/
//============

void setup() {
    Serial.begin(115200);
    
    // solenoid
    pinMode(solenoid_In1, OUTPUT);
    pinMode(solenoid_In2, OUTPUT);

    // stepper
    pinMode(stepPin,OUTPUT); 
    pinMode(dirPin,OUTPUT);
    
    // load cell
    scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
    scale.set_scale(calibration_factor);
    scale.tare();
    
    delay(5000);
    scale.tare();

    // Serial.println("Enter data in this style <2, 5.0>"); // movement cycle number, duration
    // Serial.println();
}

//============

void loop() {
    recvWithStartEndMarkers();
    if (newData == true) {
        strcpy(tempChars, receivedChars);
            // this temporary copy is necessary to protect the original data
            //   because strtok() used in parseData() replaces the commas with \0
        parseData();
        newData = false;
    }

    runProgram();
}

//============

void recvWithStartEndMarkers() {
    static bool recvInProgress = false;
    static byte ndx = 0;
    const char startMarker = '<';
    const char endMarker = '>';
    char rc;

    while (Serial.available() > 0) {
        rc = Serial.read();

        if (recvInProgress) {
            if (rc != endMarker) {
                if (ndx < numChars - 1) {
                    receivedChars[ndx++] = rc;
                }
            } else {
                receivedChars[ndx] = '\0';
                recvInProgress = false;
                ndx = 0;
                newData = true;
                return;  // stop after one full message
            }
        }
        else if (rc == startMarker) {
            recvInProgress = true;
        }
    }
}

//============

void parseData() {
    if (strcmp(tempChars, "P") == 0) {
    paused = !paused;
    return;
    }
    
    if (strcmp(tempChars, "S") == 0) {
        running = false;
        currentStep = 0;
        return;
    }
    
    if (strcmp(tempChars, "R") == 0) {
        paused = false;
        running = true;
        return;
    }
    
    char * strtokIndx;

    strtokIndx = strtok(tempChars, ",");
    totalSteps = atoi(strtokIndx);

    if (totalSteps > maxCycles) totalSteps = maxCycles;

    for (int i = 0; i < totalSteps; i++) {
        strtokIndx = strtok(NULL, ",");
        movements[i] = atoi(strtokIndx);

        strtokIndx = strtok(NULL, ",");
        durations[i] = atol(strtokIndx) * 1000;
    }

    currentStep = 0;
    programLoaded = true;
    running = false;
    paused = false;

}

//============

void runProgram() {
    if (!running || paused || !programLoaded) return;

    if (currentStep >= totalSteps) {
        running = false;
        return;
    }

    unsigned long now = millis();

    if (stepStartTime == 0) {
        stepStartTime = now;
    }

    // execute current movement (non-blocking version)
    movementCycle(movements[currentStep]);

    if (now - stepStartTime >= durations[currentStep]) {
        currentStep++;
        stepStartTime = 0;
    }
}

//============

void movementCycle(int movement) {
    static unsigned long lastPrint = 0;
    switch (movement) {
        case 0: // off
            digitalWrite(solenoid_In1, LOW);
            digitalWrite(solenoid_In2, LOW);
            if (millis() - lastPrint >= 100) {
                lastPrint = millis();
                Serial.print(lastPrint);
                Serial.print(",");
                Serial.println(scale.get_units());
            }
            break;

        case 1: // stand
            digitalWrite(solenoid_In1, LOW);
            analogWrite(solenoid_In2, 200);
            if (millis() - lastPrint >= 100) {
                lastPrint = millis();
                Serial.print(lastPrint);
                Serial.print(",");
                Serial.println(scale.get_units());
            }
            break;

        case 2: // walk - this is currently blocking - remove delays 
            digitalWrite(solenoid_In1, LOW);
            digitalWrite(solenoid_In2, LOW);
            digitalWrite(dirPin, LOW);
            stepWithRamp(36, 7000, 3000);

            Serial.print(millis()); // take readings at top of rotation
            Serial.print(",");
            Serial.println(scale.get_units());

            digitalWrite(dirPin, HIGH);
            stepWithRamp(36, 7000, 3000);

            Serial.print(millis()); // take readings at bottom of rotation
            Serial.print(",");
            Serial.println(scale.get_units());

            digitalWrite(solenoid_In1, LOW); // SOLENOID HERE
            analogWrite(solenoid_In2, 255);

            for (int j=0; j<8; j++) {
                Serial.print(millis());
                Serial.print(",");
                Serial.println(scale.get_units());
            }

            digitalWrite(solenoid_In1, LOW);
            digitalWrite(solenoid_In2, LOW);

            Serial.print(millis());
            Serial.print(",");
            Serial.println(scale.get_units());

            break;

        case 3: // run - this is currently blocking - remove delays
            digitalWrite(solenoid_In1, LOW);
            digitalWrite(solenoid_In2, LOW);
            digitalWrite(dirPin, LOW);
            stepWithRamp(36, 7000, 2000);

            Serial.print(millis()); // take readings at top of rotation
            Serial.print(",");
            Serial.println(scale.get_units());

            digitalWrite(dirPin, HIGH);
            stepWithRamp(36, 7000, 2000);

            Serial.print(millis()); // take readings at bottom of rotation
            Serial.print(",");
            Serial.println(scale.get_units());

            digitalWrite(solenoid_In1, LOW); // SOLENOID HERE
            analogWrite(solenoid_In2, 255);

            for (int j=0; j<6; j++) {
                Serial.print(millis());
                Serial.print(",");
                Serial.println(scale.get_units());
            }

            digitalWrite(solenoid_In1, LOW);
            digitalWrite(solenoid_In2, LOW);

            Serial.print(millis());
            Serial.print(",");
            Serial.println(scale.get_units());

            break;
    }
}

//============

void stepWithRamp(int steps, int startDelay, int endDelay) {
  for (int x = 0; x < steps; x++) {
    int delayTime;

    if (x < steps / 2) {
      delayTime = startDelay - (x * (startDelay - endDelay) / (steps / 2));
    } else {
      delayTime = startDelay - ((steps - x) * (startDelay - endDelay) / (steps / 2));
    }

    digitalWrite(stepPin, HIGH);
    delayMicroseconds(delayTime);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(delayTime);
  }
}
