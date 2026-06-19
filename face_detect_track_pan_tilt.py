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

arduino = serial.Serial('/dev/cu.usbmodem21301', SERIES_BAUD, timeout=1)
time.sleep(2)

arduino.reset_input_buffer()

def is_face_stably_detected(recent_face_detections):
    return sum(recent_face_detections) >= 3

CAMERA_HORIZONTAL_FOV = 90
CAMERA_VERTICAL_FOV = 52

ANGLE_DEAD_ZONE = 7
SMOOTHING_ALPHA = 0.3

PAN_DIRECTION = -1
TILT_DIRECTION = -1

KP = 0.45
KD = 0.03

MAX_PAN_STEP_DEG = 4
MIN_PAN_STEP_DEG = 1

MAX_TILT_STEP_DEG = 4
MIN_TILT_STEP_DEG = 1

last_sent_time = 0
SEND_INTERVAL = 0.08

smoothed_face_x = None
smoothed_face_y = None

last_pan_angle_error = None
last_pan_error_time = None

last_tilt_angle_error = None
last_tilt_error_time = None

def send_command(command):
    global last_sent_time

    now = time.time()

    if now - last_sent_time < SEND_INTERVAL:
        return
    
    arduino.write(f"{command}\n".encode('utf-8'))
    arduino.flush()

    last_sent_time = now
    print('sent', command)

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

    return PAN_DIRECTION * angle_deg

def calculate_tilt_angle(vertical_distance, frame_height):
    vertical_fov_rad = math.radians(CAMERA_VERTICAL_FOV)
    focal_length_px = frame_height / (2 * math.tan(vertical_fov_rad / 2))

    angle_rad = math.atan(vertical_distance / focal_length_px)
    angle_deg = math.degrees(angle_rad)
    
    return TILT_DIRECTION * angle_deg

def get_largest_detection(detections, frame_width, frame_height):
    def area(detection):
        bbox = detection.location_data.relative_bounding_box
        w = bbox.width * frame_width
        h = bbox.height * frame_height
        return w * h

    return max(detections, key=area)

def reset_pd_controller_pan():
    global last_pan_angle_error, last_pan_error_time

    last_pan_angle_error = None
    last_pan_error_time = None

def reset_pd_controller_tilt():
    global last_tilt_angle_error, last_tilt_error_time

    last_tilt_angle_error = None
    last_tilt_error_time = None

def calculate_tilt_delta_pd(angle_error):
    global last_tilt_angle_error, last_tilt_error_time

    now = time.time()

    if last_tilt_angle_error is None or last_tilt_error_time is None:
        last_tilt_angle_error = angle_error
        last_tilt_error_time = now

        # First frame: use only P term
        output = KP * angle_error
    else:
        dt = now - last_tilt_error_time

        if dt <= 0:
            return 0

        error_velocity = (angle_error - last_tilt_angle_error) / dt

        p_term = KP * angle_error
        d_term = KD * error_velocity

        output = p_term + d_term

        last_tilt_angle_error = angle_error
        last_tilt_error_time = now

    tilt_delta = round(output)

    if tilt_delta == 0:
        return 0

    tilt_delta = max(min(tilt_delta, MAX_TILT_STEP_DEG), -MAX_TILT_STEP_DEG)

    return tilt_delta

def calculate_pan_delta_pd(angle_error):
    global last_pan_angle_error, last_pan_error_time

    now = time.time()

    if last_pan_angle_error is None or last_pan_error_time is None:
        last_pan_angle_error = angle_error
        last_pan_error_time = now

        # First frame: use only P term
        output = KP * angle_error
    else:
        dt = now - last_pan_error_time

        if dt <= 0:
            return 0

        error_velocity = (angle_error - last_pan_angle_error) / dt

        p_term = KP * angle_error
        d_term = KD * error_velocity

        output = p_term + d_term

        last_pan_angle_error = angle_error
        last_pan_error_time = now

    pan_delta = round(output)

    if pan_delta == 0:
        return 0

    pan_delta = max(min(pan_delta, MAX_PAN_STEP_DEG), -MAX_PAN_STEP_DEG)

    return pan_delta

def detect_face_from_frame(frame):
    global smoothed_face_x
    global smoothed_face_y

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
        face_center_y = y + int(h / 2)

        if smoothed_face_x is None:
            smoothed_face_x = face_center_x
        else:
            smoothed_face_x = (
                SMOOTHING_ALPHA * face_center_x
                + (1 - SMOOTHING_ALPHA) * smoothed_face_x
            )

        if smoothed_face_y is None:
            smoothed_face_y = face_center_y
        else:
            smoothed_face_y = (
                SMOOTHING_ALPHA * face_center_y
                + (1 - SMOOTHING_ALPHA) * smoothed_face_y
            )            
            
        horizontal_distance = smoothed_face_x - frame_center_x
        vertical_distance = smoothed_face_y - frame_center_y

        angle_to_move_h = calculate_pan_angle(horizontal_distance, w_img)
        angle_to_move_v = calculate_tilt_angle(vertical_distance, h_img)

        pan_delta = 0
        tilt_delta = 0

        if abs(angle_to_move_h) <= ANGLE_DEAD_ZONE:
            reset_pd_controller_pan()
        else:
            pan_delta = calculate_pan_delta_pd(angle_to_move_h)

        if abs(angle_to_move_v) <= ANGLE_DEAD_ZONE:
            reset_pd_controller_tilt()
        else:
            tilt_delta = calculate_tilt_delta_pd(angle_to_move_v)


        if pan_delta != 0 or tilt_delta != 0:
            send_command(f"MOVE:{pan_delta},{tilt_delta}")

        cv2.circle(frame, (int(smoothed_face_x), int(smoothed_face_y)), 2, (0, 0, 255), 2)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (80, 48, 230), 2)
    
    return frame

video_capture = cv2.VideoCapture(0)

while True:
    ret, frame = video_capture.read()

    if ret is False:
        break

    frame = detect_face_from_frame(frame)

    cv2.imshow('Cameraman', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video_capture.release()
cv2.destroyAllWindows()

face_detection.close()