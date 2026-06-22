import cv2
import mediapipe as mp
from collections import deque, Counter
import time

from logger import debug_log, close_logger
from playwright_controller import open_dino

# -----------------------------
# MediaPipe setup
# -----------------------------

mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.6,
)

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
)

# -----------------------------
# Gesture detection
# -----------------------------

recent_gestures = deque(maxlen=5)

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

# -----------------------------
# Face detection
# -----------------------------

recent_face_detections = deque(maxlen=5)

def is_face_stably_detected():
    return sum(recent_face_detections) >= 2

def get_largest_detection(detections, frame_width, frame_height):
    def area(detection):
        bbox = detection.location_data.relative_bounding_box
        return bbox.width * frame_width * bbox.height * frame_height

    return max(detections, key=area)

def get_face_center_y(frame, face_results):
    h_img, w_img, _ = frame.shape

    face_detected = bool(face_results.detections)
    recent_face_detections.append(face_detected)

    if not is_face_stably_detected():
        return None, None

    if not face_results.detections:
        return None, None

    detection = get_largest_detection(face_results.detections, w_img, h_img)
    bbox = detection.location_data.relative_bounding_box

    x = int(bbox.xmin * w_img)
    y = int(bbox.ymin * h_img)
    w = int(bbox.width * w_img)
    h = int(bbox.height * h_img)

    center_y = int(y + h / 2)
    box = (x, y, w, h)

    return center_y, box

# -----------------------------
# Game state
# -----------------------------

dino_controller = None

game_state = "WAITING_FOR_READY"

ready_started_at = None
READY_HOLD_SECONDS = 2.0

calibration_started_at = None
calibration_samples = []
CALIBRATION_SECONDS = 2.0

baseline_y = None
smoothed_y = None
last_y = None
last_time = None
last_jump_time = 0
crouch_started_at = None

SMOOTHING_ALPHA = 0.45

CROUCH_THRESHOLD = 28
LANDING_THRESHOLD = 12

JUMP_VELOCITY_THRESHOLD = 320      # pixels / second
REBOUND_VELOCITY_THRESHOLD = 260   # pixels / second
LIFT_THRESHOLD = 6

COOLDOWN_SECONDS = 0.25
CROUCH_MAX_SECONDS = 0.7

def reset_jump_detector():
    global calibration_started_at, calibration_samples
    global baseline_y, smoothed_y, last_y, last_time
    global last_jump_time, crouch_started_at

    calibration_started_at = None
    calibration_samples = []
    baseline_y = None
    smoothed_y = None
    last_y = None
    last_time = None
    last_jump_time = 0
    crouch_started_at = None

def smooth_y(current_y):
    global smoothed_y

    if smoothed_y is None:
        smoothed_y = current_y
    else:
        smoothed_y = (
            SMOOTHING_ALPHA * current_y
            + (1 - SMOOTHING_ALPHA) * smoothed_y
        )

    return smoothed_y

def can_press_space(now):
    return now - last_jump_time >= COOLDOWN_SECONDS


LOG_AFTER_JUMP = False
CHECK_JUMP_RESULT = True

def press_space(reason=None):
    if dino_controller is None:
        return

    before = dino_controller.read_state()
    obstacle = before.get("obstacle")

    debug_log(
        "game",
        "before_jump",
        reason=reason,
        jumping=before["jumping"],
        ducking=before["ducking"],
        speed=round(before["speed"], 2),
        obstacle_type=obstacle["type"] if obstacle else None,
        distance=round(obstacle["distance"], 1) if obstacle else None,
    )

    dino_controller.jump()

    if CHECK_JUMP_RESULT:
        time.sleep(0.03)
        after = dino_controller.read_state()
        debug_log(
            "game",
            "jump_result",
            reason=reason,
            jumping=after["jumping"],
            trexY=round(after["trexY"], 1),
        )

def update_ready_state(stable_gesture):
    global game_state, ready_started_at

    now = time.time()

    if stable_gesture == "OPEN_HAND":
        if ready_started_at is None:
            ready_started_at = now

        held_for = now - ready_started_at

        if held_for >= READY_HOLD_SECONDS:
            print("Ready gesture detected. Start calibration.")
            reset_jump_detector()
            game_state = "CALIBRATING"
            ready_started_at = None
    else:
        ready_started_at = None

