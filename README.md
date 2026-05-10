# GDP 19

The programs used to test and verify the canine elbow joint simulator built by GDP 19 for the 2025-2026 academic year.
  
  1. GDP19_GUI.py - Graphical user interface made in Python using Tkinter
  2. GDP19_ARDUINO.ino - Actuator logic using ARDUINO UNO R3
  3. GDP19_PID.ino - Test PID controller for the linear solenoid
  4. GDP19_Electronics_Test_Plan.pdf - Notes on the implementation of the electronic circuit

The GUI and ARDUINO programs are required for the complete operation of the rig. Instructions from the GUI are communicated to the ARDUINO through the serial buffer. Detailed system architecture found in the GDP19_Group_Report summative submission.

----------

### Instructions to run:
  1. Connect actuators to ARDUINO and drivers according to circuit diagram included in Electronics_Test_Plan.pdf
  2. Download ARDUINO.ino onto the ARDUINO.
  3. Connect power supply to the linear solenoid and stepper motor drivers. Do not turn on to prevent A4988 overheating.
  4. Open and run GUI.py.
  5. Select COM port at the top of the GUI.
  6. Choose movement routines for the rig to actuate.
  7. Press 'Connect ARDUINO'.
  8. Press 'Run'.
  9. (optional) Results can be saved at any point during the operation using the 'Save to CSV' button.

----------

### Known issues:
  - Timing mismatch between rig and animated moving dot on the GUI -> fix using ARDUINO millis() timer to resync programs.
  - Force application from the linear solenoid is sensitive to pin spacing -> recalibrate using provided horseshoe shim.
  - A4988 overheats over long periods of operation -> ensure heatsink is attached.
  - Animated moving dot on GUI has performance issues on lower spec.

Future developments listed in both the GUI.py and the GDP19_Group_Report summative submission.

----------

*Made by Travis Richards, tr2g21@soton.ac.uk*
