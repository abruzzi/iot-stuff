# Cameraman

Python + Arduino experiments for camera-based computer vision, with serial control of servos, 7-segment displays, and LCD screens.

## Setup

```bash
pip install -r requirements.txt
```

Key dependencies: `opencv-python`, `mediapipe`, `face_recognition`, `pyserial`, `tensorflow`/`keras`, `piper-tts`.

Ignored locally (not in git): `images/` (known face photos), `voices/` (Piper TTS model), `digit_model.keras` (trained model — generate with training script).

---

## Face Related

### Evolution

1. Basic webcam + OpenCV Haar cascade (`face_detect.py`)
2. Switched to MediaPipe for better detection (`face_detect_mediapipe.py`)
3. Added face recognition against a photo library (`face_recognise.py`)
4. Stabilised recognition so labels don't flicker
5. Face tracking → servo pan to keep face centred (`face_detect_track.py`)

### Python files

| File | Purpose |
|------|---------|
| `face_detect.py` | Earliest version. OpenCV `haarcascade_frontalface_default.xml`, draws purple boxes on detected faces. |
| `face_detect_mediapipe.py` | MediaPipe `FaceDetection` (model 0, confidence 0.6). More accurate than Haar cascade. |
| `face_recognise.py` | Identifies people using the `face_recognition` library. Loads encodings from `images/known_faces/<name>/*.jpg`. Uses distance threshold `< 0.5`. Stability: requires 3 of last 5 frames to agree before showing a name. Processes every other frame at 1/4 resolution for speed. |
| `face_detect_track.py` | Full tracking pipeline. Detects largest face, pans a servo to centre it. |

### Face tracking details (`face_detect_track.py`)

- **Serial command:** `PAN:<delta>` (degrees to move servo)
- **Arduino sketch:** `arduino/servo_pan.ino`
- **Stability:** face must be detected in 3 of last 5 frames before panning starts
- **Smoothing:** exponential moving average on face x-position (`SMOOTHING_ALPHA = 0.3`)
- **Angle math:** converts pixel offset from frame centre to degrees using assumed 90° horizontal FOV
- **Control:** proportional gain `KP = 0.5`, max step `MAX_STEP_DEG = 5`, angle dead zone `3°`
- **Rate limiting:** commands sent at most every 50 ms

### Arduino files

| File | Purpose |
|------|---------|
| `arduino/servo.ino` | Early prototype. Servo on pin 9. Commands: `LEFT` (+2°), `RIGHT` (-2°). |
| `arduino/servo_pan.ino` | Production version for tracking. Commands: `LEFT`, `RIGHT`, `CENTER`, `PAN:<delta>`. Servo on pin 9, constrained 0–180°. |

### Known faces setup

Put one folder per person under `images/known_faces/`:

```
images/known_faces/
  Alice/
    photo1.jpg
    photo2.png
  Bob/
    photo1.jpg
```

Folder name becomes the displayed label.

---

## Number Related

### Evolution

1. Basic 7-segment display toggling digits 1 and 2 (`arduino/number_7_seg.ino`)
2. Full 0–9 segment patterns, cycling in a loop (`arduino/numbers_7_seg.ino`)
3. Trained MNIST CNN model (`number_recognise_train_model.py`)
4. Live camera recognition → serial → 7-segment display (`number_recognise.py` + `arduino/number_series.ino`)

### Python files

| File | Purpose |
|------|---------|
| `number_recognise_train_model.py` | Trains a small CNN on MNIST (10 epochs). Architecture: 2× Conv2D + MaxPool → Dropout → Dense softmax. Saves `digit_model.keras`. |
| `number_recognise.py` | Live digit recognition from webcam. Preprocesses centre ROI → grayscale → Otsu threshold → largest contour → resize to 28×28 (MNIST format). Sends result to Arduino. |

### Recognition pipeline details (`number_recognise.py`)

- **Model input:** 28×28 grayscale, white digit on black background (inverted threshold)
- **Confidence gate:** only accepts predictions with confidence > 0.95
- **Stability:** digit must appear in 3 of last 5 frames before sending
- **Serial commands:**
  - `NUMBER:<digit>` — show recognised digit (0–9)
  - `PLACEHOLDER` — nothing confident detected (shows `-` on display)
