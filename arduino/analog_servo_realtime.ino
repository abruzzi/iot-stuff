#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Servo.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

int servoPin = 9;
int potPin = A0;

Servo servo;

// 保存最近 128 个 analog value
int history[SCREEN_WIDTH];

void setup() {
  servo.attach(servoPin);

  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) for(;;);

  display.clearDisplay();
  display.setTextSize(1);             
  display.setTextColor(SSD1306_WHITE); 
  
  // 初始化波形数据，先都放在中间值
  for (int i = 0; i < SCREEN_WIDTH; i++) {
    history[i] = 512;
  }

  display.display();
}

void updateHistory(int value) {
  // 把所有旧数据往左移动一格
  for (int i = 0; i < SCREEN_WIDTH - 1; i++) {
    history[i] = history[i + 1];
  }

  // 最新的数据放到最右边
  history[SCREEN_WIDTH - 1] = value;
}

void displayWaveform() {
  int graphTop = 22;
  int graphBottom = 63;

  // 可选：画波形区域边框
  display.drawRect(0, graphTop, 128, graphBottom - graphTop + 1, SSD1306_WHITE);

  for (int x = 0; x < SCREEN_WIDTH - 1; x++) {
    int y1 = map(history[x], 0, 1023, graphBottom, graphTop);
    int y2 = map(history[x + 1], 0, 1023, graphBottom, graphTop);

    display.drawLine(x, y1, x + 1, y2, SSD1306_WHITE);
  }
}

void displayServoStatus(int value) {
  int angle = map(value, 0, 1023, 0, 180);

  display.clearDisplay();

  display.setCursor(0, 0);
  display.print("Servo Controller");

  display.setCursor(0, 10);
  display.print("Analog: ");
  display.print(value);

  display.setCursor(72, 10);
  display.print("A:");
  display.print(angle);

  displayWaveform();

  display.display();
}

void loop() {
  int value = analogRead(potPin);
  int angle = map(value, 0, 1023, 0, 180);

  servo.write(angle);

  updateHistory(value);
  displayServoStatus(value);

  delay(30);
}