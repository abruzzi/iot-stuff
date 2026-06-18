#include <WiFi.h>
#include <WebServer.h>

const int RELAY_PIN = 5;

const int RELAY_ON = HIGH;
const int RELAY_OFF = LOW;

WebServer server(80);

const char* ssid = "YOU_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

void triggerRelay() {
  Serial.println("Trigger relay");

  digitalWrite(RELAY_PIN, RELAY_ON);
  delay(500);
  digitalWrite(RELAY_PIN, RELAY_OFF);

  Serial.println("Relay done");
}

void handleTrigger() {
  triggerRelay();

  server.send(
    200,
    "application/json",
    "{\"ok\": true, \"message\": \"trigger sent\"}"
  );
}

void handleStatus() {
  server.send(
    200,
    "application/json",
    "{\"ok\": true, \"relay\": \"idle\"}"
  );
}


void handleNotFound() {
  server.send(
    404,
    "application/json",
    "{\"ok\": false, \"error\": \"not found\"}"
  );
}

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println();
  Serial.println("Booting...");
  
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, RELAY_OFF);

  Serial.println("Starting RESTful API...");

  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  server.on("/api/garage/trigger", HTTP_POST, handleTrigger);
  server.on("/api/garage/status", HTTP_GET, handleStatus);

  server.onNotFound(handleNotFound);

  server.begin();

  Serial.println("RESTful API started");
}

void loop() {
  server.handleClient();
}