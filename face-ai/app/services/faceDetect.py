import os
import cv2
import numpy as np
import onnxruntime
from typing import Tuple
import argparse

## -- Global Variable -- ##

## -- Global functions -- ##
def distance2bbox(points, distance, max_shape=None):
    x1 = points[:, 0] - distance[:, 0]
    y1 = points[:, 1] - distance[:, 1]
    x2 = points[:, 0] + distance[:, 2]
    y2 = points[:, 1] + distance[:, 3]
    if max_shape is not None:
        x1 = np.clip(x1, 0, max_shape[1])
        y1 = np.clip(y1, 0, max_shape[0])
        x2 = np.clip(x2, 0, max_shape[1])
        y2 = np.clip(y2, 0, max_shape[0])
    return np.stack([x1, y1, x2, y2], axis=-1)

def distance2kps(points, distance, max_shape=None):
    preds = []
    for i in range(0, distance.shape[1], 2):
        px = points[:, i % 2] + distance[:, i]
        py = points[:, i % 2 + 1] + distance[:, i + 1]
        if max_shape is not None:
            px = np.clip(px, 0, max_shape[1])
            py = np.clip(py, 0, max_shape[0])
        preds.append(px)
        preds.append(py)
    return np.stack(preds, axis=-1)

def crop_with_buffer(image, bbox, buffer_px=2):
    """
    Crop your image with given box positions (bbox)
    """
    # 1. Unpack and convert coordinates to integers
    x1, y1, x2, y2 = bbox[:4].astype(np.int32)
    # Get image dimensions to prevent out-of-bounds errors
    img_h, img_w = image.shape[:2]

    # 2. Add the buffer to the coordinates
    # Subtraction moves the top-left corner further out
    # Addition moves the bottom-right corner further out
    x1_buf = max(0, x1 - buffer_px)
    y1_buf = max(0, y1 - buffer_px)
    x2_buf = min(img_w, x2 + buffer_px)
    y2_buf = min(img_h, y2 + buffer_px)

    # 3. Crop the image using NumPy slicing [ymin:ymax, xmin:xmax]
    cropped_image = image[y1_buf:y2_buf, x1_buf:x2_buf]
    return cropped_image

def draw_corners(image, bbox, colour=(255, 0, 0)):
    x1, y1, x2, y2 = bbox[:4].astype(np.int32)
    cv2.rectangle(image, (x1, y1), (x2, y2), colour, 2)

def draw_keypoints(image, kps):
    for i in range(kps.shape[0]):
        cv2.circle(image, tuple(kps[i].astype(np.int32)), 2, (0, 255, 0), -1)

### --- Classes --- ###

