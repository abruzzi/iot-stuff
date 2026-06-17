import cv2
import mediapipe as mp
import subprocess
import tempfile
import os
import time
from collections import deque, Counter

PIPER_MODEL = "voices/en_US-libritts-high.onnx"

AUDIO_PLAYER = "afplay"

SPEAK_COOLDOWN = 1.5

last_spoken_gesture = None
last_spoken_time = 0

recent_gestures = deque(maxlen=5)

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
)


def speak(text):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output_path = f.name

    try:
        subprocess.run(
            [
                "piper",
                "--model",
                PIPER_MODEL,
                "--output_file",
                output_path,
            ],
            input=text.encode("utf-8"),
            check=True,
        )

        subprocess.run([AUDIO_PLAYER, output_path], check=True)
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def is_finger_up(landmarks, tip_id, pip_id):
    # In image coordinates, smaller y means higher on screen.
    return landmarks[tip_id].y < landmarks[pip_id].y


def classify_gesture(hand_landmarks):
    landmarks = hand_landmarks.landmark

    index_up = is_finger_up(landmarks, 8, 6)
    middle_up = is_finger_up(landmarks, 12, 10)
    ring_up = is_finger_up(landmarks, 16, 14)
    pinky_up = is_finger_up(landmarks, 20, 18)

    fingers = [index_up, middle_up, ring_up, pinky_up]
    count = sum(fingers)

    if count == 0:
        return "FIST"

    if count == 1 and index_up:
        return "ONE"

    if count == 2 and index_up and middle_up:
        return "TWO"

    if count == 3 and index_up and middle_up and ring_up:
        return "THREE"

    if count == 4:
        return "OPEN_HAND"

    return "UNKNOWN"


def get_stable_gesture():
    if len(recent_gestures) < recent_gestures.maxlen:
        return None

    gesture, count = Counter(recent_gestures).most_common(1)[0]

    if count >= 4:
        return gesture

    return None


def speak_gesture_if_needed(gesture):
    global last_spoken_gesture
    global last_spoken_time

    if gesture is None or gesture == "UNKNOWN":
        return

    now = time.time()

    if gesture == last_spoken_gesture:
        return

    if now - last_spoken_time < SPEAK_COOLDOWN:
        return

    print("Speaking:", gesture)
    speak(f"I see {gesture.lower().replace('_', ' ')}")

    last_spoken_gesture = gesture
    last_spoken_time = now


cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()

    if not ret:
        break

    frame = cv2.flip(frame, 1)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    current_gesture = "NO_HAND"

    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]

        current_gesture = classify_gesture(hand_landmarks)
        recent_gestures.append(current_gesture)

        stable_gesture = get_stable_gesture()
        speak_gesture_if_needed(stable_gesture)

        mp_draw.draw_landmarks(
            frame,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS,
        )

    cv2.putText(
        frame,
        f"Gesture: {current_gesture}",
        (30, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
    )

    cv2.imshow("Hand Gesture Speaker", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
hands.close()