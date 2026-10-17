import os
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
import sys
from threading import Thread
import json
import requests

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.navigationdrawer import MDNavigationDrawerMenu
#from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDFloatingActionButton

#
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.lang import Builder
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, BooleanProperty
from kivy.uix.widget import Widget

from plyer import filechooser #, camera as pl_cam

# local imports
from services.faceAi import FaceAiSvc
from screens.init_screen import ModelDownloder
from screens.face_match import TempSpinWait, FaceMatchBox
from screens.security import SecCamBox, SecCamBtn, NameInput, SecurityBox, SecAfterLogin, SecSingleFile
from screens.setting import SettingsBox

# IMPORTANT: Set this property for keyboard behavior
Window.softinput_mode = "below_target"

## Global definitions
__version__ = "0.1.1" # App version

# Determine the base path for your application's resources
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller bundle
    base_path = sys._MEIPASS
else:
    # Running in a normal Python environment
    base_path = os.path.dirname(os.path.abspath(__file__))
kv_file_path = os.path.join(base_path, 'main_layout.kv')

# import platform specific modules
if platform == "android":
    from jnius import autoclass, cast, PythonJavaClass, java_method
    from android.permissions import check_permission, request_permissions, Permission
    from screens.dasKivy.uix.camera import Camera
else:
    from kivy.uix.camera import Camera

## -- kivy custom classes -- ##

class ImageWithAction(ButtonBehavior, Image):
    img_type = StringProperty("none")

class ContentNavigationDrawer(MDNavigationDrawerMenu):
    screen_manager = ObjectProperty()
    nav_drawer = ObjectProperty()

class MainScreenBox(MDBoxLayout):
    top_pad = NumericProperty(0)
    bottom_pad = NumericProperty(0)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if platform == "android":
            try:
                from android.display_cutout import get_height_of_bar
                self.top_pad = int(get_height_of_bar('status'))
                self.bottom_pad = int(get_height_of_bar('navigation'))
            except Exception as e:
                print(f"Failed android 15 padding: {e}")
                self.top_pad = 32
                self.bottom_pad = 48

