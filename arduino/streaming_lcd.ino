#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);

void setup() {
  lcd.init();
  lcd.backlight();

  Serial.begin(115200);
}

String fitLine(String text) {
  if(text.length() > 16) {
    return text.substring(0, 16);
  }

  while(text.length() < 16) {
    text += " ";
  }

  return text;
}

void renderFrame(String line1, String line2) {
  lcd.setCursor(0, 0);
  lcd.print(fitLine(line1));

  lcd.setCursor(0, 1);
  lcd.print(fitLine(line2));
}

void handleMessage(String message) {
  if(!message.startsWith("LCD:")) {
    return;
  }

  String payload = message.substring(4);

  int index = payload.indexOf("|");
  if(index < 0) {
    return;
  }

  String l1 = payload.substring(0, index);
  String l2 = payload.substring(index+1);

  renderFrame(l1, l2);
}

void loop() {
  if(Serial.available() > 0) {
    String message = Serial.readStringUntil('\n');
    message.trim();
    handleMessage(message);
  }
}