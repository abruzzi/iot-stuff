import cv2
import mediapipe as mp
from collections import deque
import time
import pyautogui

mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.6
)

recent_face_detections = deque(maxlen=5)

def is_face_stably_detected(recent_face_detections):
    return sum(recent_face_detections) >= 2

def get_largest_detection(detections, frame_width, frame_height):
    def area(detection):
        bbox = detection.location_data.relative_bounding_box
        return bbox.width * frame_width * bbox.height * frame_height

    return max(detections, key=area)


# -----------------------------
# Jump detector state
# -----------------------------

state = "CALIBRATING"

calibration_samples = []
CALIBRATION_SECONDS = 2.0
calibration_started_at = None

baseline_y = None
smoothed_y = None
last_y = None
last_time = None
last_jump_time = 0
crouch_started_at = None

SMOOTHING_ALPHA = 0.45

# 这些阈值是像素值，先按 720p/1080p 摄像头大概调
CROUCH_THRESHOLD = 28       # 脸比 baseline 低多少，认为是下蹲
LIFT_THRESHOLD = 18         # 脸比 baseline 高多少，认为已经抬起
LANDING_THRESHOLD = 12      # 回到 baseline 附近，认为落地

# 速度单位：pixels / second
JUMP_VELOCITY_THRESHOLD = 420
REBOUND_VELOCITY_THRESHOLD = 360

COOLDOWN_SECONDS = 0.20
CROUCH_MAX_SECONDS = 0.7


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


def press_space():
    pyautogui.press("space")


def detect_jump(current_face_center_y):
    global state
    global calibration_started_at, calibration_samples
    global baseline_y, last_y, last_time, last_jump_time
    global crouch_started_at

    now = time.time()
    current_y = smooth_y(current_face_center_y)

    if last_y is None or last_time is None:
        last_y = current_y
        last_time = now
        return False

    dt = now - last_time

    # 避免极端情况：卡顿、暂停、debug 停住之后产生奇怪 velocity
    if dt <= 0 or dt > 0.3:
        last_y = current_y
        last_time = now
        return False

    # 屏幕坐标：y 越小，位置越高
    # 所以 last_y - current_y > 0 表示向上移动
    velocity_y = (last_y - current_y) / dt

    last_y = current_y
    last_time = now

    # -----------------------------
    # Calibration
    # -----------------------------
    if state == "CALIBRATING":
        if calibration_started_at is None:
            calibration_started_at = now
            calibration_samples = []

        calibration_samples.append(current_y)

        if now - calibration_started_at >= CALIBRATION_SECONDS:
            baseline_y = sum(calibration_samples) / len(calibration_samples)
            state = "IDLE"
            print(f"Calibration done. baseline_y={baseline_y:.1f}")

        return False

    if baseline_y is None:
        return False

    # -----------------------------
    # Derived signals
    # -----------------------------
    is_crouching = current_y > baseline_y + CROUCH_THRESHOLD
    is_lifted = current_y < baseline_y - LIFT_THRESHOLD
    moving_up_fast = velocity_y > JUMP_VELOCITY_THRESHOLD
    rebounding_up = velocity_y > REBOUND_VELOCITY_THRESHOLD
    landed = current_y > baseline_y - LANDING_THRESHOLD

    if now - last_jump_time < COOLDOWN_SECONDS:
        return False

    # -----------------------------
    # State machine
    # -----------------------------
    if state == "IDLE":
        # 只有人比较稳定时，慢慢更新 baseline
        # 这样她站的位置轻微变化时，系统可以适应
        if abs(velocity_y) < 80 and not is_crouching and not is_lifted:
            baseline_y = baseline_y * 0.98 + current_y * 0.02

        # 先蹲下，进入 armed 状态
        if is_crouching:
            state = "CROUCHING"
            crouch_started_at = now
            return False

        # 不蹲，直接向上跳，也可以触发
        if moving_up_fast and is_lifted:
            press_space()
            last_jump_time = now
            state = "JUMPING"
            print("Jump: direct lift")
            return True

    elif state == "CROUCHING":
        # 从蹲下状态快速向上，尽早触发
        if rebounding_up:
            press_space()
            last_jump_time = now
            state = "JUMPING"
            print("Jump: crouch rebound")
            return True

        # 蹲太久就放弃，不然以后下蹲动作会一直卡在 CROUCHING
        if crouch_started_at is not None and now - crouch_started_at > CROUCH_MAX_SECONDS:
            state = "IDLE"
            crouch_started_at = None
            return False

    elif state == "JUMPING":
        # 落回 baseline 附近后再允许下一次触发
        if landed:
            state = "COOLDOWN"
            return False

    elif state == "COOLDOWN":
        if now - last_jump_time >= COOLDOWN_SECONDS:
            state = "IDLE"
            return False

    return False


def draw_debug_info(frame, current_y=None):
    h_img, w_img, _ = frame.shape

    if baseline_y is not None:
        cv2.line(
            frame,
            (0, int(baseline_y)),
            (w_img, int(baseline_y)),
            (0, 255, 255),
            2
        )

    if current_y is not None:
        cv2.circle(
            frame,
            (int(w_img / 2), int(current_y)),
            5,
            (255, 0, 0),
            -1
        )

    cv2.putText(
        frame,
        f"state: {state}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )


def detect_face_from_frame(frame):
    rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_detection.process(rgb_img)

    h_img, w_img, _ = frame.shape

    face_detected = bool(results.detections)
    recent_face_detections.append(face_detected)

    current_face_center_y = None

    if not is_face_stably_detected(recent_face_detections):
        draw_debug_info(frame)
        return frame

    if results.detections:
        detection = get_largest_detection(results.detections, w_img, h_img)
        bboxC = detection.location_data.relative_bounding_box

        x = int(bboxC.xmin * w_img)
        y = int(bboxC.ymin * h_img)
        w = int(bboxC.width * w_img)
        h = int(bboxC.height * h_img)

        current_face_center_y = int(y + h / 2)

        detect_jump(current_face_center_y)

        cv2.rectangle(frame, (x, y), (x + w, y + h), (80, 48, 230), 2)
        cv2.circle(frame, (int(x + w / 2), current_face_center_y), 5, (255, 0, 0), -1)

    draw_debug_info(frame, current_face_center_y)
    return frame


video_capture = cv2.VideoCapture(0)

# 尽量降低延迟
video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

while True:
    ret, frame = video_capture.read()

    if ret is False:
        break

    frame = detect_face_from_frame(frame)

    preview = cv2.resize(frame, None, fx=0.8, fy=0.8)
    cv2.imshow("Face Detection", preview)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

video_capture.release()
cv2.destroyAllWindows()
face_detection.close()