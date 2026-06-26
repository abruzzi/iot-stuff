#include <WiFi.h>
#include <WebServer.h>

WebServer server(80);

const char* ssid = "wifi";
const char* password = "password";

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

// initialise the hardwares
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

// http handlers
int driveSpeed = 120;
int steeringSpeed = 120;
int steeringPulseMs = 150;

String driveDirection = "idle";     // idle | forward | backward
String steeringDirection = "idle";  // idle | left | right

void handleStatus() {
  String json = "{";
  json += "\"ok\":true,";
  json += "\"driveSpeed\":" + String(driveSpeed) + ",";
  json += "\"steeringSpeed\":" + String(steeringSpeed) + ",";
  json += "\"driveDirection\":\"" + driveDirection + "\",";
  json += "\"steeringDirection\":\"" + steeringDirection + "\"";
  json += "}";

  server.send(200, "application/json", json);
}

void handleLeft() {
  turnLeft();
  delay(steeringPulseMs);
  stopSteering();

  server.send(
    200,
    "application/json",
    "{\"ok\": true, \"message\": \"turned left\"}"
  );
}

void handleRight() {
  turnRight();
  delay(steeringPulseMs);
  stopSteering();

  server.send(
    200,
    "application/json",
    "{\"ok\": true, \"message\": \"turned right\"}"
  );
}

void handleForward() {
  setMotorASpeed(driveSpeed);
  forwardMotorA();
  driveDirection = "forward";

  server.send(
    200,
    "application/json",
    "{\"ok\": true, \"message\": \"forward\"}"
  );
}

void handleBackward() {
  setMotorASpeed(driveSpeed);
  backwardMotorA();
  driveDirection = "backward";

  server.send(
    200,
    "application/json",
    "{\"ok\": true, \"message\": \"backward\"}"
  );
}

void handleStop() {
  stopAllMotors();

  driveDirection = "idle";
  steeringDirection = "idle";

  server.send(
    200,
    "application/json",
    "{\"ok\": true, \"message\": \"stopped\"}"
  );
}

void handleSetSpeed() {
  if (!server.hasArg("speed")) {
    server.send(400, "application/json", "{\"ok\": false, \"error\": \"missing speed\"}");
    return;
  }

  driveSpeed = constrain(server.arg("speed").toInt(), 0, 255);

  String json = "{";
  json += "\"ok\": true,";
  json += "\"message\": \"speed updated\",";
  json += "\"driveSpeed\": " + String(driveSpeed);
  json += "}";

  server.send(200, "application/json", json);
}

void handleNotFound() {
  server.send(
    404,
    "application/json",
    "{\"ok\": false, \"error\": \"not found\"}"
  );
}

void initWiFi() {
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  server.on("/api/rc/left", HTTP_POST, handleLeft);
  server.on("/api/rc/right", HTTP_POST, handleRight);

  server.on("/api/rc/forward", HTTP_POST, handleForward);
  server.on("/api/rc/backward", HTTP_POST, handleBackward);
  server.on("/api/rc/stop", HTTP_POST, handleStop);

  server.on("/api/rc/setSpeed", HTTP_POST, handleSetSpeed);

  server.on("/api/rc/status", HTTP_GET, handleStatus);

  server.onNotFound(handleNotFound);

  server.begin();

  Serial.println("RESTful API started");
}

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println();
  Serial.println("Booting...");

  initialisePins();
  stopAllMotors();

  initWiFi();
}

void loop() {
  server.handleClient();
}