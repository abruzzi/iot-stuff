import cv2
import mediapipe as mp
from collections import deque
import math
import serial
import time

from experiment_logger import ExperimentLogger
from arduino_state import ArduinoState


# -----------------------------
# Experiment config
# -----------------------------

RUN_CONFIG = {
    "controller_mode": "p",
    "use_smoothing": False,
    "use_stable_detection": True,

    "camera_horizontal_fov": 90,
    "dead_zone": 7,
    "smoothing_alpha": 0.3,

    "direction": -1,
    "kp": 0.5,
    "kd": 0,
    "max_step_deg": 5,
    "send_interval": 0.1,

    "serial_port": "/dev/cu.usbmodem21301",
    "serial_baud": 9600,
    "camera_index": 0,
}


# -----------------------------
# Constants from config
# -----------------------------

CONTROLLER_MODE = RUN_CONFIG["controller_mode"]
USE_SMOOTHING = RUN_CONFIG["use_smoothing"]
USE_STABLE_DETECTION = RUN_CONFIG["use_stable_detection"]

CAMERA_HORIZONTAL_FOV = RUN_CONFIG["camera_horizontal_fov"]
ANGLE_DEAD_ZONE = RUN_CONFIG["dead_zone"]
SMOOTHING_ALPHA = RUN_CONFIG["smoothing_alpha"]

DIRECTION = RUN_CONFIG["direction"]
KP = RUN_CONFIG["kp"]
MAX_STEP_DEG = RUN_CONFIG["max_step_deg"]
SEND_INTERVAL = RUN_CONFIG["send_interval"]

SERIAL_PORT = RUN_CONFIG["serial_port"]
SERIAL_BAUD = RUN_CONFIG["serial_baud"]
CAMERA_INDEX = RUN_CONFIG["camera_index"]


# -----------------------------
# Setup logger and Arduino state
# -----------------------------

logger = ExperimentLogger(RUN_CONFIG)
arduino_state = ArduinoState()


# -----------------------------
# Setup Arduino serial
# -----------------------------

arduino = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.05)
time.sleep(2)
arduino.reset_input_buffer()


# -----------------------------
# Setup MediaPipe
# -----------------------------

mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.6,
)


# -----------------------------
# Runtime state
# -----------------------------

recent_face_detections = deque(maxlen=5)

last_sent_time = 0
smoothed_face_x = None
smoothed_face_y = None
frame_index = 0


# -----------------------------
# Arduino helpers
# -----------------------------

def read_arduino_lines():
    lines = []

    while arduino.in_waiting > 0:
        try:
            line = arduino.readline().decode("utf-8", errors="ignore").strip()
            if line:
                arduino_state.parse_line(line)
                lines.append(line)
        except Exception:
            pass

    return lines


def send_command(command):
    global last_sent_time

    now = time.time()
    time_since_last_send = now - last_sent_time

    if time_since_last_send < SEND_INTERVAL:
        return {
            "sent": False,
            "reason": "send_interval",
            "command": command,
            "time_since_last_send_s": time_since_last_send,
            "arduino_lines": [],
        }

    arduino.write(f"{command}\n".encode("utf-8"))
    arduino.flush()

    last_sent_time = now

    # Give Arduino a short moment to respond.
    # This is intentionally small so the camera loop is not blocked too much.
    time.sleep(0.03)

    arduino_lines = read_arduino_lines()

    print("sent", command)
    for line in arduino_lines:
        print("arduino:", line)

    return {
        "sent": True,
        "reason": "",
        "command": command,
        "time_since_last_send_s": time_since_last_send,
        "arduino_lines": arduino_lines,
    }


# -----------------------------
# Detection and control helpers
# -----------------------------

def is_face_stably_detected(detections):
    return sum(detections) >= 3


def calculate_pan_angle(horizontal_distance, frame_width):
    horizontal_fov_rad = math.radians(CAMERA_HORIZONTAL_FOV)
    focal_length_px = frame_width / (2 * math.tan(horizontal_fov_rad / 2))

    angle_rad = math.atan(horizontal_distance / focal_length_px)
    angle_deg = math.degrees(angle_rad)

    return DIRECTION * angle_deg


def calculate_pan_delta_p(angle_error):
    pan_delta = round(angle_error * KP)
    pan_delta = max(min(pan_delta, MAX_STEP_DEG), -MAX_STEP_DEG)
    return pan_delta


def get_largest_detection(detections, frame_width, frame_height):
    def area(detection):
        bbox = detection.location_data.relative_bounding_box
        w = bbox.width * frame_width
        h = bbox.height * frame_height
        return w * h

    return max(detections, key=area)


def log_common_frame_state(
    *,
    event,
    frame_index,
    face_detected,
    stable_face_detected,
    recent_detection_count,
    frame_width,
    frame_height,
    frame_center_x,
    frame_center_y,
    arduino_lines=None,
    **extra,
):
    if arduino_lines is None:
        arduino_lines = []

    logger.log(
        frame_index=frame_index,
        event=event,

        face_detected=face_detected,
        stable_face_detected=stable_face_detected,
        recent_detection_count=recent_detection_count,

        frame_width=frame_width,
        frame_height=frame_height,
        frame_center_x=frame_center_x,
        frame_center_y=frame_center_y,

        arduino_line=" | ".join(arduino_lines),

        **arduino_state.snapshot(),
        **extra,
    )


# -----------------------------
# Main frame processing
# -----------------------------

