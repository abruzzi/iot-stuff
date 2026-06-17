const int segmentPins[] = {
  2, // a
  3, // b
  4, // c
  5, // d
  6, // e
  7, // f
  8  // g
};

// 每一行表示一个数字
// 顺序是：a, b, c, d, e, f, g
const byte digits[10][7] = {
  {1, 1, 1, 1, 1, 1, 0}, // 0
  {0, 1, 1, 0, 0, 0, 0}, // 1
  {1, 1, 0, 1, 1, 0, 1}, // 2
  {1, 1, 1, 1, 0, 0, 1}, // 3
  {0, 1, 1, 0, 0, 1, 1}, // 4
  {1, 0, 1, 1, 0, 1, 1}, // 5
  {1, 0, 1, 1, 1, 1, 1}, // 6
  {1, 1, 1, 0, 0, 0, 0}, // 7
  {1, 1, 1, 1, 1, 1, 1}, // 8
  {1, 1, 1, 1, 0, 1, 1}  // 9
};

void setup() {
  Serial.begin(9600);

  for (int i = 0; i < 7; i++) {
    pinMode(segmentPins[i], OUTPUT);
  }
  
  Serial.println("Arduino ready");
}

void loop() {
  if(Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    Serial.print("Received command: ");
    Serial.println(command);

    if (command.startsWith("NUMBER:")) {
      int digit = command.substring(7).toInt();

      displayDigit(digit);
      delay(1000);
      
      Serial.print("Recognised number: ");
      Serial.println(digit);    
    } else {
      showPlaceholder();
      Serial.print("Unknown command: ");
      Serial.println(command);
    }
  }
}

void showPlaceholder() {
  clearDisplay();
  digitalWrite(8, HIGH);
}

void displayDigit(int digit) {
  clearDisplay();

  for (int segment = 0; segment < 7; segment++) {
    digitalWrite(segmentPins[segment], digits[digit][segment] ? HIGH : LOW);
  }
}

void clearDisplay() {
  for (int i = 0; i < 7; i++) {
    digitalWrite(segmentPins[i], LOW);
  }
}