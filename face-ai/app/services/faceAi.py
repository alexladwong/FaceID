import os
import datetime

import cv2
import numpy as np

from kivy.clock import Clock

## -- local imports -- ##
from services.faceDetect import FaceDetect, crop_with_buffer, draw_corners
from services.faceRecognition import FaceRecog
from services.dbServices import FaceDbSvc

## -- global vars -- ##
detect_path = "/home/somnath/.insightface/models/buffalo_l/det_10g.onnx"
recog_path = "/home/somnath/.insightface/models/buffalo_l/arc.onnx"
out_path = ""

### --- global functions --- ###

def write_text(image, bbox, text:str, colour=(255, 0, 0)):
    original_height, original_width = image.shape[:2]

    thickness = 2
    if original_width >= 4000:
        text_size = 2.0
        thickness = 4
    elif original_width >= 3000:
        text_size = 1.8
        thickness = 3
    elif original_width >= 2500:
        text_size = 1.5
    elif original_width >= 2000:
        text_size = 1.2
    elif original_width >= 1500:
        text_size = 1.0
    elif original_width >= 800:
        text_size = 0.8
        thickness = 2
    else:
        text_size = 0.5
        thickness = 1

    x1, y1, x2, y2 = bbox[:4].astype(np.int32)
    cv2.putText(image, text, (x1, y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, text_size, colour, thickness)

def face_match_draw(img1, faces1, img2, faces2, matches, scores, target_size=[512, 512]): # target_size: (h, w)
    out1 = img1.copy()
    out2 = img2.copy()
    matched_box_color = (0, 255, 0)    # BGR
    mismatched_box_color = (0, 0, 255) # BGR

    # draw on face1
    draw_corners(out1, faces1[0], matched_box_color)

    # Draw on face2
    if faces2.shape[0] == len(matches) and len(matches) == len(scores):
        for index, match in enumerate(matches):
            score = scores[index]*100
            if match == 1:
                draw_corners(out2, faces2[index], matched_box_color)
                write_text(out2, faces2[index], "{:.2f}".format(score), matched_box_color)
            else:
                draw_corners(out2, faces2[index], mismatched_box_color)
                write_text(out2, faces2[index], "{:.2f}".format(score), mismatched_box_color)
        return out1, out2
    else:
        return None, None
    #return np.concatenate([padded_out1, padded_out2], axis=1)

### --- classes --- ###
class FaceAiSvc:
    """
    This class will provide Face AI services like face detection, recognition etc.
    """

    def __init__(self, detect_model_path:str=detect_path, recog_model_path:str=recog_path, out_pth:str=out_path):
        self.detect_onnx = detect_model_path
        self.recog_onnx = recog_model_path
        self.out_path = out_pth
        self.face_detect = None
        self.face_recog = None
        self.db_sess = None
        self._threshold_cosine = 0.65
        self._threshold_norml2 = 1.13

    def start_detection_session(self):
        self.face_detect = FaceDetect(self.detect_onnx)
        self.face_detect.start_session()

    def start_recognition_session(self):
        self.face_recog = FaceRecog(self.recog_onnx)
        self.face_recog.start_session()

    def start_db_session(self, db_path:str):
        if self.db_sess:
            print("Datase connection is already OK")
            return True
        try:
            self.db_sess = FaceDbSvc(db_path)
            self.db_sess.init_db()
            return True
        except Exception as e:
            print(f"Database init error: {e}")
            self.db_sess = None
            return False

    def match_two_images_single_face(self, img1_path:str, img2_path:str, callback=None):
        """
        Match two images with single face on each image. If there is no face or more than one face on any image, it will return None.

        Args:
            img1_path (str): Path of the first image.
            img2_path (str): Path of the second image.

        Returns:
            float | None: if all goes well the compare value will be sent, else None
        """
        if self.face_detect.session is None or self.face_recog.session is None:
            print("Either detection or recognition session(s) is/are not ready")
            return None

        image1 = cv2.imread(img1_path)
        image2 = cv2.imread(img2_path)
        face1 = self.face_detect.get_single_face_cropped(image1)
        face2 = self.face_detect.get_single_face_cropped(image2)
        if face1 is None:
            print("Image 1 does not contain any face or contains more than one face")
            return None
        if face2 is None:
            print("Image 2 does not contain any face or contains more than one face")
            return None
        val_compare = self.face_recog.match_faces(face1, face2)
        return val_compare

    def face_match_group(self, img1_path:str, img2_path:str, callback=None):
        """
        Find the face from image1 (should be single face image) on image2 (could have multiple faces). 
        If there is no face or more than one face on image1, it will return None.
        If there is no face on image2, it will also return None.

        Args:
            img1_path (str): Path of the first image.
            img2_path (str): Path of the second image.

        Returns:
            path | None: if all goes well it will create a collage with two images of faces marked, else None
        """
        obj_return = {
            "stat": False,
            "msg": "",
            "src": "",
            "trgt": ""
        }
        # if session(s) is/are not ready
        if self.face_detect.session is None or self.face_recog.session is None:
            print("Detection or/and recognition session(s) is/are not ready")
            obj_return["msg"] = "Session is not ready"
            if callback:
                Clock.schedule_once(lambda dt: callback(obj_return))
            else:
                return obj_return

        img1_stat = False
        img2_stat = False

        image1 = cv2.imread(img1_path)
        image2 = cv2.imread(img2_path)

        faces1, point1 = self.face_detect.detect(image1)
        if len(faces1) == 1:
            img1_stat = True
            face1 = crop_with_buffer(image1, faces1[0])
            face1_emb = self.face_recog.get_face_embedding(face1)
        elif len(faces1) >= 2:
            obj_return["msg"] = "[color=#f58e2f]More than one face found in [b]Source Image[/b][/color]"
        else:
            obj_return["msg"] = "[color=#f58e2f]No face is found in [b]Source Image[b][/color]"

        faces2, point2 = self.face_detect.detect(image2)
        if len(faces2) >= 1:
            img2_stat = True
        else:
            obj_return["msg"] = "[color=#f58e2f]No face is found in [b]Target Image[/b][/color]"

        if img2_stat and img1_stat:
            scores = []
            matches = []
            for face in faces2:
                face_crp = crop_with_buffer(image2, face)
                face_emb = self.face_recog.get_face_embedding(face_crp)
                score = np.dot(face1_emb, face_emb)
                scores.append(score)
                matches.append(1 if score >= self._threshold_cosine else 0)
            new_image1, new_image2 = face_match_draw(image1, faces1, image2, faces2, matches, scores)
            now = datetime.datetime.now()
            current_time = str(now.strftime("%H%M%S"))
            current_date = str(now.strftime("%Y%m%d"))
            filename1 = os.path.join(self.out_path, f"fmg1_{current_date}_{current_time}.jpg")
            filename2 = os.path.join(self.out_path, f"fmg2_{current_date}_{current_time}.jpg")
            cv2.imwrite(filename1, new_image1)
            cv2.imwrite(filename2, new_image2)
            obj_return["msg"] = "Match success"
            obj_return["stat"] = True
            obj_return["src"] = filename1
            obj_return["trgt"] = filename2
        # return via callback or normal return
        if callback:
            Clock.schedule_once(lambda dt: callback(obj_return))
        else:
            return obj_return

    def check_if_data_exist(self, callback=None):
        stat = False
        if self.db_sess:
            if (
                self.db_sess.names is not None and
                self.db_sess.matrix_embeddings is not None
            ):
                stat = True
        # return via callback or normal return
        if callback:
            Clock.schedule_once(lambda dt: callback(stat))
        else:
            return stat

    def save_faces_masterdb(self, name:str, image, callback=None):
        stat = False
        if None in (self.db_sess, self.face_recog, self.face_detect):
            print("Please start the db & face sessions first")
            if callback:
                Clock.schedule_once(lambda dt: callback(stat))
            else:
                return stat

        cropped = self.face_detect.get_single_face_cropped(image)
        if cropped is not None:
            embed = self.face_recog.get_face_embedding(cropped)
            stat = self.db_sess.save_embedding(name, embed)
            print(f"Face saved successfully for {name}")
        else:
            print("Issue with given frame")
        if callback:
            Clock.schedule_once(lambda dt: callback(stat))
        else:
            return stat

    def face_verify(self, image, callback=None):
        matched_name = None
        if None in (self.db_sess, self.face_recog, self.face_detect):
            print("Please start the db & face sessions first")
            if callback:
                Clock.schedule_once(lambda dt: callback(matched_name))
            else:
                return matched_name

        cropped = self.face_detect.get_single_face_cropped(image)
        if cropped is not None:
            embed = self.face_recog.get_face_embedding(cropped)
            matched_name = self.db_sess.check_face_exists(embed, self._threshold_cosine)
        if callback:
            Clock.schedule_once(lambda dt: callback(matched_name))
        else:
            return matched_name
