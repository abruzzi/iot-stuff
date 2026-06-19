#include <Servo.h>

Servo panServo;

const int SERVO_PIN = 9;
int servoAngle = 90;
const int step = 10;

void setup() {
  Serial.begin(9600);

  panServo.attach(SERVO_PIN);
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
      servoAngle += step;
    } else if (command == "RIGHT") {
      servoAngle -= step;
    } else if (command == "CENTER") {
      // do nothing 
    } else if (command.startsWith("PAN:")) {
      int delta = command.substring(4).toInt();

      servoAngle += delta;
    } else {
      Serial.print("Unknown command: ");
      Serial.println(command);
    }

    servoAngle = constrain(servoAngle, 30, 150);

    panServo.write(servoAngle);

    Serial.print("Servo angle: ");
    Serial.println(servoAngle); 
  }
}
