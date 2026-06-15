#include <Servo.h>

Servo panServo;

int servoAngle = 90;

void setup() {
  Serial.begin(9600);

  panServo.attach(9);
  panServo.write(servoAngle);

  Serial.println("Arduino ready");
}

void loop() {
  if(Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    Serial.print("Received command: ");
    Serial.println(command);

    if(command == "LEFT") {
      servoAngle += 2;
    } else if (command == "RIGHT") {
      servoAngle -= 2;
    } else {
      // stay still in this round
    }

    servoAngle = constrain(servoAngle, 0, 180);
    panServo.write(servoAngle);

    Serial.print("servo angle: ");
    Serial.println(servoAngle);
  }
}
