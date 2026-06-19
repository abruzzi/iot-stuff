#include <Servo.h>

Servo panServo;
Servo tiltServo;

const int PAN_SERVO_PIN = 9;
const int TILT_SERVO_PIN = 10;

int panServoAngle = 90;
int tiltServoAngle = 90;

const int panStep = 5;
const int tiltStep = 5;

void setup() {
  Serial.begin(115200);

  panServo.attach(PAN_SERVO_PIN);
  panServo.write(panServoAngle);

  tiltServo.attach(TILT_SERVO_PIN);
  tiltServo.write(tiltServoAngle);  

  Serial.println("Cameraman ready");
}

void loop() {
  if(Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    Serial.print("Received command: ");
    Serial.println(command);

    if(command == "LEFT") {
      panServoAngle += panStep;
    } else if (command == "RIGHT") {
      panServoAngle -= panStep;
    } else if (command == "UP") {
      tiltServoAngle += tiltStep;
    } else if (command == "DOWN") {
      tiltServoAngle -= tiltStep;
    } else if (command == "CENTER") {
      // do nothing 
    } else if (command.startsWith("PAN:")) {
      int delta = command.substring(4).toInt();
      panServoAngle += delta;
    } else if (command.startsWith("TILT:")) {
      int delta = command.substring(5).toInt();
      tiltServoAngle += delta;
    } else {
      Serial.print("Unknown command: ");
      Serial.println(command);
    }

    panServoAngle = constrain(panServoAngle, 45, 135);
    tiltServoAngle = constrain(tiltServoAngle, 60, 120);

    panServo.write(panServoAngle);
    tiltServo.write(tiltServoAngle);

    Serial.print("Pan Servo angle: ");
    Serial.println(panServoAngle);

    Serial.print("Tilt Servo angle: ");
    Serial.println(tiltServoAngle);
  }
}