def update_jump_detector(current_raw_y):
    global game_state
    global calibration_started_at, calibration_samples
    global baseline_y, last_y, last_time
    global last_jump_time, crouch_started_at

    now = time.time()
    current_y = smooth_y(current_raw_y)

    # -----------------------------
    # Calibration
    # -----------------------------
    if game_state == "CALIBRATING":
        if calibration_started_at is None:
            calibration_started_at = now
            calibration_samples = []
            debug_log("camera", "calibration_started")
            print("Calibrating... stand still.")

        calibration_samples.append(current_y)

        if now - calibration_started_at >= CALIBRATION_SECONDS:
            baseline_y = sum(calibration_samples) / len(calibration_samples)
            last_y = current_y
            last_time = now
            game_state = "IDLE"

            debug_log(
                "camera",
                "calibration_done",
                game_state=game_state,
                y=round(current_y, 1),
                baseline=round(baseline_y, 1),
            )

            print(f"Calibration done. baseline_y={baseline_y:.1f}")

        return

    if game_state not in ["IDLE", "CROUCHING", "JUMPING", "COOLDOWN"]:
        return

    if baseline_y is None:
        return

    if last_y is None or last_time is None:
        last_y = current_y
        last_time = now
        return

    dt = now - last_time

    if dt <= 0 or dt > 0.3:
        last_y = current_y
        last_time = now

        debug_log(
            "camera",
            "frame_gap_ignored",
            game_state=game_state,
            dt=round(dt, 3),
        )

        return

    # screen y: smaller = higher
    # positive velocity = moving up
    velocity_y = (last_y - current_y) / dt

    last_y = current_y
    last_time = now

    is_crouching = current_y > baseline_y + CROUCH_THRESHOLD
    is_lifted = current_y < baseline_y - LIFT_THRESHOLD
    moving_up_fast = velocity_y > JUMP_VELOCITY_THRESHOLD
    rebounding_up = velocity_y > REBOUND_VELOCITY_THRESHOLD
    landed = current_y > baseline_y - LANDING_THRESHOLD

    if game_state == "IDLE":
        # Slowly adapt baseline only when the player is stable.
        if abs(velocity_y) < 80 and not is_crouching and not is_lifted:
            baseline_y = baseline_y * 0.98 + current_y * 0.02

        if is_crouching:
            game_state = "CROUCHING"
            crouch_started_at = now

            debug_log(
                "camera",
                "crouching",
                game_state=game_state,
                y=round(current_y, 1),
                baseline=round(baseline_y, 1),
                velocity=round(velocity_y, 1),
            )

            return

        if moving_up_fast and is_lifted:
            debug_log(
                "camera",
                "jump_candidate",
                reason="direct_lift",
                game_state=game_state,
                y=round(current_y, 1),
                baseline=round(baseline_y, 1),
                velocity=round(velocity_y, 1),
                cooldown=round(now - last_jump_time, 3),
            )

            if can_press_space(now):
                press_space(reason="direct_lift")
                last_jump_time = now
                game_state = "JUMPING"

                debug_log(
                    "camera",
                    "jump_triggered",
                    reason="direct_lift",
                    game_state=game_state,
                    y=round(current_y, 1),
                    baseline=round(baseline_y, 1),
                    velocity=round(velocity_y, 1),
                )

                print(
                    f"Jump: direct lift, velocity={velocity_y:.1f}, "
                    f"y={current_y:.1f}, baseline={baseline_y:.1f}"
                )
            else:
                debug_log(
                    "camera",
                    "jump_blocked",
                    reason="cooldown",
                    game_state=game_state,
                    cooldown=round(now - last_jump_time, 3),
                )

                print("Jump ignored: cooldown")

            return

    elif game_state == "CROUCHING":
        if rebounding_up:
            debug_log(
                "camera",
                "jump_candidate",
                reason="crouch_rebound",
                game_state=game_state,
                y=round(current_y, 1),
                baseline=round(baseline_y, 1),
                velocity=round(velocity_y, 1),
                crouch_for=round(now - crouch_started_at, 3)
                if crouch_started_at is not None
                else None,
                cooldown=round(now - last_jump_time, 3),
            )

            if can_press_space(now):
                press_space(reason="crouch_rebound")
                last_jump_time = now
                game_state = "JUMPING"

                debug_log(
                    "camera",
                    "jump_triggered",
                    reason="crouch_rebound",
                    game_state=game_state,
                    y=round(current_y, 1),
                    baseline=round(baseline_y, 1),
                    velocity=round(velocity_y, 1),
                )

                print(
                    f"Jump: crouch rebound, velocity={velocity_y:.1f}, "
                    f"y={current_y:.1f}, baseline={baseline_y:.1f}"
                )
            else:
                debug_log(
                    "camera",
                    "jump_blocked",
                    reason="cooldown",
                    game_state=game_state,
                    cooldown=round(now - last_jump_time, 3),
                )

                print("Jump ignored: cooldown")

            return

        if crouch_started_at is not None and now - crouch_started_at > CROUCH_MAX_SECONDS:
            debug_log(
                "camera",
                "crouch_timeout",
                game_state=game_state,
                y=round(current_y, 1),
                baseline=round(baseline_y, 1),
                velocity=round(velocity_y, 1),
                crouch_for=round(now - crouch_started_at, 3),
            )

            game_state = "IDLE"
            crouch_started_at = None
            return

    elif game_state == "JUMPING":
        if landed:
            game_state = "COOLDOWN"

            debug_log(
                "camera",
                "landed",
                game_state=game_state,
                y=round(current_y, 1),
                baseline=round(baseline_y, 1),
                velocity=round(velocity_y, 1),
            )

            return

    elif game_state == "COOLDOWN":
        if now - last_jump_time >= COOLDOWN_SECONDS:
            game_state = "IDLE"

            debug_log(
                "camera",
                "cooldown_done",
                game_state=game_state,
                cooldown=round(now - last_jump_time, 3),
            )

            return

