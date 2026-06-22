#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

#include <Servo.h>

int servoPin = 9;
int potPin = A0;

Servo servo;

void setup() {
  servo.attach(servoPin);

  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) for(;;);

  display.clearDisplay();
  display.setTextSize(1);             
  display.setTextColor(SSD1306_WHITE); 
  
  display.setCursor(0, 0);
  display.display();
}

void displayProcessBar(int value) {
  int barWidth = map(value, 0, 1023, 0, 120);

  display.drawRect(0, 52, 122, 10, SSD1306_WHITE);
  display.fillRect(1, 53, barWidth, 8, SSD1306_WHITE);
}

void displayServoStatus(int value) {
  int angle = map(value, 0, 1023, 0, 180);

  display.clearDisplay();

  display.setCursor(0, 0);
  display.print("Servo Controller");

  display.setCursor(0, 20);
  display.print("Analog: ");
  display.print(value);

  display.setCursor(0, 35);
  display.print("Angle: ");
  display.print(angle);
  display.print(" deg");

  displayProcessBar(value);

  display.display();
}

void loop() {
  int value = analogRead(potPin);
  int angle = map(value, 0, 1023, 0, 180);

  servo.write(angle);
  displayServoStatus(value);

  delay(15);
}