def detect_face_from_frame(frame, frame_index):
    global smoothed_face_x, smoothed_face_y

    rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_detection.process(rgb_img)

    h_img, w_img, _ = frame.shape
    frame_center_x = int(w_img / 2)
    frame_center_y = int(h_img / 2)

    cv2.circle(frame, (frame_center_x, frame_center_y), 3, (0, 255, 0), 2)

    face_detected = bool(results.detections)
    recent_face_detections.append(face_detected)

    stable_face_detected = (
        is_face_stably_detected(recent_face_detections)
        if USE_STABLE_DETECTION
        else face_detected
    )

    recent_detection_count = sum(recent_face_detections)

    # Always read Arduino state if available.
    arduino_lines = read_arduino_lines()

    if not face_detected:
        log_common_frame_state(
            event="no_face",
            frame_index=frame_index,
            face_detected=False,
            stable_face_detected=stable_face_detected,
            recent_detection_count=recent_detection_count,
            frame_width=w_img,
            frame_height=h_img,
            frame_center_x=frame_center_x,
            frame_center_y=frame_center_y,
            arduino_lines=arduino_lines,
        )
        print("no face detected")
        return frame

    if not stable_face_detected:
        log_common_frame_state(
            event="unstable_face",
            frame_index=frame_index,
            face_detected=True,
            stable_face_detected=False,
            recent_detection_count=recent_detection_count,
            frame_width=w_img,
            frame_height=h_img,
            frame_center_x=frame_center_x,
            frame_center_y=frame_center_y,
            arduino_lines=arduino_lines,
        )
        print("no stable face detected")
        return frame

    detection = get_largest_detection(results.detections, w_img, h_img)
    bboxC = detection.location_data.relative_bounding_box

    x = int(bboxC.xmin * w_img)
    y = int(bboxC.ymin * h_img)
    w = int(bboxC.width * w_img)
    h = int(bboxC.height * h_img)

    raw_face_center_x = x + int(w / 2)
    raw_face_center_y = y + int(h / 2)

    if USE_SMOOTHING:
        if smoothed_face_x is None:
            smoothed_face_x = raw_face_center_x
            smoothed_face_y = raw_face_center_y
        else:
            smoothed_face_x = (
                SMOOTHING_ALPHA * raw_face_center_x
                + (1 - SMOOTHING_ALPHA) * smoothed_face_x
            )
            smoothed_face_y = (
                SMOOTHING_ALPHA * raw_face_center_y
                + (1 - SMOOTHING_ALPHA) * smoothed_face_y
            )
    else:
        smoothed_face_x = raw_face_center_x
        smoothed_face_y = raw_face_center_y

    horizontal_distance = smoothed_face_x - frame_center_x
    vertical_distance = smoothed_face_y - frame_center_y

    angle_error = calculate_pan_angle(horizontal_distance, w_img)
    within_dead_zone = abs(angle_error) <= ANGLE_DEAD_ZONE

    pan_delta = 0
    command = ""
    command_sent = False
    send_skipped_reason = ""
    time_since_last_send_s = ""
    event = ""

    if within_dead_zone:
        event = "center"
        print(f"center, angle error: {angle_error:.2f}°")

    else:
        event = "control"

        if CONTROLLER_MODE == "p":
            pan_delta = calculate_pan_delta_p(angle_error)
        else:
            raise ValueError(f"Unsupported controller mode: {CONTROLLER_MODE}")

        command = f"PAN:{pan_delta}"
        result = send_command(command)

        command_sent = result["sent"]
        send_skipped_reason = result["reason"]
        time_since_last_send_s = result["time_since_last_send_s"]
        arduino_lines.extend(result["arduino_lines"])

        print(f"angle error: {angle_error:.2f}°, pan delta: {pan_delta}°")

    log_common_frame_state(
        event=event,
        frame_index=frame_index,

        face_detected=True,
        stable_face_detected=stable_face_detected,
        recent_detection_count=recent_detection_count,

        frame_width=w_img,
        frame_height=h_img,
        frame_center_x=frame_center_x,
        frame_center_y=frame_center_y,

        arduino_lines=arduino_lines,

        bbox_x=x,
        bbox_y=y,
        bbox_w=w,
        bbox_h=h,

        raw_face_center_x=raw_face_center_x,
        raw_face_center_y=raw_face_center_y,
        smoothed_face_center_x=round(smoothed_face_x, 3),
        smoothed_face_center_y=round(smoothed_face_y, 3),

        horizontal_distance=round(horizontal_distance, 3),
        vertical_distance=round(vertical_distance, 3),
        angle_error=round(angle_error, 6),
        within_dead_zone=within_dead_zone,

        pan_delta=pan_delta,
        command=command,
        command_sent=command_sent,
        send_skipped_reason=send_skipped_reason,
        time_since_last_send_s=(
            round(time_since_last_send_s, 6)
            if time_since_last_send_s != ""
            else ""
        ),
    )

    cv2.circle(
        frame,
        (int(smoothed_face_x), int(smoothed_face_y)),
        3,
        (0, 0, 255),
        2,
    )
    cv2.rectangle(frame, (x, y), (x + w, y + h), (80, 48, 230), 2)

    cv2.putText(
        frame,
        f"error: {angle_error:.2f} deg",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )

    cv2.putText(
        frame,
        f"event: {event}",
        (20, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )

    return frame


# -----------------------------
# Main loop
# -----------------------------

def main():
    global frame_index

    video_capture = cv2.VideoCapture(CAMERA_INDEX)

    try:
        while True:
            ret, frame = video_capture.read()

            if ret is False:
                break

            frame_index += 1

            frame = detect_face_from_frame(frame, frame_index)

            cv2.imshow("cameraman", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        video_capture.release()
        cv2.destroyAllWindows()
        face_detection.close()
        arduino.close()

        logger.close()
        logger.print_paths()


if __name__ == "__main__":
    main()