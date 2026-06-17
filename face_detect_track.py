import cv2
import mediapipe as mp
from collections import deque
import math

import serial
import time

mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.6)

recent_face_detections = deque(maxlen=5)

# update this later
SERIES_BAUD=115200

arduino = serial.Serial('/dev/cu.usbmodem21201', 9600, timeout=1)
time.sleep(2)

arduino.reset_input_buffer()

def is_face_stably_detected(recent_face_detections):
    return sum(recent_face_detections) >= 3

CAMERA_HORIZONTAL_FOV = 90
ANGLE_DEAD_ZONE = 7
SMOOTHING_ALPHA = 0.3

DIRECTION = -1
KP = 0.5
MAX_STEP_DEG = 5

last_sent_time = 0
SEND_INTERVAL = 0.1

smoothed_face_x = None

def send_command(command):
    global last_sent_time

    now = time.time()

    if now - last_sent_time < SEND_INTERVAL:
        return
    
    arduino.write(f"{command}\n".encode('utf-8'))
    arduino.flush()

    last_sent_time = now
    print('sent', command)

    time.sleep(0.05)

    if arduino.in_waiting > 0:
        try:
            line = arduino.readline().decode("utf-8", errors="ignore").strip()
            print("arduino:", line)
        except Exception:
            pass

def calculate_pan_angle(horizontal_distance, frame_width):
    horizontal_fov_rad = math.radians(CAMERA_HORIZONTAL_FOV)
    focal_length_px = frame_width / (2 * math.tan(horizontal_fov_rad / 2))

    angle_rad = math.atan(horizontal_distance / focal_length_px)
    angle_deg = math.degrees(angle_rad)

    return DIRECTION * angle_deg

def send_pan_delta(delta):
    send_command(f"PAN:{delta}")

def get_largest_detection(detections, frame_width, frame_height):
    def area(detection):
        bbox = detection.location_data.relative_bounding_box
        w = bbox.width * frame_width
        h = bbox.height * frame_height
        return w * h

    return max(detections, key=area)

def detect_face_from_frame(frame):
    global smoothed_face_x

    rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = face_detection.process(rgb_img)

    h_img, w_img, _ = frame.shape
    frame_center_x = int(w_img / 2)
    frame_center_y = int(h_img / 2)

    cv2.circle(frame, (frame_center_x, frame_center_y), 2, (0, 255, 0), 2)

    face_detected = bool(results.detections)
    recent_face_detections.append(face_detected)

    if not is_face_stably_detected(recent_face_detections):
        print('no stable face detected')
        return frame

    if results.detections:
        detection = get_largest_detection(results.detections, w_img, h_img)
        bboxC = detection.location_data.relative_bounding_box
        x = int(bboxC.xmin * w_img)
        y = int(bboxC.ymin * h_img)
        w = int(bboxC.width * w_img)
        h = int(bboxC.height * h_img)

        face_center_x = x + int(w / 2)

        if smoothed_face_x is None:
            smoothed_face_x = face_center_x
        else:
            smoothed_face_x = (
                SMOOTHING_ALPHA * face_center_x
                + (1 - SMOOTHING_ALPHA) * smoothed_face_x
            )
            
        horizontal_distance = smoothed_face_x - frame_center_x

        angle_to_move = calculate_pan_angle(horizontal_distance, w_img)

        if abs(angle_to_move) <= ANGLE_DEAD_ZONE:
            print("center")
        else:
            pan_delta = round(angle_to_move * KP)

            # Limit each movement so the servo does not jump too much
            pan_delta = max(min(pan_delta, MAX_STEP_DEG), -MAX_STEP_DEG)

            send_command(f"PAN:{pan_delta}")
            print(f"angle to move: {angle_to_move:.2f}°, pan delta: {pan_delta}°")

        cv2.circle(frame, (int(smoothed_face_x), frame_center_y), 2, (0, 0, 255), 2)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (80, 48, 230), 2)
    
    return frame

video_capture = cv2.VideoCapture(0)

while True:
    ret, frame = video_capture.read()

    if ret is False:
        break

    frame = detect_face_from_frame(frame)

    cv2.imshow('cameraman', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video_capture.release()
cv2.destroyAllWindows()

face_detection.close()