import cv2
import mediapipe as mp
from collections import deque
import math

import serial
import time

mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.6)

recent_face_detections = deque(maxlen=5)

arduino = serial.Serial('/dev/cu.usbmodem11301', 9600, timeout=1)
time.sleep(2)

arduino.reset_input_buffer()

def is_face_stably_detected(recent_face_detections):
    return sum(recent_face_detections) >= 3

CAMERA_HORIZONTAL_FOV = 90
DEAD_ZONE = 30
DIRECTION = 1

last_sent_time = 0
SEND_INTERVAL = 0.2

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

    while arduino.in_waiting > 0:
        line = arduino.readline().decode("utf-8", errors="ignore").strip()
        print("arduino:", line)  

def calculate_pan_angle(horizontal_distance, frame_width):
    horizontal_fov_rad = math.radians(CAMERA_HORIZONTAL_FOV)
    focal_length_px = frame_width / (2 * math.tan(horizontal_fov_rad / 2))

    angle_rad = math.atan(horizontal_distance / focal_length_px)
    angle_deg = math.degrees(angle_rad)

    return DIRECTION * angle_deg


def detect_face_from_frame(frame):
    rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = face_detection.process(rgb_img)

    h_img, w_img, _ = frame.shape
    cv2.circle(frame, (int(w_img/2), int(h_img/2)), 2, (0, 255, 0), 2)

    face_detected = bool(results.detections)
    recent_face_detections.append(face_detected)

    if not is_face_stably_detected(recent_face_detections):
        print('no stable face detected')
        return frame

    if results.detections:
        for detection in results.detections:
            bboxC = detection.location_data.relative_bounding_box
            x = int(bboxC.xmin * w_img)
            y = int(bboxC.ymin * h_img)
            w = int(bboxC.width * w_img)
            h = int(bboxC.height * h_img)

            horizontal_distance = x+int(w/2) - int(w_img/2)

            if(horizontal_distance > DEAD_ZONE):
                # print("move to right --->")
                send_command('RIGHT')
            elif(horizontal_distance < -DEAD_ZONE):
                # print("<--- move to left")
                send_command('LEFT')
            else:
                send_command('CENTER')

            # angle_to_move = calculate_pan_angle(horizontal_distance, w_img)

            # if abs(horizontal_distance) <= DEAD_ZONE:
            #     print("center")
            # else:
            #     print(f"angle to move: {angle_to_move:.2f}°")

            # print('distance to move: ', horizontal_distance)

            cv2.circle(frame, (x+int(w/2), int(h_img/2)), 2, (0, 0, 255), 2)
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