class FaceDetect:
    """
    This class provides the methods to perform the face detections and related services
    """

    def __init__(self, model_path: str, input_size: Tuple[int] = (640, 640), conf_thres: float = 0.3, iou_thres: float = 0.4) -> None:
        self.input_size = input_size
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres

        self.fmc = 3
        self._feat_stride_fpn = [8, 16, 32]
        self._num_anchors = 2
        self.use_kps = True

        self.mean = 127.5
        self.std = 128.0
        self.center_cache = {}

        self.model_path = model_path
        self.session = None

    def _initialize_model(self, model_path: str):
        try:
            self.session = onnxruntime.InferenceSession(
                model_path,
                providers=["CPUExecutionProvider"] # "CUDAExecutionProvider", 
            )
            self.output_names = [x.name for x in self.session.get_outputs()]
            self.input_names = [x.name for x in self.session.get_inputs()]
        except Exception as e:
            print(f"Failed to load the model: {e}")
            self.session = None

    def start_session(self):
        self._initialize_model(model_path=self.model_path)

    def forward(self, image, threshold):
        if not self.session:
            print("Onnx session is not ready")
            return

        scores_list = []
        bboxes_list = []
        kpss_list = []
        input_size = tuple(image.shape[0:2][::-1])

        blob = cv2.dnn.blobFromImage(
            image,
            1.0 / self.std,
            input_size,
            (self.mean, self.mean, self.mean),
            swapRB=True
        )
        outputs = self.session.run(self.output_names, {self.input_names[0]: blob})

        input_height = blob.shape[2]
        input_width = blob.shape[3]

        fmc = self.fmc
        for idx, stride in enumerate(self._feat_stride_fpn):
            scores = outputs[idx]
            bbox_preds = outputs[idx + fmc]
            bbox_preds = bbox_preds * stride
            if self.use_kps:
                kps_preds = outputs[idx + fmc * 2] * stride

            height = input_height // stride
            width = input_width // stride
            key = (height, width, stride)
            if key in self.center_cache:
                anchor_centers = self.center_cache[key]
            else:
                anchor_centers = np.stack(np.mgrid[:height, :width][::-1], axis=-1).astype(np.float32)
                anchor_centers = (anchor_centers * stride).reshape((-1, 2))
                if self._num_anchors > 1:
                    anchor_centers = np.stack([anchor_centers] * self._num_anchors, axis=1).reshape((-1, 2))
                if len(self.center_cache) < 100:
                    self.center_cache[key] = anchor_centers

            pos_inds = np.where(scores >= threshold)[0]
            bboxes = distance2bbox(anchor_centers, bbox_preds)
            pos_scores = scores[pos_inds]
            pos_bboxes = bboxes[pos_inds]
            scores_list.append(pos_scores)
            bboxes_list.append(pos_bboxes)
            if self.use_kps:
                kpss = distance2kps(anchor_centers, kps_preds)
                kpss = kpss.reshape((kpss.shape[0], -1, 2))
                pos_kpss = kpss[pos_inds]
                kpss_list.append(pos_kpss)
        return scores_list, bboxes_list, kpss_list

    def nms(self, dets, iou_thres):
        x1 = dets[:, 0]
        y1 = dets[:, 1]
        x2 = dets[:, 2]
        y2 = dets[:, 3]
        scores = dets[:, 4]

        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter)

            indices = np.where(ovr <= iou_thres)[0]
            order = order[indices + 1]
        return keep

    def detect(self, image, max_num=0, metric="max"):
        """
        Detect the faces on an image. This returns the face boxes and keypoints.
        """

        if not self.session:
            print("Onnx session is not ready")
            return

        width, height = self.input_size
        im_ratio = float(image.shape[0]) / image.shape[1]
        model_ratio = height / width
        if im_ratio > model_ratio:
            new_height = height
            new_width = int(new_height / im_ratio)
        else:
            new_width = width
            new_height = int(new_width * im_ratio)

        det_scale = float(new_height) / image.shape[0]
        resized_image = cv2.resize(image, (new_width, new_height))

        det_image = np.zeros((height, width, 3), dtype=np.uint8)
        # Handle 4-channel images by converting to 3-channel
        if resized_image.shape[2] == 4:
            resized_image = cv2.cvtColor(resized_image, cv2.COLOR_BGRA2BGR)
        det_image[:new_height, :new_width, :] = resized_image

        scores_list, bboxes_list, kpss_list = self.forward(det_image, self.conf_thres)

        scores = np.vstack(scores_list)
        scores_ravel = scores.ravel()
        order = scores_ravel.argsort()[::-1]
        bboxes = np.vstack(bboxes_list) / det_scale

        if self.use_kps:
            kpss = np.vstack(kpss_list) / det_scale

        pre_det = np.hstack((bboxes, scores)).astype(np.float32, copy=False)
        pre_det = pre_det[order, :]
        keep = self.nms(pre_det, iou_thres=self.iou_thres)
        det = pre_det[keep, :]
        if self.use_kps:
            kpss = kpss[order, :, :]
            kpss = kpss[keep, :, :]
        else:
            kpss = None
        if 0 < max_num < det.shape[0]:
            area = (det[:, 2] - det[:, 0]) * (det[:, 3] - det[:, 1])
            image_center = image.shape[0] // 2, image.shape[1] // 2
            offsets = np.vstack(
                [
                    (det[:, 0] + det[:, 2]) / 2 - image_center[1],
                    (det[:, 1] + det[:, 3]) / 2 - image_center[0],
                ]
            )
            offset_dist_squared = np.sum(np.power(offsets, 2.0), 0)
            if metric == "max":
                values = area
            else:
                values = (area - offset_dist_squared * 2.0)  # some extra weight on the centering
            bindex = np.argsort(values)[::-1]
            bindex = bindex[0:max_num]
            det = det[bindex, :]
            if kpss is not None:
                kpss = kpss[bindex, :]
        return det, kpss

    def get_single_face_cropped(self, image, max_num=0, metric="max"):
        """
        This will detect the face from a Numpy image array and will crop the face only.
        If more than one face detected, it will send False status.
        """
        crp_face = None
        if not self.session:
            print("Onnx session is not ready")
            return None

        boxes_list, points_list = self.detect(image, max_num, metric)
        if len(boxes_list) >= 2:
            print("Found more than one faces")
        elif len(boxes_list) == 1:
            crp_face = crop_with_buffer(image, boxes_list[0])
        else:
            print("No face found in the photo")
        return crp_face

    def get_all_faces_marked(self, image, draw_points:bool = True, max_num=0, metric="max"):
        """
        Detect and mark all faces on a single image.
        """
        if not self.session:
            print("Onnx session is not ready")
            return None

        boxes_list, points_list = self.detect(image, max_num, metric)
        # draw boxes for identified faces
        for boxes in boxes_list:
            draw_corners(image, boxes)

        if draw_points and points_list is not None:
            for points in points_list:
                draw_keypoints(image, points)
        # return the processed image
        return image
