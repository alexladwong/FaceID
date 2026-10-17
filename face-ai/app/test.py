import os

import cv2

## -- local imports --##
from services.faceAi import FaceAiSvc

# tests #

img_path1 = "/home/somnath/Pictures/AI/som4.jpg"
img_path2 = "/home/somnath/Pictures/AI/group1.jpg"

face_ai = FaceAiSvc()
face_ai.start_detection_session()
face_ai.start_recognition_session()
match_val = face_ai.face_match_group(img_path1, img_path2)

print(match_val)
