#include <Adafruit_SSD1306.h>

// made by ultramegabombastiucfuze on https://projecthub.arduino.cc/

#define BUTTON_PIN 13  // button pin 

// Game state variables
bool isJumping = false;
bool gameOver = false;
int dinoY = 40;
int velocity = 0;
const int gravity = 2;
const int groundY = 40;
int cactusX1 = 128;
int cactusX2 = 180;
int gameSpeed = 3;
unsigned long lastSpeedIncrease = 0;
unsigned long lastFrame = 0;
unsigned long score = 0;

// Button debounce state
bool buttonPressed = false;

Adafruit_SSD1306 display(128, 64, &Wire, -1);

void setup() {
    pinMode(BUTTON_PIN, INPUT_PULLUP);  // Enable internal pull-up

    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
        while (1);
    }

    display.clearDisplay();
    display.display();
    randomSeed(analogRead(0));  // Randomize cactus spawn
}

void loop() {
    unsigned long currentTime = millis();
    if (currentTime - lastFrame < 50) return;
    lastFrame = currentTime;

    int buttonState = digitalRead(BUTTON_PIN);

    // --- GAME OVER & RESTART HANDLING ---
    if (gameOver) {
        if (buttonState == HIGH && !buttonPressed) {
            buttonPressed = true;
        }

        if (buttonState == LOW && buttonPressed) {
            buttonPressed = false;
            resetGame();
        }

        return;
    }

    // --- JUMP HANDLING ---
    if (buttonState == HIGH && !buttonPressed && dinoY == groundY) {
        buttonPressed = true;
        isJumping = true;
        velocity = -13;
    }

    if (buttonState == LOW) {
        buttonPressed = false;
    }

    // --- PHYSICS ---
    if (isJumping) {
        dinoY += velocity;
        velocity += gravity;
        if (dinoY >= groundY) {
            dinoY = groundY;
            isJumping = false;
        }
    }

    // --- MOVE CACTI ---
    cactusX1 -= gameSpeed;
    cactusX2 -= gameSpeed;

    if (cactusX1 < -10) {
        cactusX1 = 128 + random(0, 40);
        if (random(0, 10) > 6) cactusX2 = cactusX1 + random(15, 30);
    }
    if (cactusX2 < -10) {
        cactusX2 = 128 + random(30, 60);
    }

    // --- SPEED UP ---
    if (currentTime - lastSpeedIncrease > 3000) {
        gameSpeed++;
        lastSpeedIncrease = currentTime;
    }

    // --- SCORE ---
    score++;

    // --- DRAW SCENE ---
    display.clearDisplay();
    
    drawDino(10, dinoY);
    drawCactus(cactusX1, 58);
    drawCactus(cactusX2, 58);

    display.drawLine(0, 58, 128, 58, SSD1306_WHITE);            // Ground
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.print("Score: ");
    display.print(score / 10);
    display.display();

    // --- COLLISION DETECTION ---
    bool hitCactus1 = (cactusX1 < 20 && cactusX1 > 5 && dinoY == groundY);
    bool hitCactus2 = (cactusX2 < 20 && cactusX2 > 5 && dinoY == groundY);

    if (hitCactus1 || hitCactus2) {
        gameOver = true;
        display.clearDisplay();
        display.setTextSize(2);
        display.setCursor(20, 20);
        display.print("Game Over");
        display.setTextSize(1);
        display.setCursor(10, 45);
        display.print("Press to restart");
        display.display();
    }
}

// --- RESTART GAME FUNCTION ---
void resetGame() {
    isJumping = false;
    dinoY = groundY;
    velocity = 0;
    cactusX1 = 128;
    cactusX2 = 180;
    gameSpeed = 3;
    score = 0;
    gameOver = false;
    lastSpeedIncrease = millis();
    lastFrame = millis();
    display.clearDisplay();
    display.display();
}

void drawDino(int x, int y) {
    // body
    display.fillRect(x + 2, y + 6, 10, 8, SSD1306_WHITE);

    // head
    display.fillRect(x + 10, y + 2, 8, 7, SSD1306_WHITE);

    // mouth
    display.drawPixel(x + 17, y + 5, SSD1306_BLACK);

    // eye
    display.drawPixel(x + 14, y + 4, SSD1306_BLACK);

    // tail
    display.drawLine(x + 2, y + 8, x - 3, y + 5, SSD1306_WHITE);

    // legs
    display.drawLine(x + 5, y + 14, x + 4, y + 18, SSD1306_WHITE);
    display.drawLine(x + 10, y + 14, x + 12, y + 18, SSD1306_WHITE);

    // tiny arm
    display.drawPixel(x + 12, y + 10, SSD1306_WHITE);
    display.drawPixel(x + 13, y + 10, SSD1306_WHITE);
}

void drawCactus(int x, int y) {
    // main stem
    display.fillRect(x + 4, y - 16, 4, 16, SSD1306_WHITE);

    // left arm
    display.fillRect(x, y - 11, 4, 4, SSD1306_WHITE);
    display.fillRect(x, y - 14, 2, 5, SSD1306_WHITE);

    // right arm
    display.fillRect(x + 8, y - 8, 4, 4, SSD1306_WHITE);
    display.fillRect(x + 10, y - 11, 2, 5, SSD1306_WHITE);
}