# -----------------------------
# Debug drawing
# -----------------------------

def draw_debug_info(frame, current_y=None, stable_gesture=None):
    h_img, w_img, _ = frame.shape

    if baseline_y is not None:
        cv2.line(
            frame,
            (0, int(baseline_y)),
            (w_img, int(baseline_y)),
            (0, 255, 255),
            2,
        )

    if current_y is not None:
        cv2.circle(
            frame,
            (int(w_img / 2), int(current_y)),
            5,
            (255, 0, 0),
            -1,
        )

    cv2.putText(
        frame,
        f"State: {game_state}",
        (30, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 255, 0),
        2,
    )

    cv2.putText(
        frame,
        f"Gesture: {stable_gesture}",
        (30, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 255, 0),
        2,
    )

    if game_state == "WAITING_FOR_READY":
        message = "Stand ready, then open hand for 2 seconds"
        cv2.putText(
            frame,
            message,
            (30, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
        )

    if game_state == "CALIBRATING":
        message = "Calibrating... stand still"
        cv2.putText(
            frame,
            message,
            (30, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
        )

# -----------------------------
# Main loop
# -----------------------------

playwright, browser, page, dino_controller = open_dino()

cap = cv2.VideoCapture(0)

# Lower resolution usually means lower latency.
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

frame_count = 0
fps_started_at = time.time()

was_crashed = False

while True:
    ret, frame = cap.read()

    if not ret:
        break

    frame = cv2.flip(frame, 1)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    hand_results = hands.process(rgb)
    face_results = face_detection.process(rgb)

    current_gesture = "NO_HAND"
    stable_gesture = None

    if hand_results.multi_hand_landmarks:
        hand_landmarks = hand_results.multi_hand_landmarks[0]
        current_gesture = classify_gesture(hand_landmarks)
        recent_gestures.append(current_gesture)
        stable_gesture = get_stable_gesture()

        mp_draw.draw_landmarks(
            frame,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS,
        )
    else:
        recent_gestures.append("NO_HAND")

    frame_count += 1

    now = time.time()
    if now - fps_started_at >= 2:
        debug_log(
            "camera",
            "fps",
            fps=round(frame_count / (now - fps_started_at), 1),
        )
        frame_count = 0
        fps_started_at = now        

    if game_state == "WAITING_FOR_READY":
        update_ready_state(stable_gesture)
    else:
        current_face_center_y, box = get_face_center_y(frame, face_results)

        if current_face_center_y is not None:
            update_jump_detector(current_face_center_y)

        if box is not None:
            x, y, w, h = box
            cv2.rectangle(frame, (x, y), (x + w, y + h), (80, 48, 230), 2)

    draw_debug_info(frame, stable_gesture=stable_gesture)

    if dino_controller is not None:
        crashed, game_snapshot = dino_controller.is_crashed()

        if crashed and not was_crashed:
            obstacle = game_snapshot.get("obstacle")

            debug_log(
                "game",
                "crashed",
                jumping=game_snapshot["jumping"],
                ducking=game_snapshot["ducking"],
                speed=round(game_snapshot["speed"], 2),
                obstacle_type=obstacle["type"] if obstacle else None,
                distance=round(obstacle["distance"], 1) if obstacle else None,
            )

        was_crashed = crashed

    cv2.imshow("Dino Jump Controller", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    # Optional: press r to reset to waiting mode.
    if key == ord("r"):
        print("Reset to WAITING_FOR_READY")
        game_state = "WAITING_FOR_READY"
        ready_started_at = None
        was_crashed = False
        reset_jump_detector()

cap.release()
cv2.destroyAllWindows()

hands.close()
face_detection.close()

browser.close()
playwright.stop()

close_logger()