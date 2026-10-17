from jnius import autoclass


class AndroidSvc:

    def __init__(self):
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        self.Context = autoclass('android.content.Context')
        self.activity = PythonActivity.mActivity

    def get_camera_list(self):
        camera_manager = self.activity.getSystemService(
            self.Context.CAMERA_SERVICE
        )
        camera_ids = camera_manager.getCameraIdList()
        print(f"Android camera ids: {str(camera_ids)}")
        return camera_ids

    def get_camera_details(self):
        camera_map = {
            "front": None,
            "back": None
        }
        camera_manager = self.activity.getSystemService(
            self.Context.CAMERA_SERVICE
        )
        CameraCharacteristics = autoclass(
            'android.hardware.camera2.CameraCharacteristics'
        )
        camera_ids = camera_manager.getCameraIdList()
        for cam_id in camera_ids:
            chars = camera_manager.getCameraCharacteristics(cam_id)
            facing = chars.get(
                CameraCharacteristics.LENS_FACING
            )
            if facing == CameraCharacteristics.LENS_FACING_FRONT:
                print(cam_id, "FRONT")
                camera_map["front"] = int(cam_id)
            elif facing == CameraCharacteristics.LENS_FACING_BACK:
                print(cam_id, "BACK")
                camera_map["back"] = int(cam_id)
            else:
                print(cam_id, "EXTERNAL")
        # return the details
        return camera_map