- **Rate limiting:** won't resend same command within 0.5 s

### Arduino files

| File | Purpose |
|------|---------|
| `arduino/number_7_seg.ino` | Learning prototype. Alternates displaying `1` and `2` every second. |
| `arduino/numbers_7_seg.ino` | Segment lookup table for all digits 0–9. Cycles 0→9 in `loop()`. |
| `arduino/number_series.ino` | Serial-controlled version. Parses `NUMBER:<digit>`, displays on 7-seg. Unknown commands show placeholder (`-` via segment g). |

### 7-segment wiring

Segments a–g on Arduino pins 2–8:

```
Pin 2 = a    Pin 5 = d
Pin 3 = b    Pin 6 = e
Pin 4 = c    Pin 7 = f
             Pin 8 = g
```

---

## Other Stuff

### Hand gesture + speech (`hand_recoginise.py`)

- MediaPipe Hands (single hand, confidence 0.7)
- Classifies gestures by counting raised fingers: `FIST`, `ONE`, `TWO`, `THREE`, `OPEN_HAND`
- Stability: 4 of last 5 frames must agree
- Speaks via Piper TTS (`voices/en_US-libritts-high.onnx`) + macOS `afplay`
- Cooldown: 1.5 s between spoken gestures, won't repeat same gesture

### HTTP streaming → LCD (`streaming-ui.py` + `arduino/streaming_lcd.ino`)

- Reads a streaming HTTP API at `http://127.0.0.1:8788/api/stream` (POST, newline-delimited JSON)
- Buffers incoming text into a 32-char rolling window, split into two 16-char LCD lines
- **Serial command:** `LCD:<line1>|<line2>`
- **Baud rate:** 115200 (unlike most other sketches which use 9600)
- Arduino: I2C LCD at address `0x27`, 16×2 characters

### Static LCD demo (`arduino/lcd.ino`)

- Simple "Luna Qiu / Student Council" message on boot. No serial.

### Serial test (`serial_test.py`)

- Sends `LEFT` / `RIGHT` to Arduino to verify servo wiring. Pairs with `arduino/servo.ino`.

---

## Serial Port Cheat Sheet

Each script hardcodes a port — update to match your board (`/dev/cu.usbmodem*` on Mac):

| Script | Port | Baud |
|--------|------|------|
| `face_detect_track.py` | `/dev/cu.usbmodem11101` | 9600 |
| `number_recognise.py` | `/dev/cu.usbmodem1301` | 9600 |
| `streaming-ui.py` | `/dev/cu.usbmodem21201` | 115200 |
| `serial_test.py` | `/dev/cu.usbmodem11301` | 9600 |

Always `time.sleep(2)` after opening serial, then `reset_input_buffer()`.

---

## Common Patterns Used Across Scripts

1. **Stability via sliding window** — `collections.deque` + `Counter` to avoid flickering detections (faces, digits, gestures)
2. **Rate-limited serial** — don't flood Arduino; track `last_sent_time` and skip duplicate commands
3. **Debug windows** — OpenCV `imshow` for live preview; number recognition also shows threshold and 28×28 model input
4. **Serial protocol** — newline-terminated text commands (`COMMAND:value\n`), Arduino reads with `readStringUntil('\n')`

---

## Quick Run Reference

```bash
# Face detection (MediaPipe)
python face_detect_mediapipe.py

# Face recognition (needs images/known_faces/)
python face_recognise.py

# Face tracking + servo pan (flash arduino/servo_pan.ino first)
python face_detect_track.py

# Train digit model (one-time)
python number_recognise_train_model.py

# Digit recognition + 7-seg (flash arduino/number_series.ino first)
python number_recognise.py

# Hand gestures + TTS (needs voices/ model)
python hand_recoginise.py

# Stream text to LCD (flash arduino/streaming_lcd.ino first)
python streaming-ui.py
```

Press `q` to quit any OpenCV window.
