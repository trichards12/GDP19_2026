#include "HX711.h"
#include <PID_v1.h>

#define LOADCELL_SCK_PIN  2
#define LOADCELL_DOUT_PIN  3

const int solenoid_In1 = 5;
const int solenoid_In2 = 6;

const int dirPin = 8;
const int stepPin = 9;

// Load Cell
HX711 scale;
float calibration_factor = -43765 / 9.81; // for newtons

// PID
double Setpoint, Input, Output;
double Kp=2.4, Ki=3.2, Kd=0;
PID myPID(&Input, &Output, &Setpoint, Kp, Ki, Kd, DIRECT);

// Moving Window
const int mw_size = 3;
float array[mw_size] = {0};
float total = 0;
int mw_i = 0;
int count = 0;

// Declarations
float movingwindow(float);

void setup() {
    // solenoid
  pinMode(solenoid_In1, OUTPUT);
  pinMode(solenoid_In2, OUTPUT);

  // stepper
  pinMode(stepPin,OUTPUT); 
  pinMode(dirPin,OUTPUT);

  // load cell
  Serial.begin(115200);
  Serial.println("GDP 19 Solenoid Feedback Test"); 

  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
  scale.set_scale(calibration_factor); //This value is obtained by using the SparkFun_HX711_Calibration sketch
  scale.tare();	//Assuming there is no weight on the scale at start up, reset the scale to 0

  delay(7000);
  digitalWrite(solenoid_In2, LOW);
  scale.tare();
  Setpoint = 30;
  Input = scale.get_units();
  // myPID.SetOutputLimits(0, 255);
  // myPID.SetSampleTime(50); // 50 ms
  myPID.SetMode(AUTOMATIC);
}

void loop() {
  Input = movingwindow(scale.get_units());
  myPID.Compute();
  analogWrite(solenoid_In1, Output);
  Serial.print(millis());
  Serial.print(",");
  Serial.print(scale.get_units());
  Serial.print(",");
  Serial.print(Input);
  Serial.print(",");
  Serial.println(Output);

}

// moving window filter function - I need to reset the array every time a new command is called?
float movingwindow(float new_value) {
  total -=array[mw_i];
  total += new_value;
  array[mw_i] = new_value;
  mw_i = (mw_i+1) % mw_size;
  if (count < mw_size){
    count++;
  }
  return total/count;
}

