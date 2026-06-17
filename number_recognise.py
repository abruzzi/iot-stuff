import cv2
import serial
import time
import numpy as np
from tensorflow.keras.models import load_model
from collections import deque, Counter

history = deque(maxlen=5)

model = load_model("digit_model.keras")

arduino = serial.Serial('/dev/cu.usbmodem1301', 9600, timeout=1)
time.sleep(2)

arduino.reset_input_buffer()

last_sent_time = 0
last_sent_command = None
SEND_INTERVAL = 0.5

def send_command(command):
    global last_sent_time, last_sent_command

    if command == last_sent_command:
        return
    
    now = time.time()

    if now - last_sent_time < SEND_INTERVAL:
        return
    
    arduino.write(f"{command}\n".encode('utf-8'))
    arduino.flush()

    last_sent_time = now
    last_sent_command = command
    print('sent', command)

    time.sleep(0.05)

    while arduino.in_waiting > 0:
        line = arduino.readline().decode("utf-8", errors="ignore").strip()
        print("arduino:", line)

def preprocess_digit(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    h, w = gray.shape

    box_size = min(h, w) // 2
    x1 = w // 2 - box_size // 2
    y1 = h // 2 - box_size // 2

    roi = gray[y1:y1 + box_size, x1:x1 + box_size]

    blurred = cv2.GaussianBlur(roi, (5, 5), 0)

    _, threshold = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    contours, _ = cv2.findContours(
        threshold,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if len(contours) == 0:
        return None, np.zeros((28, 28), dtype=np.uint8), roi, threshold

    largest = max(contours, key=cv2.contourArea)

    if cv2.contourArea(largest) < 100:
        return None, np.zeros((28, 28), dtype=np.uint8), roi, threshold

    x, y, w, h = cv2.boundingRect(largest)

    if w < 5 or h < 5:
        return None, np.zeros((28, 28), dtype=np.uint8), roi, threshold

    digit = threshold[y:y+h, x:x+w]

    digit_h, digit_w = digit.shape

    if digit_h <= 0 or digit_w <= 0:
        return None, np.zeros((28, 28), dtype=np.uint8), roi, threshold

    if digit_h > digit_w:
        new_h = 20
        new_w = int(digit_w * 20 / digit_h)
    else:
        new_w = 20
        new_h = int(digit_h * 20 / digit_w)

    if new_w <= 0 or new_h <= 0:
        return None, np.zeros((28, 28), dtype=np.uint8), roi, threshold

    digit = cv2.resize(digit, (new_w, new_h))

    canvas = np.zeros((28, 28), dtype=np.uint8)

    x_offset = (28 - new_w) // 2
    y_offset = (28 - new_h) // 2

    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = digit

    image = canvas.astype("float32") / 255.0
    image = np.expand_dims(image, axis=-1)
    image = np.expand_dims(image, axis=0)

    return image, canvas, roi, threshold

def detect_number_from_frame(frame):
    image, model_input, _, threshold = preprocess_digit(frame)

    cv2.imshow("threshold", threshold)

    preview = cv2.resize(
        model_input,
        (280, 280),
        interpolation=cv2.INTER_NEAREST
    )
    cv2.imshow("model input", preview)

    if image is None:
        return None

    predictions = model.predict(image, verbose=0)[0]

    digit = int(np.argmax(predictions))
    confidence = float(np.max(predictions))

    print("digit:", digit, "confidence:", confidence)

    if confidence > 0.95:
        history.append(digit)
    else:
        history.clear()
        return None

    counts = Counter(history)
    winner, count = counts.most_common(1)[0]

    if count >= 3:
        return winner

    return None

video_capture = cv2.VideoCapture(0)

while True:
    ret, frame = video_capture.read()

    if ret is False:
        break

    h, w, _ = frame.shape

    box_size = min(h, w) // 2
    x1 = w // 2 - box_size // 2
    y1 = h // 2 - box_size // 2

    cv2.rectangle(
        frame,
        (x1, y1),
        (x1 + box_size, y1 + box_size),
        (0, 255, 0),
        2
    )

    center_x = w // 2
    center_y = h // 2

    cv2.line(frame, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 0), 1)
    cv2.line(frame, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 0), 1)

    digit = detect_number_from_frame(frame)
    if digit is None:
        send_command(f"PLACEHOLDER")
    else:
        send_command(f"NUMBER:{digit}")

    cv2.imshow('cameraman', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video_capture.release()
cv2.destroyAllWindows()
