constexpr int PWMA = 2;
constexpr int AIN1 = 3;
constexpr int AIN2 = 4;

constexpr int PWMB = 5;
constexpr int BIN1 = 6;
constexpr int BIN2 = 7;

constexpr int STBY = 10;

void forwardMotorA() {
  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);
}

void backwardMotorA() {
  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, HIGH);
}

void stopMotorA() {
  analogWrite(PWMA, 0);
  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, LOW);
}

void stopMotorB() {
  analogWrite(PWMB, 0);
  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, LOW);
}

// 0 - 255
void setMotorASpeed(int speed) {
  analogWrite(PWMA, speed);
}

// steering 
void turnLeft() {
  analogWrite(PWMB, 120);
  digitalWrite(BIN1, HIGH);
  digitalWrite(BIN2, LOW);
}

void turnRight() {
  analogWrite(PWMB, 120);
  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, HIGH);
}

void stopSteering() {
  analogWrite(PWMB, 0);
  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, LOW);
}

void initialisePins() {
  pinMode(PWMA, OUTPUT);
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);

  pinMode(PWMB, OUTPUT);
  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);

  pinMode(STBY, OUTPUT);

  digitalWrite(STBY, HIGH);
}

void stopAllMotors() {
  stopMotorA();
  stopMotorB();
}

void setup() {
  initialisePins();
  stopAllMotors();
}

void loop() {
  setMotorASpeed(100);
  forwardMotorA();

  delay(1000);

  setMotorASpeed(150);
  forwardMotorA();

  delay(1000);

  stopMotorA();

  delay(1000);

  setMotorASpeed(150);
  backwardMotorA();

  delay(1000);

  setMotorASpeed(100);
  backwardMotorA();

  delay(1000);

  stopMotorA();

  delay(1000);

    turnLeft();
  delay(150);
  stopSteering();
  delay(1000);

  turnRight();
  delay(150);
  stopSteering();
  delay(1000);
}