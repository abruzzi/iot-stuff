const int RELAY_PIN = 5;

const int RELAY_ON = HIGH;
const int RELAY_OFF = LOW;

void setup() {
  Serial.begin(115200);
  
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, RELAY_OFF);

  Serial.println("Relay is ready");
}

void loop() {
  Serial.println("Relay ON");
  digitalWrite(RELAY_PIN, RELAY_ON);
  delay(500);

  Serial.println("Relay OFF");
  digitalWrite(RELAY_PIN, RELAY_OFF);
  delay(3000);
}