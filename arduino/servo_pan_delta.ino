#include <Servo.h>

Servo panServo;
Servo tiltServo;

const int PAN_SERVO_PIN = 9;
const int TILT_SERVO_PIN = 10;

int panServoAngle = 90;
int tiltServoAngle = 90;

const int panStep = 5;
const int tiltStep = 4;

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(50);

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

    // Serial.print("Received command: ");
    // Serial.println(command);

    if(command == "LEFT") {
      panServoAngle += panStep;
    } else if (command == "RIGHT") {
      panServoAngle -= panStep;
    } else if (command == "UP") {
      tiltServoAngle += tiltStep;
    } else if (command == "DOWN") {
      tiltServoAngle -= tiltStep;
    } else if (command.startsWith("MOVE:")) {
      String payload = command.substring(5);
      int commaIndex = payload.indexOf(',');

      if (commaIndex > 0) {
        int panDelta = payload.substring(0, commaIndex).toInt();
        int tiltDelta = payload.substring(commaIndex + 1).toInt();

        panServoAngle += panDelta;
        tiltServoAngle += tiltDelta;
      }
    } else {
      Serial.print("Unknown command: ");
      Serial.println(command);
    }

    panServoAngle = constrain(panServoAngle, 45, 135);
    tiltServoAngle = constrain(tiltServoAngle, 45, 135);

    panServo.write(panServoAngle);
    tiltServo.write(tiltServoAngle);

    Serial.print("Pan Servo angle: ");
    Serial.println(panServoAngle);

    Serial.print("Tilt Servo angle: ");
    Serial.println(tiltServoAngle);
  }
}
