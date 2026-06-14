import cv2

imagePath = 'images/rollback-in-production.jpg'

img = cv2.imread(imagePath)

print(img.shape)

gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

print(gray_img.shape)

face_classifier = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

faces = face_classifier.detectMultiScale(
    gray_img, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
)

print(faces)

for (x, y, w, h) in faces:
    cv2.rectangle(img, (x, y), (x + w, y + h), (80, 48, 230), 4)

img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

print(img_rgb.shape)

import matplotlib.pyplot as plt

plt.figure(figsize=(20,10))
plt.imshow(img_rgb)
plt.axis('off')

plt.show()