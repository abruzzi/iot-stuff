const int segmentPins[] = {
  2, // a
  3, // b
  4, // c
  5, // d
  6, // e
  7, // f
  8  // g
};

void number_1() {
  digitalWrite(3, HIGH);
  digitalWrite(4, HIGH);
}

void number_2() {
  digitalWrite(2, HIGH);
  digitalWrite(3, HIGH);
  digitalWrite(5, HIGH);
  digitalWrite(6, HIGH);
  digitalWrite(8, HIGH);
}

void setup() {
  for (int i = 0; i < 7; i++) {
    pinMode(segmentPins[i], OUTPUT);
  }
}

void loop() {
  for (int i = 0; i < 100; i++) {
    clearDisplay();
    if(i % 2 == 0) {
      number_1();
    } else {
      number_2();
    }
    delay(1000);
  }
}

void clearDisplay() {
  for (int i = 0; i < 7; i++) {
    digitalWrite(segmentPins[i], LOW);
  }
}