// pin numbers
const int stepperDir = 2;
const int stepperStep = 3;

const int solenoidIn1 = 5;
const int solenoidIn2 = 6;

const int loadDat = 11;
const int loadClk = 12;

const char *names[] = {"Off", "Stand", "Walk", "Run"};

const int off = 0;
const int stand = 1;
const int walk = 2;
const int run = 3;

// test
const int stepperF = 3;
const int stepperB = 6;
const int solenoid = 10;

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
void recvWithStartEndMarkers();
void parseData();
void showParsedData();
void runProgram();
void movementCycle(int);

/*
void offCycle(unsigned long);
void standCycle(unsigned long);
void walkCycle(unsigned long);
void runCycle(unsigned long);
*/
//============

void setup() {
    Serial.begin(115200);
    pinMode(stepperF, OUTPUT);
    pinMode(stepperB, OUTPUT);
    pinMode(solenoid, OUTPUT);
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
            digitalWrite(stepperF, LOW);
            digitalWrite(stepperB, LOW);
            digitalWrite(solenoid, LOW);
            if (millis() - lastPrint >= 100) {
                lastPrint = millis();
                Serial.print(lastPrint);
                Serial.print(",");
                Serial.println();
            }
            break;

        case 1: // stand
            analogWrite(solenoid, 120);
            if (millis() - lastPrint >= 100) {
                lastPrint = millis();
                Serial.print(lastPrint);
                Serial.print(",");
                Serial.println();
            }
            break;

        case 2: // walk - this is currently blocking - remove delays 
            digitalWrite(solenoid, LOW);
            digitalWrite(stepperF, HIGH);
            digitalWrite(stepperB,LOW);
            delay(300);
            digitalWrite(stepperF, LOW);
            digitalWrite(stepperB,HIGH);
            delay(300);
            digitalWrite(stepperB, LOW);
            analogWrite(solenoid, 200);
            delay(300);
            digitalWrite(solenoid, LOW);
            break;

        case 3: // run - this is currently blocking - remove delays
            digitalWrite(solenoid, LOW);
            digitalWrite(stepperF, HIGH);
            digitalWrite(stepperB,LOW);
            delay(200);
            digitalWrite(stepperF, LOW);
            digitalWrite(stepperB,HIGH);
            delay(200);
            digitalWrite(stepperB, LOW);
            analogWrite(solenoid, 200);
            delay(200);
            digitalWrite(solenoid, LOW);
            break;
    }
}

//============