### --- main app --- ###
class FaceAiApp(MDApp):
    is_downloading = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_keyboard=self.events)
        self.face_ai = None
        self.txt_dialog = None
        self.is_onnx_running = False
        self.models_ok = False
        self.last_instance = None
        self.wake_lock = None
        self.sec_uix = None
        self.camera = None
        self.db_conn_ok = False
        self.data_in_db = False
        self.tmp_spinner = None
        self.login_success = False
        self.face_reg_error = False
        self.sec_file_box = None
        self.sec_file_current_path = None
        self.used_cam_id = None
        self.tmp_login_name = ""
        self.new_face_req = False
        self.user_preferences = {
            "fm_dont_again": False,
            "sec_dont_again": False
        }

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Orange"
        return Builder.load_file(kv_file_path)

    def on_start(self):
        # paths setup
        file_m_height = 1
        if platform == "android":
            file_m_height = 0.9
            from android.storage import app_storage_path
            sdk_version = 28
            try:
                VERSION = autoclass('android.os.Build$VERSION')
                sdk_version = VERSION.SDK_INT
                print(f"Android SDK: {sdk_version}")
                #self.show_toast_msg(f"Android SDK: {sdk_version}")
            except Exception as e:
                print(f"Could not check the android SDK version: {e}")
                #self.show_toast_msg(f"Error checking SDK: {e}", is_error=True)
            self.android_permissions = [Permission.WAKE_LOCK]
            self.total_permissions = [Permission.CAMERA]
            if sdk_version >= 33:  # Android 13+
                self.android_permissions.append(Permission.READ_MEDIA_IMAGES)
            else:  # Android 9–12
                self.android_permissions.extend([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
            self.total_permissions.extend(self.android_permissions)
            request_permissions(self.total_permissions)
            self.internal_storage = app_storage_path()
            self.encrypt_key = None
            try:
                Environment = autoclass("android.os.Environment")
                self.external_storage = Environment.getExternalStorageDirectory().getAbsolutePath()
            except Exception:
                self.external_storage = os.path.abspath("/storage/emulated/0/")
        # non android platforms
        else:
            self.internal_storage = self.user_data_dir
            self.external_storage = os.path.expanduser("~")
            self.encrypt_key = os.path.join(self.internal_storage, 'config', 'vault.key')
        # remaining start activities
        self.model_dir = os.path.join(self.internal_storage, 'model_files')
        self.op_dir = os.path.join(self.internal_storage, 'outputs')
        self.config_dir = os.path.join(self.internal_storage, 'config')
        self.sec_file_dir = os.path.join(self.internal_storage, 'secure_files')
        self.tmp_dir = os.path.join(self.internal_storage, 'tmp_files')
        db_dir = os.path.join(self.internal_storage, 'databases')
        self.last_upload_path = None
        self.last_downlaod_path = None
        self.src_image_path = None
        self.trgt_image_path = None
        self.download_file_path = None
        self.delete_file_path = None
        self.tmp_login_filename = None
        os.makedirs(self.model_dir, exist_ok=True)
        os.makedirs(self.op_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.sec_file_dir, exist_ok=True)
        os.makedirs(self.tmp_dir, exist_ok=True)
        os.makedirs(db_dir, exist_ok=True)
        print(f"Internal model files to be stored in: {self.model_dir}")
        self.config_path = os.path.join(self.config_dir, 'config.json')
        self.resp_path = os.path.join(self.config_dir, 'resp.json')
        self.usr_pref_path = os.path.join(self.config_dir, 'preferences.json')
        self.detect_model_path = os.path.join(self.model_dir, "faceai", "det_10g.onnx")
        self.recog_model_path = os.path.join(self.model_dir, "faceai","arc.onnx")
        self.db_path = os.path.join(db_dir, "master_face.db")
        self.is_inp_file_mgr_open = False
        self.is_op_file_mgr_open = False
        # folder manager for downloading
        self.op_file_manager = MDFileManager(
            exit_manager=self.op_file_exit_manager,
            select_path=self.select_op_path,
            selector="folder",  # Restrict to selecting directories only
            size_hint_y=file_m_height,
        )
        # load / write user preferences at app start
        if os.path.exists(self.usr_pref_path):
            with open(self.usr_pref_path, "r") as pf:
                old_pref = json.load(pf)
            self.user_preferences["fm_dont_again"] = old_pref.get("fm_dont_again", False)
            self.user_preferences["sec_dont_again"] = old_pref.get("sec_dont_again", False)
        else:
            with open(self.usr_pref_path, "w") as pf:
                json.dump(self.user_preferences, pf)
        # set encryption key for non android
        if self.encrypt_key:
            if not os.path.exists(self.encrypt_key):
                from cryptography.fernet import Fernet
                key = Fernet.generate_key()
                with open(self.encrypt_key, "wb") as key_file:
                    key_file.write(key)
                print("Generated the encryption key")
        # check if model files are present
        Clock.schedule_once(lambda dt: self.model_existance_check())
        print("Init success...")

    def acquire_wakelock(self):
        if self.wake_lock:
            return  # already acquired
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            activity = PythonActivity.mActivity
            PowerManager = autoclass("android.os.PowerManager")
            power_manager = cast(PowerManager, activity.getSystemService(Context.POWER_SERVICE))
            # Create wakelock (use PowerManager.FULL_WAKE_LOCK for full wakelock)
            self.wake_lock = power_manager.newWakeLock(
                PowerManager.FULL_WAKE_LOCK, "MyApp::WakeLockTag"
            )
            self.wake_lock.acquire()
            print("WakeLock acquired")
        except Exception as e:
            print(f"Wake lock aquire error: {e}")

    def release_wakelock(self):
        if self.wake_lock and self.wake_lock.isHeld():
            self.wake_lock.release()
            self.wake_lock = None
            print("WakeLock released")

    def save_config_file(self, configData:dict, filepath:str):
        with open(filepath, "w") as pf:
            json.dump(configData, pf)

    def set_usr_pref(self, instance=None):
        self.txt_dialog_closer()
        saveFlag = False
        if self.root.ids.screen_manager.current == "faceFindScr":
            self.user_preferences["fm_dont_again"] = True
            saveFlag = True
        elif self.root.ids.screen_manager.current == "securityScr":
            self.user_preferences["sec_dont_again"] = True
            saveFlag = True
        # save the file
        if saveFlag:
            Clock.schedule_once(lambda dt: self.save_config_file(self.user_preferences, self.usr_pref_path))

    def check_request_android_permission(self):
        if platform == "android":
            permission_flag = True
            for permission in self.android_permissions:
                tmp_flag = check_permission(permission)
                if not tmp_flag:
                    permission_flag = False
                    break
            if not permission_flag:
                request_permissions(self.android_permissions, self.permission_callback)
            return permission_flag
        else:
            return True

    def check_request_total_permission(self):
        if platform == "android":
            permission_flag = True
            for permission in self.total_permissions:
                tmp_flag = check_permission(permission)
                if not tmp_flag:
                    permission_flag = False
                    break
            if not permission_flag:
                request_permissions(self.total_permissions, self.permission_callback)
            return permission_flag
        else:
            return True

    def permission_callback(self, permissions, results):
        # results is a list of booleans corresponding to requested permissions
        usr_deny_flag = False
        if False in results:
            # the user checked "Don't ask again" or denied it twice.
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            current_activity = PythonActivity.mActivity
            # Check rationale status via Android API
            for permission in permissions:
                should_show = current_activity.shouldShowRequestPermissionRationale(permission)
                if not should_show:
                    usr_deny_flag = True
                    break
            if usr_deny_flag:
                # User denied twice / blocked permanently! Show redirect popup.
                print("Permission is denied by user!")
                Clock.schedule_once(lambda dt: self.show_settings_popup())

    def show_settings_popup(self):
        buttons = [
            MDFlatButton(
                text="Cancel",
                theme_text_color="Custom",
                text_color=self.theme_cls.primary_color,
                on_release=self.txt_dialog_closer
            ),
            MDFlatButton(
                text="Open Settings",
                theme_text_color="Custom",
                text_color="orange",
                on_release=self.open_android_settings
            ),
        ]
        self.show_text_dialog(
            "Permissions Missing",
            "Please grant the permissions from Settings.",
            buttons
        )

    def open_android_settings(self, instance=None):
        self.txt_dialog_closer()
        # Target Android Native Intents
        Intent = autoclass('android.content.Intent')
        Settings = autoclass('android.provider.Settings')
        Uri = autoclass('android.net.Uri')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        # Create intent to open this specific app's settings details
        activity = PythonActivity.mActivity
        intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
        uri = Uri.fromParts("package", activity.getPackageName(), None)
        intent.setData(uri)
        # Launch settings
        activity.startActivity(intent)

    def show_toast_msg(self, message, is_error=False, duration=3):
        from kivymd.uix.snackbar import MDSnackbar
        bg_color = (0.2, 0.6, 0.2, 1) if not is_error else (0.8, 0.2, 0.2, 1)
        MDSnackbar(
            MDLabel(
                text = message,
                font_style = "Subtitle1"
            ),
            md_bg_color=bg_color,
            y=dp(24),
            pos_hint={"center_x": 0.5},
            duration=duration
        ).open()

    def show_text_dialog(self, title, text="", buttons=[]):
        self.txt_dialog = MDDialog(
            title=title,
            text=text,
            buttons=buttons
        )
        self.txt_dialog.open()

    def txt_dialog_closer(self, instance=None):
        if self.txt_dialog:
            self.txt_dialog.dismiss()

    def model_download_popup(self, instance=None):
        buttons = [
            MDFlatButton(
                text="Cancel",
                theme_text_color="Custom",
                text_color=self.theme_cls.primary_color,
                on_release=self.txt_dialog_closer
            ),
            MDFlatButton(
                text="Download",
                theme_text_color="Custom",
                text_color="green",
                on_release=self.start_model_download
            ),
        ]
        self.show_text_dialog(
            "Download model files",
            "You need to downlaod the models first (~140MB).",
            buttons
        )

    def unzip_model(self, filepath):
        import tarfile
        try:
            with tarfile.open(filepath, "r:gz") as tar:
                tar.extractall(path=self.model_dir)
            os.remove(filepath)
            self.show_toast_msg("Model files have been downloaded successfully.")
            self.is_downloading = False
            if platform == "android":
                Clock.schedule_once(lambda dt: self.release_wakelock())
        except Exception as e:
            print(f"Unzip error: {e}")

    def update_download_progress(self, downloaded, total_size):
        if total_size > 0:
            percentage = (downloaded / total_size) * 100
            self.download_progress.text = f"Progress: {percentage:.1f}%"
        else:
            self.download_progress.text = f"Progress: {downloaded} bytes"

    def download_file(self, download_url, download_path):
        filename = download_url.split("/")[-1]
        try:
            self.is_downloading = filename
            with requests.get(download_url, stream=True) as req:
                req.raise_for_status()
                total_size = int(req.headers.get('content-length', 0))
                downloaded = 0
                with open(download_path, 'wb') as f:
                    for chunk in req.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            Clock.schedule_once(lambda dt: self.update_download_progress(downloaded, total_size))
            if os.path.exists(download_path):
                Clock.schedule_once(lambda dt: self.unzip_model(download_path))
            else:
                Clock.schedule_once(lambda dt: self.show_toast_msg(f"Download failed for: {download_path}", is_error=True))
            self.is_downloading = False
        except requests.exceptions.RequestException as e:
            print(f"Error downloading the onnx file: {e} 😞")
            Clock.schedule_once(lambda dt: self.show_toast_msg(f"Download failed for: {download_path}", is_error=True))
            self.is_downloading = False
        Clock.schedule_once(lambda dt: self.download_progress.dismiss())

    def download_model_file(self, model_url, download_path, instance=None):
        self.txt_dialog_closer(instance)
        filename = download_path.split("/")[-1]
        print(f"Starting the download for: {filename}")

        self.download_progress = MDDialog(
            title=f"Downloading {filename}",
            text="Starting download process...",
            #buttons=buttons
        )
        self.download_progress.open()
        Thread(target=self.download_file, args=(model_url, download_path), daemon=True).start()

    def start_model_download(self, instance=None):
        if self.is_downloading:
            self.show_toast_msg("Please wait for the download to finish", is_error=True)
            return
        if platform == "android":
            Clock.schedule_once(lambda dt: self.acquire_wakelock())
        download_path = os.path.join(self.model_dir, "faceai.tar.gz")
        model_url = "https://github.com/daslearning-org/face-ai/releases/download/vOnnxModels/faceai.tar.gz"
        self.download_model_file(model_url, download_path)

    def model_existance_check(self):
        if os.path.exists(self.detect_model_path) and os.path.exists(self.recog_model_path):
            self.models_ok = True
        else:
            Clock.schedule_once(lambda dt: self.model_download_popup())
            return

    def start_face_services(self, instance=None):
        self.txt_dialog_closer()
        if self.models_ok and self.face_ai:
            self.show_toast_msg("Session is already active")
        if os.path.exists(self.detect_model_path) and os.path.exists(self.recog_model_path):
            self.models_ok = True
        else:
            self.model_download_popup()
            return
        self.face_ai = FaceAiSvc(self.detect_model_path, self.recog_model_path, self.op_dir)
        start_svc_btn = self.root.ids.init_screen.ids.start_svc_btn
        try:
            self.face_ai.start_detection_session()
            self.face_ai.start_recognition_session()
            self.show_toast_msg("Sesstions started successfully")
            start_svc_btn.text = "Service Started"
            start_svc_btn.md_bg_color = 'gray'
        except Exception as e:
            print(f"Could not start the sessions: {e}")
            self.show_toast_msg("Couldn't start the services", is_error=True)
            self.face_ai = None

    def goto_face_matcher(self, instance=None):
        self.root.ids.screen_manager.current = "faceFindScr"

    def on_face_matcher_entry(self, instance=None):
        if self.user_preferences["fm_dont_again"]:
            return
        buttons = [
            MDFlatButton(
                text="Don't Show Again",
                theme_text_color="Custom",
                text_color='orange',
                on_release=self.set_usr_pref
            ),
            MDFlatButton(
                text="Ok",
                theme_text_color="Custom",
                text_color="green",
                on_release=self.txt_dialog_closer
            ),
        ]
        self.show_text_dialog(
            "Instructions",
            "Upload an image with Single Face as Source image & any image with one or more Faces as Target image. Once the face tagged images are generated, you can tap on that to Downlaod or Delete.",
            buttons
        )

    def open_img_file_manager(self, instance=None):
        permissions_ok = self.check_request_android_permission()
        if not permissions_ok:
            return
        try:
            if not self.last_upload_path:
                self.last_upload_path = self.external_storage
            filechooser.open_file(
                on_selection = self.handle_img_selection,
                path = self.last_upload_path,
                multiple = False,
                filters = [["*.JPG", "*.jpg", "*.png", "*.jpeg", "*.webp"], "*"],
                preview = True,
            )
            self.is_inp_file_mgr_open = True
            if instance == "btn_fm_src_upload":
                self.img_purpose = "src"
            elif instance == "btn_fm_tgt_upload":
                self.img_purpose = "trgt"
        except Exception as e:
            self.show_toast_msg(f"Error: {e}", is_error=True)

    def handle_img_selection(self, selection=None):
        '''
        Callback function for handling the image selection.
        '''
        self.is_inp_file_mgr_open = False
        if selection:
            image_path = str(selection[0])
            self.last_upload_path = os.path.dirname(image_path)
            Clock.schedule_once(lambda dt: self.select_img_path(image_path))

    def select_img_path(self, path: str):
        if not path.endswith((".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG", ".webp", ".WEBP")):
            self.show_toast_msg(f"Selected file: `{path}` is not an image", is_error=True)
            return

        fitImage = Image(
            source = path,
            fit_mode = "contain"
        )

        if self.img_purpose == "src":
            upload_image_box = self.root.ids.face_match_scr.ids.fm_up_src_box
            self.src_image_path = path
        elif self.img_purpose == "trgt":
            upload_image_box = self.root.ids.face_match_scr.ids.fm_up_trgt_box
            self.trgt_image_path = path

        upload_image_box.clear_widgets()
        upload_image_box.add_widget(fitImage)

    def submit_face_match(self, instance=None):
        """
        Performs the face match job in a separate thread with callback option.
        """
        if not self.face_ai:
            self.show_text_dialog(
                title="Service is not started",
                text=f"Do you want to start the service?.",
                buttons=[
                    MDFlatButton(
                        text="Cancel",
                        theme_text_color="Custom",
                        text_color="blue",
                        on_release=self.txt_dialog_closer
                    ),
                    MDFlatButton(
                        text="START",
                        theme_text_color="Custom",
                        text_color="green",
                        on_release=self.start_face_services
                    ),
                ],
            )
            return
        if self.is_onnx_running:
            self.show_toast_msg("Please wait for the previous job to finish!", is_error=True)
            return
        if not self.src_image_path or not self.trgt_image_path:
            self.show_toast_msg("Please upload both the source & target image", is_error=True)
            return
        src_box = self.root.ids.face_match_scr.ids.fm_gen_src_box
        trgt_box = self.root.ids.face_match_scr.ids.fm_gen_trgt_box
        src_box.clear_widgets()
        trgt_box.clear_widgets()
        onnx_thread = Thread(
            target=self.face_ai.face_match_group,
            kwargs={
                "img1_path": self.src_image_path,
                "img2_path": self.trgt_image_path,
                "callback": self.face_match_callback
            },
            daemon=True
        )
        onnx_thread.start()
        self.is_onnx_running = True
        spinner1 = TempSpinWait()
        spinner2 = TempSpinWait()
        src_box.add_widget(spinner1)
        trgt_box.add_widget(spinner2)

    def face_match_callback(self, resp):
        self.is_onnx_running = False
        stat = resp["stat"]
        msg = resp["msg"]
        src = resp["src"]
        trgt = resp["trgt"]
        src_box = self.root.ids.face_match_scr.ids.fm_gen_src_box
        trgt_box = self.root.ids.face_match_scr.ids.fm_gen_trgt_box
        src_box.clear_widgets()
        trgt_box.clear_widgets()
        if stat:
            srcImage = ImageWithAction(
                source = src,
                fit_mode = "contain"
            )
            trgtImage = ImageWithAction(
                source = trgt,
                fit_mode = "contain"
            )
            srcImage.img_type = "src"
            trgtImage.img_type = "trgt"
            srcImage.bind(on_release=self.download_image_from_view)
            trgtImage.bind(on_release=self.download_image_from_view)
            src_box.add_widget(srcImage)
            trgt_box.add_widget(trgtImage)
        else:
            label = MDLabel(
                text=msg,
                halign="center",
                valign="center",
                markup=True
            )
            src_box.add_widget(label)

    def download_image_from_view(self, instance=None):
        if instance:
            self.download_file_path = instance.source
            self.delete_file_path = instance.source
            self.last_instance = instance
            self.show_text_dialog(
                title="Download or Delete?",
                text=f"You can downlaod or delete this file",
                buttons=[
                    MDFlatButton(
                        text="Canel",
                        theme_text_color="Custom",
                        text_color="blue",
                        on_release=self.txt_dialog_closer
                    ),
                    MDFlatButton(
                        text="DELETE",
                        theme_text_color="Custom",
                        text_color="red",
                        on_release=self.delete_selected_file
                    ),
                    MDFlatButton(
                        text="Download",
                        theme_text_color="Custom",
                        text_color="green",
                        on_release=self.download_from_app_local
                    ),
                ],
            )

    def download_from_app_local(self, instance=None):
        self.txt_dialog_closer()
        if self.download_file_path:
            #dir_name = os.path.dirname(self.download_file_path)
            if not self.last_downlaod_path:
                self.last_downlaod_path = str(self.external_storage)
            self.op_file_manager.show(self.last_downlaod_path)
            self.is_op_file_mgr_open = True

    def select_op_path(self, path: str):
        """
        Called when a directory is selected. Save the Output file.
        """
        self.op_file_exit_manager()
        filename = os.path.basename(self.download_file_path)
        dir_name = os.path.dirname(path)
        self.last_downlaod_path = dir_name
        chosen_path = os.path.join(path, filename) # destination path
        try:
            if (self.root.ids.screen_manager.current in ("faceFindScr") or 
                platform == "android"
            ):
                import shutil
                shutil.copyfile(self.download_file_path, chosen_path)
                self.delete_file_path = str(self.download_file_path)
                self.download_file_path = None
                if (self.root.ids.screen_manager.current in ("faceFindScr")):
                    self.delete_file_popup()
            elif (self.root.ids.screen_manager.current in ("securityScr") and 
                  platform != "android"
                ):
                # decrypt the data
                from cryptography.fernet import Fernet
                with open(self.encrypt_key, "rb") as key_file:
                    key = key_file.read()
                fernet = Fernet(key)
                with open(self.download_file_path, "rb") as enc_file:
                    encrypted_data = enc_file.read()
                decrypted_data = fernet.decrypt(encrypted_data)
                with open(chosen_path, "wb") as file:
                    file.write(decrypted_data)
            print(f"File successfully download to: {chosen_path}")
            self.show_toast_msg(f"File download to: {chosen_path}")
        except Exception as e:
            print(f"Error saving file: {e}")
            self.show_toast_msg(f"Error saving file: {e}", is_error=True)

    def op_file_exit_manager(self, *args):
        """Called when the user reaches the root of the directory tree."""
        self.is_op_file_mgr_open = False
        self.op_file_manager.close()

    def delete_file_popup(self, instance=None):
        filename = os.path.basename(self.delete_file_path)
        self.show_text_dialog(
            title="Delete the file?",
            text=f"Your download {filename} was successful. You can now Delete the file.",
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    theme_text_color="Custom",
                    text_color="blue",
                    on_release=self.txt_dialog_closer
                ),
                MDFlatButton(
                    text="DELETE",
                    theme_text_color="Custom",
                    text_color="red",
                    on_release=self.delete_selected_file
                ),
            ],
        )

    def delete_selected_file(self, instance=None):
        self.txt_dialog_closer()
        if self.delete_file_path:
            try:
                os.remove(self.delete_file_path)
                self.show_toast_msg(f"Deleted: {self.delete_file_path}")
                print(f"Deleted: {self.delete_file_path}")
                self.delete_file_path = None
                if self.last_instance and self.last_instance.parent:
                    Clock.schedule_once(lambda dt: self.last_instance.parent.remove_widget(self.last_instance))
                    #self.last_instance = None
            except Exception as e:
                print(f"Error while deleting {self.delete_file_path} because: {e}")
                self.show_toast_msg(f"Error while deleting {self.delete_file_path} because: {e}", is_error=True)

    def reset_face_matcher(self, instance=None):
        self.src_image_path = None
        self.trgt_image_path = None
        self.img_purpose = ""
        src_box = self.root.ids.face_match_scr.ids.fm_gen_src_box
        trgt_box = self.root.ids.face_match_scr.ids.fm_gen_trgt_box
        src_box.clear_widgets()
        trgt_box.clear_widgets()
        upload_src_box = self.root.ids.face_match_scr.ids.fm_up_src_box
        upload_trgt_box = self.root.ids.face_match_scr.ids.fm_up_trgt_box
        upload_src_box.clear_widgets()
        upload_trgt_box.clear_widgets()

    # Security section starts here
    def on_security_enter(self):
        permissions_ok = self.check_request_total_permission()
        if not permissions_ok:
            return
        if not self.face_ai:
            self.show_toast_msg("Please start the services first.", is_error=True, duration=2)
            self.root.ids.screen_manager.current = "initScreen"
            return
        self.on_security_leave() # clear existing things
        self.sec_uix = self.root.ids.security_box.ids.sec_elements_box
        self.db_conn_ok = self.face_ai.start_db_session(self.db_path)
        if self.db_conn_ok:
            self.tmp_spinner = TempSpinWait()
            self.tmp_spinner.text_to_show = "Checking database, please wait..."
            self.sec_uix.add_widget(self.tmp_spinner)
            height_widget = Widget(
                size_hint_y = 0.5
            )
            self.sec_uix.add_widget(height_widget)
            Clock.schedule_once(lambda dt: self.face_ai.check_if_data_exist(self._init_security_callback))

    def android_front_cam(self):
        from services.androidSvc import AndroidSvc
        cam_svc = AndroidSvc()
        cam_map = cam_svc.get_camera_details()
        cam_id = cam_map.get("front", None)
        return cam_id

    def add_camera(self, parent_element):
        #self.sec_uix = self.root.ids.security_box.ids.camera_box
        self.on_security_leave()
        self.sec_uix = parent_element
        cam_indx = -1
        if platform == "android":
            if self.used_cam_id is not None:
                cam_indx = int(self.used_cam_id)
            else:
                self.used_cam_id = self.android_front_cam()
                cam_indx = int(self.used_cam_id)
            resolution = (960, 720) # will fallback to 480 if fails again
            import datetime
            now = datetime.datetime.now()
            current_time = str(now.strftime("%H%M%S"))
            current_date = str(now.strftime("%Y%m%d"))
            self.tmp_login_filename = os.path.join(self.sec_file_dir, f"login_{current_date}_{current_time}.jpg")
        # for non-android devices
        else:
            resolution = (640, 480)
            if not self.camera:
                if self.used_cam_id is not None:
                    cam_indx = int(self.used_cam_id)
                else:
                    import cv2
                    available_cameras = []
                    for i in range(2):
                        cap = cv2.VideoCapture(i)
                        if cap.isOpened():
                            print(f"Camera found at index: {i}")
                            available_cameras.append(i)
                            cap.release()
                    if len(available_cameras) >= 1:
                        self.used_cam_id = cam_indx = available_cameras[0]
                    else:
                        self.show_toast_msg(f"No camera found on {platform}!", is_error=True)
                        return
        # using custom kivy cam for all env
        try:
            if not self.camera:
                self.camera = Camera(
                    index = cam_indx,
                    resolution = resolution,
                    fit_mode = "contain",
                    play = True
                )
            else:
                self.camera.play = True
            self.sec_uix.add_widget(self.camera)
        except Exception as e:
            print(f"Error setting up the camera: {e}")
            self.show_toast_msg(f"Error setting up the camera: {e}", is_error=True)

    def add_name_input(self, parent_element):
        name_inp_elem = NameInput()
        parent_element.add_widget(name_inp_elem)

    def add_login_btn(self, parent_element):
        login_btn = SecCamBtn()
        height_widget = Widget(
            size_hint_y = 0.5
        )
        parent_element.add_widget(login_btn)
        parent_element.add_widget(height_widget)

    def _init_security_callback(self, resp): # should not be called directly
        if self.login_success:
            self.sec_login_ok()
            return
        if self.sec_uix:
            self.sec_uix.clear_widgets()
        if not resp: # no data found 
            self.add_camera(self.root.ids.security_box.ids.sec_elements_box)
            self.add_name_input(self.root.ids.security_box.ids.sec_elements_box)
        else: # data found, need login
            self.data_in_db = True
            self.add_camera(self.root.ids.security_box.ids.sec_elements_box)
            self.add_login_btn(self.root.ids.security_box.ids.sec_elements_box)

    def add_new_face(self, instance=None):
        self.on_security_leave()
        self.add_camera(self.root.ids.security_box.ids.sec_elements_box)
        self.add_name_input(self.root.ids.security_box.ids.sec_elements_box)

    def get_sec_file_list(self, path:str):
        files = []
        for filename in os.listdir(path):
            files.append(filename)
        return files

    def refresh_sec_file_list(self, instance=None):
        if self.sec_file_box:
            secMdList = self.sec_file_box.ids.sec_file_list
            secMdList.clear_widgets()
            sec_files = self.get_sec_file_list(self.sec_file_dir)
            for file in sec_files:
                fileElem = SecSingleFile()
                fileElem.filename = str(file)
                secMdList.add_widget(fileElem)

    def after_login_instructions(self):
        if self.user_preferences["sec_dont_again"]:
            return
        else:
            buttons = [
                MDFlatButton(
                    text="Don't Show Again",
                    theme_text_color="Custom",
                    text_color='orange',
                    on_release=self.set_usr_pref
                ),
                MDFlatButton(
                    text="Ok",
                    theme_text_color="Custom",
                    text_color="green",
                    on_release=self.txt_dialog_closer
                ),
            ]
            self.show_text_dialog(
                "Instructions",
                "You can upload your secret files here. You can download them later. You can add a new face for login.",
                buttons
            )

    def sec_login_ok(self, msg:str="Login"):
        self.on_security_leave()
        self.sec_file_box = SecAfterLogin()
        secMdList = self.sec_file_box.ids.sec_file_list
        sec_files = self.get_sec_file_list(self.sec_file_dir)
        for file in sec_files:
            fileElem = SecSingleFile()
            fileElem.filename = str(file)
            secMdList.add_widget(fileElem)
        self.sec_uix.add_widget(self.sec_file_box)
        self.login_success = True
        self.after_login_instructions()
        print(f"{msg} is successful!")

    def sec_face_login_save(self, name:str, img, newFace=False):
        if not self.data_in_db or newFace:
            matched_name = None
            if len(name) < 3:
                self.show_toast_msg("Please enter a proper name", True)
                return
            if self.data_in_db:
                matched_name = self.face_ai.face_verify(img)
            if matched_name is None:
                stat = self.face_ai.save_faces_masterdb(name, img)
                if stat:
                    self.data_in_db = True
                    self.login_success = False
                    self.on_security_enter()
                    Clock.schedule_once(lambda dt: self.show_toast_msg(f"{name}'s face has been added in database."))
                else:
                    self.show_toast_msg("Face is not saved, please try again", True)
                    self.face_reg_error = True
            else:
                msg = f"This face is already saved for: {str(matched_name)}"
                self.login_success = False
                self.on_security_enter()
                Clock.schedule_once(lambda dt: self.show_toast_msg(msg))
        else:
            print("There is existing face(s)")
            matched_name = self.face_ai.face_verify(img)
            if matched_name is None:
                self.show_toast_msg("Face is not matched", True)
            else:
                msg = f"Logged in as: {str(matched_name)}"
                self.sec_login_ok()
                Clock.schedule_once(lambda dt: self.show_toast_msg(msg))

    def sec_capture_frame(self, instance=None, newFace=False):
        if not self.camera or not self.camera.texture:
            self.show_toast_msg("Camera is Not OK", True, 2)
            return
        if instance:
            name_txt = str(instance.text)
            name_txt = name_txt.strip()
        else:
            name_txt = ""
        try:
            import cv2
            import numpy as np
            texture = self.camera.texture
            pixels = texture.pixels
            width, height = texture.size
            arr = np.frombuffer(pixels, dtype=np.uint8).reshape((height, width, 4))
            img = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            if platform == 'android':
                img = np.flipud(img)  # Flip up down in android
                #cv2.imwrite(self.tmp_login_filename, img) # to debug the capture
            #print(img)
            self.sec_face_login_save(name_txt, img, newFace)
        except Exception as e:
            print(f"Error processing frame: {e}")

    def vault_file_saver(self, file_path:str):
        filename = os.path.basename(file_path)
        target_file = os.path.join(self.sec_file_dir, filename)
        try:
            if platform == "android":
                # encryption not required on android as the internal path is secure
                import shutil
                shutil.copyfile(file_path, target_file)
            else:
                # store encrypted data
                from cryptography.fernet import Fernet
                with open(self.encrypt_key, "rb") as key_file:
                    key = key_file.read()
                fernet = Fernet(key)
                with open(file_path, "rb") as file:
                    original_data = file.read()
                encrypted_data = fernet.encrypt(original_data)
                with open(target_file, "wb") as tfile:
                    tfile.write(encrypted_data)
            print(f"File {filename} successfully uploaded to vault")
            self.refresh_sec_file_list()
            self.show_toast_msg(f"File {filename} successfully uploaded to vault")
        except Exception as e:
            print(f"Error saving file: {e}")
            self.show_toast_msg(f"Error saving file: {e}", is_error=True)

    def save_in_vault(self, selection):
        self.is_inp_file_mgr_open = False
        if selection:
            file_path = str(selection[0])
            self.last_upload_path = os.path.dirname(file_path)
            Clock.schedule_once(lambda dt: self.vault_file_saver(file_path))

    def upload_to_vault(self, instance=None):
        permissions_ok = self.check_request_android_permission()
        if not permissions_ok:
            return
        try:
            if not self.last_upload_path:
                self.last_upload_path = self.external_storage
            filechooser.open_file(
                on_selection = self.save_in_vault,
                path = self.last_upload_path,
                multiple = False,
                filters = [["*.JPG", "*.jpg", "*.png", "*.jpeg", "*.webp"], "*"],
                preview = True,
            )
            self.is_inp_file_mgr_open = True
        except Exception as e:
            self.show_toast_msg(f"Error: {e}", is_error=True)

    def download_sec_file(self, instance):
        filename = str(instance.filename)
        full_path = os.path.join(self.sec_file_dir, filename)
        self.download_file_path = str(full_path)
        self.download_from_app_local()

    def popup_sec_file_delete(self, instance):
        filename = str(instance.filename)
        self.last_instance = instance
        self.delete_file_path = os.path.join(self.sec_file_dir, filename)
        self.show_text_dialog(
            title="Delete the file?",
            text=f"Do you want to delete: {filename} ?",
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    theme_text_color="Custom",
                    text_color="blue",
                    on_release=self.txt_dialog_closer
                ),
                MDFlatButton(
                    text="DELETE",
                    theme_text_color="Custom",
                    text_color="red",
                    on_release=self.delete_selected_file
                ),
            ],
        )

    def on_security_leave(self):
        if self.camera:
            self.camera.play = False
            if platform == "android":
                self.camera = None
            print("Camera has been stopped")
        if self.sec_uix:
            self.sec_uix.clear_widgets()

    # Settings section start here
    def show_all_delete_alert(self):
        op_img_count = 0
        for filename in os.listdir(self.op_dir):
            if filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png"):
                op_img_count += 1
        self.show_text_dialog(
            title="Delete all output files?",
            text=f"There are total: {op_img_count} image files. This action cannot be undone!",
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    theme_text_color="Custom",
                    text_color=self.theme_cls.primary_color,
                    on_release=self.txt_dialog_closer
                ),
                MDFlatButton(
                    text="DELETE",
                    theme_text_color="Custom",
                    text_color="red",
                    on_release=self.delete_all_op_action
                ),
            ],
        )

    def delete_all_op_action(self, instance):
        # Custom function called when DISCARD is clicked
        for filename in os.listdir(self.op_dir):
            if filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png"):
                file_path = os.path.join(self.op_dir, filename)
                try:
                    os.unlink(file_path)
                    print(f"Deleted {file_path}")
                except Exception as e:
                    print(f"Could not delete the audion files, error: {e}")
        self.show_toast_msg("Executed the audio cleanup!")
        self.txt_dialog_closer(instance)
        # Will add a cleanup option for the generated options on screen.

    def open_link(self, instance, url):
        import webbrowser
        webbrowser.open(url)

    def update_link_open(self, instance=None):
        self.txt_dialog_closer(instance)
        self.open_link(instance=instance, url="https://github.com/daslearning-org/face-ai/releases")

    def update_checker(self, instance=None):
        buttons = [
            MDFlatButton(
                text="Cancel",
                theme_text_color="Custom",
                text_color=self.theme_cls.primary_color,
                on_release=self.txt_dialog_closer
            ),
            MDFlatButton(
                text="Releases",
                theme_text_color="Custom",
                text_color="green",
                on_release=self.update_link_open
            ),
        ]
        self.show_text_dialog(
            "Check for update",
            f"Your version: {__version__}",
            buttons
        )

    # Handling the device events (mostly on Android)
    def on_pause(self):
        self.login_success = False
        return True

    def events(self, instance, keyboard, keycode, text, modifiers):
        """Handle mobile device button presses (e.g., Android back button)."""
        if keyboard in (1001, 27):
            # control file manager with back btn on android
            if self.is_op_file_mgr_open:
                if self.op_file_manager.current_path == self.external_storage:
                    self.show_toast_msg(f"Closing file manager from main storage")
                    self.op_file_exit_manager()
                else:
                    self.op_file_manager.back() # go one dir back
                # stop app from exiting
                return True
            if self.face_reg_error:
                self.on_security_enter()
        # exits from app
        return False

## -- run the app -- ##
if __name__ == '__main__':
    FaceAiApp().run()