import cv2
import face_recognition
import os
import numpy as np

KNOWN_FACE_DIR = "images/known_faces"

known_encodings = []
known_names = []

for person_name in os.listdir(KNOWN_FACE_DIR):
    person_dir = os.path.join(KNOWN_FACE_DIR, person_name)

    if not os.path.isdir(person_dir):
        continue

    for filename in os.listdir(person_dir):
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        image_path = os.path.join(person_dir, filename)
        image = face_recognition.load_image_file(image_path)

        encodings = face_recognition.face_encodings(image)

        if len(encodings) == 0:
            print(f"No face found in {image_path}")
            continue

        known_encodings.append(encodings[0])
        known_names.append(person_name)

print(f"Loaded {len(known_encodings)} known face encodings")

cap = cv2.VideoCapture(0)

process_this_frame = True

while True:
    ret, frame = cap.read()

    if not ret:
        break

    if process_this_frame:
        # Resize frame to 1/4 size for faster face recognition
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Convert BGR to RGB
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(
            rgb_small_frame,
            face_locations
        )

        face_names = []

        for face_encoding in face_encodings:
            name = "Unknown"

            face_distances = face_recognition.face_distance(
                known_encodings,
                face_encoding
            )

            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                best_distance = face_distances[best_match_index]

                if best_distance < 0.5:
                    name = known_names[best_match_index]

            face_names.append(name)

    # Only process every other frame
    process_this_frame = not process_this_frame

    # Draw results
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Scale back up since the frame was 1/4 size
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)

        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.putText(
            frame,
            name,
            (left, top - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2
        )

    cv2.imshow("Face Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()