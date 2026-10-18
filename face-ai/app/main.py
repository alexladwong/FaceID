import os
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
import sys
from threading import Thread
import json
import re
import datetime
import subprocess
import requests

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.navigationdrawer import MDNavigationDrawerItem
#from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDFloatingActionButton

#
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import PopMatrix, PushMatrix, Rotate
from kivy.utils import platform, get_color_from_hex
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
from screens import tokens
from screens.face_match import FaceMatchBox
from screens.init_screen import InitBox
from screens.security import (
    CameraCard,
    LoadingCard,
    LoginCard,
    RegisterCard,
    SecAfterLogin,
    SecSingleFile,
    SecurityBox,
    SecurityTipsCard,
)
from screens.setting import SettingsBox
from screens.ui import BusyState, EmptyState, NoticeCard, RecentTile

# IMPORTANT: Set this property for keyboard behavior
Window.softinput_mode = "below_target"

## Global definitions
__version__ = "0.1.1" # App version
MODEL_URL = "https://github.com/daslearning-org/face-ai/releases/download/vOnnxModels/faceai.tar.gz"

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
    initial_window_size = (1200, 820)

    # UI state (declared as properties so the kv file can bind to them)
    models_ready = BooleanProperty(False)
    services_running = BooleanProperty(False)
    download_active = BooleanProperty(False)
    download_progress_value = NumericProperty(0)
    download_status_text = StringProperty("")
    is_onnx_running = BooleanProperty(False)
    verifying = BooleanProperty(False)
    face_tip_visible = BooleanProperty(True)
    vault_tip_visible = BooleanProperty(True)
    ready_to_match = BooleanProperty(False)
    is_desktop = BooleanProperty(False)
    is_wide = BooleanProperty(False)
    nav_offset = NumericProperty(dp(232))
    home_action_label = StringProperty("Start face engine")
    home_action_icon = StringProperty("play")
    app_version = StringProperty(__version__)
    output_count = NumericProperty(0)
    output_count_label = StringProperty("No generated images yet")
    logo_path = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_keyboard=self.events)
        Window.bind(on_key_down=self._on_key_down)
        self.logo_path = os.path.join(base_path, "data", "images", "favicon.png")
        self.is_desktop = platform not in ("android", "ios")
        self.face_ai = None
        self.txt_dialog = None
        self._toast = None
        self.models_ok = False
        self.last_instance = None
        self.wake_lock = None
        self.sec_uix = None
        self.camera = None
        self.camera_card = None
        self.sec_name_input = None
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
        self.img_purpose = ""
        self.user_preferences = {
            "fm_dont_again": False,
            "sec_dont_again": False
        }
        self.is_wide = Window.width >= 980
        self._drawer_open = False
        Window.bind(on_resize=self._on_window_resize)
        self.bind(
            models_ready=self._update_home_action,
            services_running=self._update_home_action,
            download_active=self._update_home_action,
        )

    def build(self):
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.accent_palette = "Teal"
        self.theme_cls.theme_style = "Light"
        self.title = "Face AI"
        try:
            self.icon = self.logo_path
        except Exception:
            pass
        if self.is_desktop:
            Window.size = self.initial_window_size
            Window.clearcolor = get_color_from_hex(tokens.SURFACE)
        self.is_wide = Window.width >= 980
        return Builder.load_file(kv_file_path)

    # -- responsive shell / dashboard helpers ------------------------
    def _on_window_resize(self, window, width, height):
        self.is_wide = width >= 980
        if self.root:
            if self.is_wide:
                self.close_drawer()
            self._apply_nav_mode()
            self.refresh_recent_outputs()

    def _apply_nav_mode(self):
        if not self.root:
            return
        ids = self.root.ids
        panel = ids.get("nav_panel")
        scrim = ids.get("drawer_scrim")
        if panel is None:
            return
        if self.is_wide:
            self.nav_offset = dp(232)
            panel.x = 0
            panel.disabled = False
            self._drawer_open = False
            if scrim is not None:
                scrim.opacity = 0
                scrim.disabled = True
        else:
            self.nav_offset = 0
            panel.disabled = False
            if not self._drawer_open:
                panel.x = -panel.width

    def open_drawer(self, instance=None):
        if self.is_wide or not self.root:
            return
        panel = self.root.ids.nav_panel
        scrim = self.root.ids.drawer_scrim
        self._drawer_open = True
        panel.x = -panel.width
        scrim.disabled = False
        Animation(x=0, d=.18, t="out_quad").start(panel)
        Animation(opacity=1, d=.16).start(scrim)

    def close_drawer(self, instance=None):
        if not self.root:
            return
        panel = self.root.ids.get("nav_panel")
        scrim = self.root.ids.get("drawer_scrim")
        if panel is None:
            return
        was_open = self._drawer_open
        self._drawer_open = False
        Animation(x=-panel.width, d=.16, t="in_quad").start(panel)
        if scrim is not None:
            Animation(opacity=0, d=.16).start(scrim)
            Clock.schedule_once(lambda dt: setattr(scrim, "disabled", True), .18)
        if not was_open:
            panel.x = -panel.width

    def _wire_navigation(self):
        manager = self.root.ids.screen_manager
        menu = self.root.ids.get("nav_menu")
        if menu:
            menu.screen_manager = manager
        self._apply_nav_mode()
        self._set_nav_selection(manager.current)

    def _update_home_action(self, *args):
        if self.download_active:
            self.home_action_label = "Downloading models..."
            self.home_action_icon = "download"
        elif not self.models_ready:
            self.home_action_label = "Download models"
            self.home_action_icon = "download"
        elif not self.services_running:
            self.home_action_label = "Start face engine"
            self.home_action_icon = "play"
        else:
            self.home_action_label = "Open Face Finder"
            self.home_action_icon = "account-search"

    def home_action(self, instance=None):
        if self.download_active:
            return
        if not self.models_ready:
            self.start_model_download()
        elif not self.services_running:
            self.start_face_services()
        else:
            self.goto_screen("faceFindScr")

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        if self._drawer_open and key == 27:
            self.close_drawer()
            return True
        meta = "meta" in modifiers or "ctrl" in modifiers
        if not meta:
            return False
        screen = self.root.ids.screen_manager.current if self.root else ""
        if codepoint in ("1", "2", "3", "4"):
            target = {
                "1": "initScreen",
                "2": "faceFindScr",
                "3": "securityScr",
                "4": "settingsScr",
            }[codepoint]
            self.goto_screen(target)
            return True
        if codepoint == "o" and screen == "faceFindScr":
            self.open_img_file_manager(self.img_purpose or "src")
            return True
        if codepoint == "r" and screen == "faceFindScr":
            self.reset_face_matcher()
            return True
        if codepoint == "l" and screen == "securityScr":
            self.lock_vault()
            return True
        if codepoint == "h":
            self.show_help_dialog()
            return True
        return False

    def goto_screen(self, name):
        self.root.ids.screen_manager.current = name
        self._set_nav_selection(name)
        if self._drawer_open:
            self.close_drawer()

    def _set_nav_selection(self, current):
        labels = {
            "Home": "initScreen",
            "Face Finder": "faceFindScr",
            "Secure Vault": "securityScr",
            "Settings": "settingsScr",
        }
        menu = self.root.ids.get("nav_menu")
        if not menu:
            return
        for widget in menu.walk():
            if isinstance(widget, MDNavigationDrawerItem):
                widget.selected = labels.get(widget.text) == current

    def _open_path(self, path):
        if not path or not os.path.exists(path):
            self.show_toast_msg("That file is no longer available.", is_error=True)
            return
        try:
            if platform == "macosx":
                subprocess.Popen(["open", path])
            elif platform == "win":
                os.startfile(path)
            elif platform == "linux":
                subprocess.Popen(["xdg-open", path])
            else:
                self.show_toast_msg("Opening files is not supported on this device.")
        except Exception as e:
            print(f"Could not open {path}: {e}")
            self.show_toast_msg("Could not open that file.", is_error=True)

    def open_file(self, path, instance=None):
        self._open_path(path)

    def open_outputs_folder(self, instance=None):
        self._open_path(self.op_dir)

    def refresh_recent_outputs(self, instance=None):
        if not self.root:
            return
        try:
            files = [
                os.path.join(self.op_dir, name)
                for name in os.listdir(self.op_dir)
                if name.lower().endswith((".jpg", ".jpeg", ".png"))
            ]
            files.sort(key=os.path.getmtime, reverse=True)
        except OSError as e:
            print(f"Could not list recent outputs: {e}")
            files = []
        recent = files[:6]
        init = self.root.ids.init_screen
        grid = init.ids.recent_grid
        scroll = init.ids.recent_scroll
        empty = init.ids.recent_empty
        grid.clear_widgets()
        tile_width = dp(206) if self.is_wide else dp(150)
        for path in recent:
            tile = RecentTile(image_source=path)
            tile.size_hint = (None, None)
            tile.width = tile_width
            tile.height = dp(104)
            grid.add_widget(tile)
        has_tiles = bool(recent)
        scroll.size_hint_y = None
        scroll.height = dp(104) if has_tiles else 0
        scroll.opacity = 1 if has_tiles else 0
        scroll.disabled = not has_tiles
        empty.size_hint_y = None
        empty.height = dp(112) if not has_tiles else 0
        empty.opacity = 1 if not has_tiles else 0
        empty.disabled = has_tiles

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
        self.face_tip_visible = not self.user_preferences["fm_dont_again"]
        self.vault_tip_visible = not self.user_preferences["sec_dont_again"]
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
        Clock.schedule_once(lambda dt: self.reset_result_panes())
        Clock.schedule_once(lambda dt: self._wire_navigation())
        Clock.schedule_once(lambda dt: self.refresh_recent_outputs())
        self.refresh_output_count()
        self._update_home_action()
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
        from kivymd.uix.card import MDCard
        from kivymd.uix.label import MDIcon
        from kivy.animation import Animation

        previous = getattr(self, "_toast", None)
        if previous is not None and previous.parent:
            previous.parent.remove_widget(previous)
        toast = MDCard(
            orientation="horizontal",
            size_hint=(None, None),
            width=min(Window.width - dp(32), dp(430)),
            height=dp(46),
            padding=(dp(14), 0),
            spacing=dp(10),
            radius=[dp(14)],
            elevation=3,
            md_bg_color=get_color_from_hex(tokens.ERROR if is_error else "#1F2937"),
        )
        toast.add_widget(
            MDIcon(
                icon="alert-circle-outline" if is_error else "check-circle-outline",
                theme_text_color="Custom",
                text_color="#FFFFFF",
                font_size=sp(17),
                size_hint=(None, None),
                size=(dp(20), dp(20)),
                pos_hint={"center_y": 0.5},
            )
        )
        toast.add_widget(
            MDLabel(
                text=message,
                font_size=sp(11),
                theme_text_color="Custom",
                text_color="#FFFFFF",
                text_size=(toast.width - dp(70), None),
                valign="middle",
                pos_hint={"center_y": 0.5},
            )
        )
        Window.add_widget(toast)
        toast.pos = (Window.width / 2 - toast.width / 2, dp(24))
        toast.opacity = 0
        Animation(opacity=1, d=0.15).start(toast)
        self._toast = toast

        def dismiss():
            anim = Animation(opacity=0, d=0.2)
            anim.bind(on_complete=lambda *a: Window.remove_widget(toast) if toast.parent else None)
            anim.start(toast)

        Clock.schedule_once(lambda dt: dismiss(), duration)

    def show_text_dialog(self, title, text="", buttons=[]):
        self.txt_dialog = MDDialog(
            title=title,
            text=text,
            buttons=buttons,
            # KivyMD's dialog shadow requires four corner radii
            radius=[dp(18), dp(18), dp(18), dp(18)],
        )
        self.txt_dialog.open()

    def txt_dialog_closer(self, instance=None):
        if self.txt_dialog:
            self.txt_dialog.dismiss()

    def unzip_model(self, filepath):
        import tarfile
        try:
            with tarfile.open(filepath, "r:gz") as tar:
                tar.extractall(path=self.model_dir)
            os.remove(filepath)
            self.models_ready = True
            self.models_ok = True
            self.download_progress_value = 100
            self.download_status_text = "Models ready"
            self.download_active = False
            if platform == "android":
                Clock.schedule_once(lambda dt: self.release_wakelock())
            self.show_toast_msg("Models are ready. Starting the face engine...")
            Clock.schedule_once(lambda dt: self.start_face_services())
        except Exception as e:
            print(f"Unzip error: {e}")
            self.fail_model_download("Could not unpack the model archive. Please try again.")

    def update_download_progress(self, percentage, downloaded, total_size):
        self.download_progress_value = percentage
        if total_size:
            self.download_status_text = (
                f"{downloaded / (1024 * 1024):.0f} MB of "
                f"{total_size / (1024 * 1024):.0f} MB"
            )
        else:
            self.download_status_text = f"{downloaded / (1024 * 1024):.1f} MB downloaded"

    def fail_model_download(self, message):
        self.download_active = False
        self.is_downloading = False
        self.download_status_text = ""
        self.show_toast_msg(message, is_error=True, duration=4)

    def download_file(self, download_url, download_path):
        self.is_downloading = download_url.split("/")[-1]
        last_percentage = -1.0
        try:
            with requests.get(download_url, stream=True, timeout=30) as req:
                req.raise_for_status()
                total_size = int(req.headers.get("content-length", 0))
                downloaded = 0
                with open(download_path, "wb") as f:
                    for chunk in req.iter_content(chunk_size=16384):
                        if not chunk:
                            continue
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            percentage = downloaded * 100.0 / total_size
                            if percentage - last_percentage >= 0.5:
                                last_percentage = percentage
                                Clock.schedule_once(
                                    lambda dt, p=percentage, d=downloaded, t=total_size: (
                                        self.update_download_progress(p, d, t)
                                    )
                                )
            if os.path.exists(download_path):
                Clock.schedule_once(lambda dt: self.unzip_model(download_path))
            else:
                Clock.schedule_once(
                    lambda dt: self.fail_model_download(
                        "The download did not complete. Please try again."
                    )
                )
        except Exception as e:
            print(f"Error downloading the ONNX models: {e}")
            Clock.schedule_once(
                lambda dt, m=str(e): self.fail_model_download(f"Download failed: {m}")
            )
        finally:
            self.is_downloading = False

    def start_model_download(self, instance=None):
        if self.download_active:
            self.show_toast_msg("The download is already running", is_error=True)
            return
        if self.models_ready:
            self.show_toast_msg("The models are already downloaded")
            return
        if platform == "android":
            Clock.schedule_once(lambda dt: self.acquire_wakelock())
        self.download_active = True
        self.download_progress_value = 0
        self.download_status_text = "Connecting..."
        print("Starting the model download")
        download_path = os.path.join(self.model_dir, "faceai.tar.gz")
        Thread(target=self.download_file, args=(MODEL_URL, download_path), daemon=True).start()

    def model_existance_check(self):
        self.models_ready = os.path.exists(self.detect_model_path) and os.path.exists(self.recog_model_path)
        self.models_ok = self.models_ready
        if not self.models_ready:
            print("Model files are missing. Use the Download button on the home screen.")

    def start_face_services(self, instance=None):
        self.txt_dialog_closer()
        if self.face_ai:
            self.services_running = True
            self.models_ready = True
            self.show_toast_msg("The face engine is already running")
            return
        self.models_ready = os.path.exists(self.detect_model_path) and os.path.exists(self.recog_model_path)
        if not self.models_ready:
            self.show_toast_msg("Download the model files first", is_error=True)
            return
        try:
            self.face_ai = FaceAiSvc(self.detect_model_path, self.recog_model_path, self.op_dir)
            self.face_ai.start_detection_session()
            self.face_ai.start_recognition_session()
            self.services_running = True
            self.show_toast_msg("Face engine started")
        except Exception as e:
            print(f"Could not start the sessions: {e}")
            self.face_ai = None
            self.services_running = False
            self.show_toast_msg(
                "Could not start the face engine. The model files may be damaged.",
                is_error=True,
            )

    def goto_face_matcher(self, instance=None):
        self.root.ids.screen_manager.current = "faceFindScr"

    def dismiss_face_tip(self, instance=None):
        self.face_tip_visible = False
        self.user_preferences["fm_dont_again"] = True
        Clock.schedule_once(lambda dt: self.save_config_file(self.user_preferences, self.usr_pref_path))

    def dismiss_vault_tip(self, instance=None):
        self.vault_tip_visible = False
        self.user_preferences["sec_dont_again"] = True
        Clock.schedule_once(lambda dt: self.save_config_file(self.user_preferences, self.usr_pref_path))

    def on_face_matcher_entry(self, instance=None):
        self.face_tip_visible = not self.user_preferences["fm_dont_again"]
        if self.is_onnx_running:
            return
        # keep finished results when the user navigates away and back
        if not self._result_box("src").children:
            self._refresh_result_placeholders()

    # -- face finder helpers -----------------------------------------
    def _result_box(self, which: str):
        pane = self.root.ids.face_match_scr.ids[f"fm_gen_{which}_pane"]
        return pane.ids.content

    def _set_pane_message(self, which, icon, text, detail=""):
        box = self._result_box(which)
        box.clear_widgets()
        box.add_widget(EmptyState(icon=icon, text=text, detail=detail))

    def _show_matching_state(self):
        for which in ("src", "trgt"):
            box = self._result_box(which)
            box.clear_widgets()
            box.add_widget(
                BusyState(
                    text="Matching faces...",
                    detail="Running on your device",
                )
            )

    def _refresh_result_placeholders(self):
        if self.is_onnx_running:
            return
        if self.src_image_path and self.trgt_image_path:
            icon, text, detail = (
                "check-circle-outline",
                "Ready to match",
                "Tap Find matches to compare the two photos.",
            )
        elif self.src_image_path or self.trgt_image_path:
            icon, text, detail = (
                "image-plus",
                "One more image",
                "Add a source face and a target photo.",
            )
        else:
            icon, text, detail = (
                "image-filter-center-focus",
                "Results appear here",
                "Pick a source face and a target photo first.",
            )
        for which in ("src", "trgt"):
            self._set_pane_message(which, icon, text, detail)

    def reset_result_panes(self):
        self._refresh_result_placeholders()

    def update_ready_to_match(self):
        self.ready_to_match = bool(self.src_image_path and self.trgt_image_path)
        self._refresh_result_placeholders()

    @staticmethod
    def _clean_markup(message: str) -> str:
        return re.sub(r"\[/?[a-zA-Z0-9_=#]+\]", "", message or "").strip()

    def open_img_file_manager(self, instance=None):
        permissions_ok = self.check_request_android_permission()
        if not permissions_ok:
            return
        if instance in ("btn_fm_src_upload", "src"):
            self.img_purpose = "src"
        elif instance in ("btn_fm_tgt_upload", "trgt"):
            self.img_purpose = "trgt"
        try:
            if not self.last_upload_path:
                self.last_upload_path = self.external_storage
            filechooser.open_file(
                on_selection=self.handle_img_selection,
                path=self.last_upload_path,
                multiple=False,
                filters=[["*.JPG", "*.jpg", "*.png", "*.jpeg", "*.webp"], "*"],
                preview=True,
            )
            self.is_inp_file_mgr_open = True
        except Exception as e:
            print(f"File chooser error: {e}")
            self.show_toast_msg("Could not open the file picker on this device.", is_error=True)

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
        if not path.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            self.show_toast_msg("That file is not a supported image.", is_error=True)
            return
        try:
            from kivy.core.image import Image as CoreImage
            opened = CoreImage(path)
            if opened.texture is None:
                raise ValueError("no texture")
        except Exception as e:
            print(f"Could not open selected image: {e}")
            self.show_toast_msg("That image could not be opened. Pick another one.", is_error=True)
            return
        fm = self.root.ids.face_match_scr.ids
        if self.img_purpose == "src":
            tile = fm.fm_src_tile
            self.src_image_path = path
        elif self.img_purpose == "trgt":
            tile = fm.fm_trgt_tile
            self.trgt_image_path = path
        else:
            self.show_toast_msg("Choose the source or the target image first.")
            return
        tile.image_source = path
        tile.file_name = os.path.basename(path)
        self.update_ready_to_match()

    def submit_face_match(self, instance=None):
        """
        Performs the face match job in a separate thread with callback option.
        """
        if not self.face_ai:
            self.show_text_dialog(
                title="Face engine is off",
                text="Start the face engine to run a comparison?",
                buttons=[
                    MDFlatButton(
                        text="Not now",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=self.txt_dialog_closer,
                    ),
                    MDFlatButton(
                        text="START",
                        theme_text_color="Custom",
                        text_color=tokens.SUCCESS,
                        on_release=self.start_face_services,
                    ),
                ],
            )
            return
        if self.is_onnx_running:
            self.show_toast_msg("A match is already running.")
            return
        if not self.src_image_path or not self.trgt_image_path:
            self.show_toast_msg("Choose both a source and a target image.", is_error=True)
            return
        self.is_onnx_running = True
        self._show_matching_state()
        Thread(
            target=self._run_face_match,
            args=(self.src_image_path, self.trgt_image_path),
            daemon=True,
        ).start()

    def _run_face_match(self, img1_path, img2_path):
        """Run the comparison, guaranteeing the UI leaves its busy state."""
        try:
            self.face_ai.face_match_group(
                img1_path=img1_path,
                img2_path=img2_path,
                callback=self.face_match_callback,
            )
        except Exception as e:
            print(f"Face match failed: {e}")
            Clock.schedule_once(
                lambda dt: self.face_match_callback(
                    {
                        "stat": False,
                        "msg": "Something went wrong while matching. Please try again.",
                        "src": "",
                        "trgt": "",
                    }
                )
            )

    def face_match_callback(self, resp):
        self.is_onnx_running = False
        if not resp or not resp.get("stat"):
            message = self._clean_markup((resp or {}).get("msg", ""))
            if not message:
                message = "No faces could be compared. Try clearer photos."
            for which in ("src", "trgt"):
                self._set_pane_message(which, "alert-circle-outline", "No match", message)
            self.show_toast_msg(message, is_error=True, duration=4)
            return
        for which, source in (("src", resp["src"]), ("trgt", resp["trgt"])):
            image = ImageWithAction(source=source, fit_mode="contain")
            image.img_type = which
            image.bind(on_release=self.download_image_from_view)
            box = self._result_box(which)
            box.clear_widgets()
            box.add_widget(image)
        self.refresh_output_count()
        self.refresh_recent_outputs()
        self.show_toast_msg("Match complete. Tap a result to save or delete it.")

    def download_image_from_view(self, instance=None):
        if instance:
            self.download_file_path = instance.source
            self.delete_file_path = instance.source
            self.last_instance = instance
            self.show_text_dialog(
                title="Save or delete this result?",
                text="Choose a folder to save the image, or remove it from this device.",
                buttons=[
                    MDFlatButton(
                        text="Cancel",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=self.txt_dialog_closer
                    ),
                    MDFlatButton(
                        text="DELETE",
                        theme_text_color="Custom",
                        text_color=tokens.ERROR,
                        on_release=self.delete_selected_file
                    ),
                    MDFlatButton(
                        text="Save",
                        theme_text_color="Custom",
                        text_color=tokens.SUCCESS,
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
            print(f"File successfully saved to: {chosen_path}")
            self.show_toast_msg(f"Saved to {chosen_path}")
        except Exception as e:
            print(f"Error saving file: {e}")
            self.show_toast_msg(f"Could not save the file: {e}", is_error=True)

    def op_file_exit_manager(self, *args):
        """Called when the user reaches the root of the directory tree."""
        self.is_op_file_mgr_open = False
        self.op_file_manager.close()

    def delete_file_popup(self, instance=None):
        filename = os.path.basename(self.delete_file_path)
        self.show_text_dialog(
            title="Download successful",
            text=f"{filename} was saved. Remove the copy stored by Face AI?",
            buttons=[
                MDFlatButton(
                    text="Keep",
                    theme_text_color="Custom",
                    text_color=self.theme_cls.primary_color,
                    on_release=self.txt_dialog_closer
                ),
                MDFlatButton(
                    text="DELETE",
                    theme_text_color="Custom",
                    text_color=tokens.ERROR,
                    on_release=self.delete_selected_file
                ),
            ],
        )

    def delete_selected_file(self, instance=None):
        self.txt_dialog_closer()
        if self.delete_file_path:
            try:
                os.remove(self.delete_file_path)
                self.show_toast_msg("File deleted.")
                print(f"Deleted: {self.delete_file_path}")
                self.delete_file_path = None
                if self.last_instance and self.last_instance.parent:
                    Clock.schedule_once(lambda dt: self.last_instance.parent.remove_widget(self.last_instance))
                self.refresh_output_count()
                self.refresh_recent_outputs()
                if self.sec_file_box:
                    self.refresh_sec_file_list()
            except Exception as e:
                print(f"Error while deleting {self.delete_file_path} because: {e}")
                self.show_toast_msg("Could not delete the file.", is_error=True)

    def reset_face_matcher(self, instance=None):
        self.src_image_path = None
        self.trgt_image_path = None
        self.img_purpose = ""
        fm = self.root.ids.face_match_scr.ids
        for tile_id in ("fm_src_tile", "fm_trgt_tile"):
            tile = fm[tile_id]
            tile.image_source = ""
            tile.file_name = ""
        self.update_ready_to_match()

    # Security section starts here
    def on_security_enter(self):
        permissions_ok = self.check_request_total_permission()
        if not permissions_ok:
            return
        if not self.face_ai or not self.services_running:
            self.show_toast_msg("Start the face engine first.", is_error=True, duration=2)
            self.root.ids.screen_manager.current = "initScreen"
            return
        self.verifying = False
        self.on_security_leave()  # clear existing things
        self.sec_uix = self.root.ids.security_box.ids.sec_elements_box
        self.db_conn_ok = self.face_ai.start_db_session(self.db_path)
        if not self.db_conn_ok:
            self.sec_uix.add_widget(
                LoadingCard(
                    text="Vault is unavailable",
                    detail="The local database could not be opened.",
                )
            )
            return
        self.sec_uix.add_widget(
            LoadingCard(
                text="Checking your vault",
                detail="Looking for enrolled faces...",
            )
        )
        self.sec_uix.add_widget(Widget())
        Clock.schedule_once(
            lambda dt: self.face_ai.check_if_data_exist(self._init_security_callback)
        )

    def android_front_cam(self):
        from services.androidSvc import AndroidSvc
        cam_svc = AndroidSvc()
        cam_map = cam_svc.get_camera_details()
        cam_id = cam_map.get("front", None)
        return cam_id

    def _camera_index(self):
        cam_indx = -1
        if platform == "android":
            if self.used_cam_id is not None:
                cam_indx = int(self.used_cam_id)
            else:
                self.used_cam_id = self.android_front_cam()
                cam_indx = int(self.used_cam_id) if self.used_cam_id is not None else 0
        else:
            if self.used_cam_id is not None:
                cam_indx = int(self.used_cam_id)
            else:
                import cv2
                for i in range(2):
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        print(f"Camera found at index: {i}")
                        self.used_cam_id = cam_indx = i
                        cap.release()
                        break
                    cap.release()
        return cam_indx

    def _make_camera_card(self):
        cam_indx = self._camera_index()
        resolution = (960, 720) if platform == "android" else (640, 480)
        if platform == "android":
            import datetime
            now = datetime.datetime.now()
            self.tmp_login_filename = os.path.join(
                self.sec_file_dir,
                f"login_{now.strftime('%Y%m%d')}_{now.strftime('%H%M%S')}.jpg",
            )
        card = CameraCard()
        self.camera_card = card
        if cam_indx < 0:
            card.show_error("No camera was found on this device.")
            self.show_toast_msg("No camera found on this device.", is_error=True)
            return card
        try:
            if platform != "android" and self.camera:
                # AVFoundation may hand back a sideways texture on macOS; a
                # fresh widget keeps the rotation transform from stacking.
                try:
                    self.camera.play = False
                except Exception:
                    pass
                if self.camera.parent:
                    self.camera.parent.remove_widget(self.camera)
                self.camera = None
            if not self.camera:
                self.camera = Camera(
                    index=cam_indx,
                    resolution=resolution,
                    fit_mode="contain",
                    play=True,
                )
            else:
                self.camera.play = True
            if self.camera.parent:
                self.camera.parent.remove_widget(self.camera)
            holder = card.ids.cam_holder
            if platform == "android":
                self.camera.size_hint = (1, 1)
            else:
                self.camera.size_hint = (None, None)
                self.camera.fit_mode = "fill"
                with self.camera.canvas.before:
                    PushMatrix()
                    self._camera_rotate = Rotate(angle=-90, origin=self.camera.center)
                with self.camera.canvas.after:
                    PopMatrix()
                holder.bind(size=lambda *a: self._fit_rotated_camera(holder))
                Clock.schedule_once(lambda dt: self._fit_rotated_camera(holder))
            holder.add_widget(self.camera)
            card.status = "LIVE" if self.camera.texture else "Starting..."
            self.camera.bind(texture=lambda *a: self._refresh_camera_status(card))
            Clock.schedule_once(lambda dt: self._refresh_camera_status(card), 1.2)
        except Exception as e:
            print(f"Error setting up the camera: {e}")
            card.show_error("The camera could not be started.\nCheck the camera permission.")
            self.show_toast_msg("The camera could not be started.", is_error=True)
        return card

    def _fit_rotated_camera(self, holder):
        if platform == "android" or not self.camera:
            return
        margin = dp(10)
        inner_w = max(dp(40), holder.width - 2 * margin)
        inner_h = max(dp(40), holder.height - 2 * margin)
        # Draw the texture in a box that is landscape-inverse, then rotate it
        # 90 degrees so the corrected frame fills the portrait/landscape tile.
        self.camera.size = (inner_h, inner_w)
        self.camera.center = holder.center
        rotate = getattr(self, "_camera_rotate", None)
        if rotate is not None:
            rotate.origin = self.camera.center

    def _refresh_camera_status(self, card=None):
        card = card or self.camera_card
        if not card or not self.camera:
            return
        texture = self.camera.texture
        if texture:
            width, height = texture.size
            if width and height:
                if platform == "android":
                    card.preview_ratio = max(0.55, min(2.2, width / height))
                else:
                    # raw frames arrive rotated 90 degrees on macOS
                    card.preview_ratio = max(0.55, min(2.2, height / width))
            card.status = "LIVE"
        else:
            card.status = "No signal"

    def reset_tips(self, instance=None):
        self.user_preferences["fm_dont_again"] = False
        self.user_preferences["sec_dont_again"] = False
        self.face_tip_visible = True
        self.vault_tip_visible = True
        self.save_config_file(self.user_preferences, self.usr_pref_path)
        self.show_toast_msg("Help tips will be shown again.")

    def lock_vault(self, instance=None):
        self.login_success = False
        self.sec_file_box = None
        self.vault_tip_visible = not self.user_preferences["sec_dont_again"]
        self.on_security_enter()

    def _auth_view(self, mode="auto"):
        """Camera and form side by side on desktop, stacked on mobile."""
        self.on_security_leave()
        self.sec_uix = self.root.ids.security_box.ids.sec_elements_box
        enroll = mode == "enroll" or not self.data_in_db
        form = RegisterCard() if enroll else LoginCard()
        self.sec_name_input = form.ids.sec_name_inp_txt if enroll else None
        camera_card = self._make_camera_card()
        if self.is_wide:
            row = MDBoxLayout(
                orientation="horizontal",
                spacing=dp(12),
                size_hint_y=None,
                height=dp(392),
            )
            camera_card.size_hint = (None, 1)
            camera_card.width = dp(430)
            right = MDBoxLayout(orientation="vertical", spacing=dp(10))
            right.add_widget(form)
            right.add_widget(SecurityTipsCard())
            right.add_widget(Widget())
            row.add_widget(camera_card)
            row.add_widget(right)
            self.sec_uix.add_widget(row)
            self.sec_uix.add_widget(Widget())
        else:
            self.sec_uix.add_widget(camera_card)
            self.sec_uix.add_widget(form)
            self.sec_uix.add_widget(Widget())

    def _init_security_callback(self, resp):  # should not be called directly
        if self.login_success:
            self.sec_login_ok()
            return
        self.data_in_db = bool(resp)
        self._auth_view("auto")

    def add_new_face(self, instance=None):
        self._auth_view("enroll")

    def get_sec_file_list(self, path: str):
        files = []
        try:
            for filename in os.listdir(path):
                files.append(filename)
        except OSError as e:
            print(f"Could not read the vault directory: {e}")
        return files

    def _toggle_vault_empty(self, is_empty: bool):
        if not self.sec_file_box:
            return
        ids = self.sec_file_box.ids
        scroll = ids.sec_file_scroll
        empty = ids.sec_empty
        if is_empty:
            scroll.size_hint_y = None
            scroll.height = 0
            scroll.opacity = 0
            scroll.disabled = True
            empty.size_hint_y = 1
            empty.opacity = 1
            empty.disabled = False
        else:
            scroll.size_hint_y = 1
            scroll.opacity = 1
            scroll.disabled = False
            empty.size_hint_y = None
            empty.height = 0
            empty.opacity = 0
            empty.disabled = True

    def refresh_sec_file_list(self, instance=None):
        if not self.sec_file_box:
            return
        secMdList = self.sec_file_box.ids.sec_file_list
        secMdList.clear_widgets()
        sec_files = self.get_sec_file_list(self.sec_file_dir)
        for file in sec_files:
            fileElem = SecSingleFile()
            fileElem.filename = str(file)
            try:
                full_path = os.path.join(self.sec_file_dir, file)
                size = os.path.getsize(full_path)
                stamp = os.path.getmtime(full_path)
                size_txt = (
                    f"{size / 1024:.0f} KB"
                    if size < 1024 * 1024
                    else f"{size / (1024 * 1024):.1f} MB"
                )
                date_txt = datetime.datetime.fromtimestamp(stamp).strftime("%d %b %Y")
                fileElem.detail = f"Encrypted - {size_txt} - {date_txt}"
            except OSError:
                fileElem.detail = "Encrypted - tap to download"
            secMdList.add_widget(fileElem)
        self._toggle_vault_empty(len(sec_files) == 0)

    def sec_login_ok(self, msg: str = "Login"):
        self.on_security_leave()
        self.sec_uix = self.root.ids.security_box.ids.sec_elements_box
        self.sec_file_box = SecAfterLogin()
        self.sec_uix.add_widget(self.sec_file_box)
        self.refresh_sec_file_list()
        self.login_success = True
        self.vault_tip_visible = not self.user_preferences["sec_dont_again"]
        print(f"{msg} is successful!")

    def sec_face_login_save(self, name: str, img, newFace=False):
        if not self.face_ai:
            self.show_toast_msg("Start the face engine first.", is_error=True)
            return
        if not self.data_in_db or newFace:
            if len(name) < 3:
                self.show_toast_msg(
                    "Please enter a name with at least 3 characters.", is_error=True
                )
                return
            matched_name = None
            if self.data_in_db:
                matched_name = self.face_ai.face_verify(img)
            if matched_name is None:
                stat = self.face_ai.save_faces_masterdb(name, img)
                if stat:
                    self.data_in_db = True
                    self.login_success = False
                    self.face_reg_error = False
                    self.on_security_enter()
                    Clock.schedule_once(
                        lambda dt: self.show_toast_msg(
                            f"{name} is enrolled. Look at the camera to unlock."
                        )
                    )
                else:
                    self.show_toast_msg(
                        "No single face was found. Look straight at the camera and retry.",
                        is_error=True,
                    )
                    self.face_reg_error = True
            else:
                message = f"This face is already enrolled as {matched_name}."
                self.login_success = False
                self.on_security_enter()
                Clock.schedule_once(lambda dt: self.show_toast_msg(message))
        else:
            matched_name = self.face_ai.face_verify(img)
            if matched_name is None:
                self.show_toast_msg(
                    "Face not recognised. Try again with better light.", is_error=True
                )
            else:
                self.sec_login_ok()
                Clock.schedule_once(
                    lambda dt: self.show_toast_msg(f"Welcome back, {matched_name}.")
                )

    def sec_capture_frame(self, instance=None, newFace=False):
        if self.verifying:
            return
        if not self.camera or not self.camera.texture:
            self.show_toast_msg(
                "The camera is not ready yet. Wait a moment and retry.", is_error=True
            )
            return
        name_txt = ""
        if instance:
            name_txt = str(instance.text).strip()
        self.verifying = True
        try:
            import cv2
            import numpy as np
            texture = self.camera.texture
            pixels = texture.pixels
            width, height = texture.size
            arr = np.frombuffer(pixels, dtype=np.uint8).reshape((height, width, 4))
            img = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            if platform == "android":
                img = np.flipud(img)  # Flip up down in android
            else:
                # AVFoundation frames arrive rotated 90 degrees
                img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
            self.sec_face_login_save(name_txt, img, newFace)
        except Exception as e:
            print(f"Error processing frame: {e}")
            self.show_toast_msg("Could not read a frame from the camera.", is_error=True)
        finally:
            self.verifying = False

    def vault_file_saver(self, file_path: str):
        filename = os.path.basename(file_path)
        target_file = os.path.join(self.sec_file_dir, filename)
        if os.path.exists(target_file):
            self.show_toast_msg(
                "A file with this name already exists in the vault.", is_error=True
            )
            return
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
            self.show_toast_msg(f"{filename} is now encrypted in your vault.")
        except Exception as e:
            print(f"Error saving file: {e}")
            self.show_toast_msg("Could not encrypt that file.", is_error=True)

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
                on_selection=self.save_in_vault,
                path=self.last_upload_path,
                multiple=False,
            )
            self.is_inp_file_mgr_open = True
        except Exception as e:
            print(f"Vault file chooser error: {e}")
            self.show_toast_msg("Could not open the file picker on this device.", is_error=True)

    def download_sec_file(self, instance):
        filename = str(instance.filename)
        full_path = os.path.join(self.sec_file_dir, filename)
        if not os.path.exists(full_path):
            self.show_toast_msg("That file is no longer in the vault.", is_error=True)
            self.refresh_sec_file_list()
            return
        self.download_file_path = str(full_path)
        self.download_from_app_local()

    def popup_sec_file_delete(self, instance):
        filename = str(instance.filename)
        self.last_instance = instance
        self.delete_file_path = os.path.join(self.sec_file_dir, filename)
        self.show_text_dialog(
            title="Delete this file?",
            text=f"{filename} will be removed from the vault. This cannot be undone.",
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    theme_text_color="Custom",
                    text_color=self.theme_cls.primary_color,
                    on_release=self.txt_dialog_closer,
                ),
                MDFlatButton(
                    text="DELETE",
                    theme_text_color="Custom",
                    text_color=tokens.ERROR,
                    on_release=self.delete_selected_file,
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
        self.verifying = False

    # Settings section start here
    def refresh_output_count(self, instance=None):
        count = 0
        try:
            for filename in os.listdir(self.op_dir):
                if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                    count += 1
        except OSError as e:
            print(f"Could not count output files: {e}")
        self.output_count = count
        if count == 0:
            self.output_count_label = "No generated images yet"
        elif count == 1:
            self.output_count_label = "1 generated image in the output folder"
        else:
            self.output_count_label = f"{count} generated images in the output folder"

    def show_all_delete_alert(self):
        self.refresh_output_count()
        if self.output_count == 0:
            self.show_toast_msg("There are no generated images to delete.")
            return
        noun = "image" if self.output_count == 1 else "images"
        self.show_text_dialog(
            title="Delete generated images?",
            text=f"Remove all {self.output_count} generated {noun} from the output folder? This cannot be undone.",
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    theme_text_color="Custom",
                    text_color=self.theme_cls.primary_color,
                    on_release=self.txt_dialog_closer,
                ),
                MDFlatButton(
                    text="DELETE",
                    theme_text_color="Custom",
                    text_color=tokens.ERROR,
                    on_release=self.delete_all_op_action,
                ),
            ],
        )

    def delete_all_op_action(self, instance):
        removed = 0
        for filename in os.listdir(self.op_dir):
            if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                file_path = os.path.join(self.op_dir, filename)
                try:
                    os.unlink(file_path)
                    removed += 1
                except Exception as e:
                    print(f"Could not delete {file_path}: {e}")
        self.txt_dialog_closer(instance)
        self.refresh_output_count()
        self.refresh_recent_outputs()
        if not self.is_onnx_running:
            self.reset_result_panes()
        noun = "image" if removed == 1 else "images"
        self.show_toast_msg(f"Removed {removed} generated {noun}.")

    def open_data_folder(self, instance=None):
        path = self.internal_storage
        try:
            if platform == "win":
                os.startfile(path)
            elif platform == "macosx":
                subprocess.Popen(["open", path])
            elif platform == "linux":
                subprocess.Popen(["xdg-open", path])
            else:
                self.show_toast_msg("Opening folders is not supported on this device.")
        except Exception as e:
            print(f"Could not open the data folder: {e}")
            self.show_toast_msg("Could not open the data folder.", is_error=True)

    def show_help_dialog(self, instance=None):
        self.txt_dialog_closer()
        self.show_text_dialog(
            "Face AI",
            "Offline face detection, matching and an encrypted vault.\n\n"
            "Home: download the model files once, then start the engine.\n"
            "Face Finder: one clear face as the source, any photo as the target.\n"
            "Secure Vault: enroll a face to lock and unlock your files.\n\n"
            "Shortcuts: Ctrl/Cmd+1..4 switch sections, Ctrl/Cmd+O picks a photo,\n"
            "Ctrl/Cmd+R resets Face Finder, Ctrl/Cmd+L locks the vault, Esc closes the menu.\n\n"
            "Everything is processed on this device.",
            buttons=[
                MDFlatButton(
                    text="Got it",
                    theme_text_color="Custom",
                    text_color=self.theme_cls.primary_color,
                    on_release=self.txt_dialog_closer,
                )
            ],
        )

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
                text_color=tokens.PRIMARY,
                on_release=self.update_link_open
            ),
        ]
        self.show_text_dialog(
            "Updates",
            f"Face AI v{__version__}\nCheck the releases page to see if a newer build is available.",
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