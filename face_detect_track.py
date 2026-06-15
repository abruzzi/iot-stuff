import cv2
import mediapipe as mp
from collections import deque

mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.6)

recent_face_detections = deque(maxlen=5)

DEAD_ZONE = 30

def is_face_stably_detected(recent_face_detections):
    return sum(recent_face_detections) >= 3

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

            box_center = (x+int(w/2), y+int(h/2))
            horizontal_distance = x+int(w/2) - int(w_img/2)

            if(horizontal_distance > DEAD_ZONE):
                print('<--- move to left')
            elif(horizontal_distance < -DEAD_ZONE):
                print('move to right --->')
            else:
                print('center')

            print('distance to move: ', horizontal_distance)

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