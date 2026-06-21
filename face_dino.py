import cv2
import mediapipe as mp
from collections import deque
import time
import pyautogui

mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.6)

recent_face_detections = deque(maxlen=3)

def is_face_stably_detected(recent_face_detections):
    return sum(recent_face_detections) >= 1

def get_largest_detection(detections, frame_width, frame_height):
    def area(detection):
        bbox = detection.location_data.relative_bounding_box
        w = bbox.width * frame_width
        h = bbox.height * frame_height
        return w * h

    return max(detections, key=area)

last_face_center_y = None
duck_face_center_y = None

smoothed_face_center_y = None
last_jump_time = 0

SMOOTHING_ALPHA = 0.6
DUCK_THRESHOLD = 25
LIFT_THRESHOLD = 25
COOLDOWN_SECONDS = 0.15

def smooth_y(current_y):
    global smoothed_face_center_y

    if smoothed_face_center_y is None:
        smoothed_face_center_y = current_y
    else:
        smoothed_face_center_y = (
            SMOOTHING_ALPHA * current_y
            + (1 - SMOOTHING_ALPHA) * smoothed_face_center_y
        )

    return smoothed_face_center_y

def detect_jump(current_face_center_y):
    global last_face_center_y, duck_face_center_y, last_jump_time

    current_y = smooth_y(current_face_center_y)
    now = time.time()

    if now - last_jump_time < COOLDOWN_SECONDS:
        last_face_center_y = current_y
        return False

    if last_face_center_y is None:
        last_face_center_y = current_y
        return False

    delta = current_y - last_face_center_y

    if delta >= DUCK_THRESHOLD:
        duck_face_center_y = current_y

    if duck_face_center_y is not None and duck_face_center_y - current_y >= LIFT_THRESHOLD:
        duck_face_center_y = None
        last_jump_time = now
        last_face_center_y = current_y
        return True

    last_face_center_y = current_y
    return False

def detect_face_from_frame(frame):
    rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = face_detection.process(rgb_img)

    h_img, w_img, _ = frame.shape
    frame_center_x = int(w_img / 2)
    frame_center_y = int(h_img / 2)

    cv2.circle(frame, (frame_center_x, frame_center_y), 2, (0, 255, 0), 2)

    face_detected = bool(results.detections)
    recent_face_detections.append(face_detected)

    if not is_face_stably_detected(recent_face_detections):
        return frame

    if results.detections:
        detection = get_largest_detection(results.detections, w_img, h_img)
        bboxC = detection.location_data.relative_bounding_box
        x = int(bboxC.xmin * w_img)
        y = int(bboxC.ymin * h_img)
        w = int(bboxC.width * w_img)
        h = int(bboxC.height * h_img)

        current_face_center_y = int(y + h/2)

        if detect_jump(current_face_center_y):
            pyautogui.press('space')

        cv2.rectangle(frame, (x, y), (x + w, y + h), (80, 48, 230), 2)
    
    return frame

video_capture = cv2.VideoCapture(0)

while True:
    ret, frame = video_capture.read()

    if ret is False:
        break

    face = detect_face_from_frame(frame)

    preview = cv2.resize(frame, None, fx=0.5, fy=0.5)
    cv2.imshow("Face Detection", preview)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video_capture.release()
cv2.destroyAllWindows()

face_detection.close()