import cv2
import mediapipe as mp

mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.6)

def detect_face_from_frame(frame):
    rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = face_detection.process(rgb_img)

    if results.detections:
        h_img, w_img, _ = frame.shape
        for detection in results.detections:
            bboxC = detection.location_data.relative_bounding_box
            x = int(bboxC.xmin * w_img)
            y = int(bboxC.ymin * h_img)
            w = int(bboxC.width * w_img)
            h = int(bboxC.height * h_img)

            cv2.rectangle(frame, (x, y), (x + w, y + h), (80, 48, 230), 4)

video_capture = cv2.VideoCapture(0)

while True:
    ret, frame = video_capture.read()

    if ret is False:
        break

    faces = detect_face_from_frame(frame)

    cv2.imshow('cameraman', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video_capture.release()
cv2.destroyAllWindows()

face_detection.close()