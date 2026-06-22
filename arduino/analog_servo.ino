#include <Servo.h>

int servoPin = 9;
int potPin = A0;

Servo servo;

void setup() {
  servo.attach(servoPin);
}

void loop() {
  int value = analogRead(potPin);
  int angle = map(value, 0, 1023, 0, 180);

  servo.write(angle);
  delay(15);
}
