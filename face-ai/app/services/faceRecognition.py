import numpy as np
import cv2
import onnxruntime as ort

## -- Global Variable -- ##

## -- Global functions -- ##

### --- Classes --- ###

class FaceRecog:
    """
    This class will perform the face recognistion on the given face. Face should be cropped.
    """

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.session = None

    def _initialize_model(self, model_path: str):
        try:
            self.session = ort.InferenceSession(
                model_path,
                providers=["CPUExecutionProvider"] # "CUDAExecutionProvider", 
            )
            self.output_names = self.session.get_outputs()[0].name
            self.input_names = self.session.get_inputs()[0].name
        except Exception as e:
            print(f"Failed to load the model: {e}")
            self.session = None

    def start_session(self):
        self._initialize_model(model_path=self.model_path)

    def _preprocess(self, img):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (112, 112))
        img = (img.astype(np.float32) - 127.5) / 128.0
        return img[np.newaxis, ...]

    def get_face_embedding(self, image):
        """
        Get the face embeddings from ArcFace ONNX. Input image should be Numpy array.
        """
        if not self.session:
            print("Onnx session is not ready")
            return None

        emb = self.session.run([self.output_names], {self.input_names: self._preprocess(image)})[0][0]
        # normalise
        emb = emb / np.linalg.norm(emb)
        return emb

    def match_faces(self, img1, img2):
        """
        Match two faces and get the cosine similarity. Input images should be Numpy array.
        """
        if not self.session:
            print("Onnx session is not ready")
            return None

        emb1 = self.get_face_embedding(img1)
        emb2 = self.get_face_embedding(img2)
        cosine_sim = np.dot(emb1, emb2)
        return cosine_sim
