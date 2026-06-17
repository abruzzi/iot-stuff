#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);

void setup() {
  lcd.init();
  lcd.backlight();

  Serial.begin(115200);

  panServo.attach(9);
  panServo.write(servoAngle);

  Serial.println("Arduino ready");
}

void loop() {
  if(Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if(command == "LEFT") {
      servoAngle += 2;
    } else if (command == "RIGHT") {
      servoAngle -= 2;
    } else if (command == "CENTER") {
      // do nothing 
    } else if (command.startsWith("PAN:")) {
      int delta = command.substring(4).toInt();

      servoAngle += delta;
      servoAngle = constrain(servoAngle, 0, 180);

      panServo.write(servoAngle);

      Serial.print("Servo angle: ");
      Serial.println(servoAngle);    
    } else {
      Serial.print("Unknown command: ");
      Serial.println(command);
    }

    servoAngle = constrain(servoAngle, 0, 180);
    panServo.write(servoAngle);

    Serial.print("servo angle: ");
    Serial.println(servoAngle);
  }
}