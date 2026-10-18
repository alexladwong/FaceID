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
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.navigationdrawer import MDNavigationDrawerItem
#from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import (
    MDFillRoundFlatIconButton,
    MDFlatButton,
    MDFloatingActionButton,
    MDIconButton,
    MDTextButton,
)
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivy.uix.scrollview import ScrollView

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
from services.access import AccessSvc, DoorController
from services.faceAi import FaceAiSvc
from screens.palette import theme
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
from screens.access import AccessEventRow
from screens.people import AuditEventRow, PeopleBox, PeopleRow
from screens.setting import SettingsBox
from screens.ui import AppCard, BusyState, EmptyState, IconBadge, NoticeCard, RecentTile, StatusPill

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
    match_step_text = StringProperty("1/4  -  Source face")
    match_step_index = NumericProperty(1)
    match_has_results = BooleanProperty(False)
    verifying = BooleanProperty(False)
    face_tip_visible = BooleanProperty(True)
    vault_tip_visible = BooleanProperty(True)
    ready_to_match = BooleanProperty(False)
    is_desktop = BooleanProperty(False)
    is_wide = BooleanProperty(False)
    nav_offset = NumericProperty(dp(248))
    nav_collapsed = BooleanProperty(False)
    current_screen = StringProperty("initScreen")
    current_page_title = StringProperty("Home")
    home_action_label = StringProperty("Start face engine")
    home_action_icon = StringProperty("play")
    app_version = StringProperty(__version__)
    output_count = NumericProperty(0)
    output_count_label = StringProperty("No generated images yet")
    logo_path = StringProperty("")
    access_mode = StringProperty("scan")
    access_state = StringProperty("idle")
    access_title = StringProperty("Ready to scan")
    access_message = StringProperty("Look at the camera and press Scan & unlock.")
    access_detail1 = StringProperty("")
    access_detail2 = StringProperty("")
    access_busy = BooleanProperty(False)
    access_controller_label = StringProperty("Simulated relay")
    access_controller_detail = StringProperty("No physical door is connected.")
    access_controller_state = StringProperty("simulated")
    access_controller_bg = StringProperty(theme.primary_soft)
    access_controller_fg = StringProperty(theme.primary_text)
    access_fail_mode = StringProperty("fail_secure")
    access_policy_label = StringProperty("Single factor")
    access_two_factor = BooleanProperty(False)
    access_face_available = BooleanProperty(False)
    access_face_warning = StringProperty("")
    access_card_status = StringProperty("No card reader connected")
    access_card_available = BooleanProperty(False)
    people_search = StringProperty("")
    people_filter = StringProperty("all")
    people_admin_missing = BooleanProperty(True)
    people_count_text = StringProperty("No people registered")
    theme_dark = BooleanProperty(False)
    theme_label = StringProperty("Light")
    reduce_motion = BooleanProperty(False)
    motion_label = StringProperty("Off")
    door_name = StringProperty("Main Gate")
    door_controller_label = StringProperty("Simulated relay (pilot)")
    vault_search = StringProperty("")
    vault_sort = StringProperty("date")
    vault_sort_label = StringProperty("Newest")
    vault_count_text = StringProperty("")
    vault_busy = BooleanProperty(False)

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
        self._camera_configured = False
        self._camera_status_bound = False
        self._camera_holder = None
        self._camera_stop_event = None
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
        self._match_token = 0
        self.user_preferences = {
            "fm_dont_again": False,
            "sec_dont_again": False,
            "dark": False,
            "reduce_motion": False
        }
        self.is_wide = Window.width >= 980
        self._drawer_open = False
        self._access_register_requested = False
        self.access_svc = None
        self.door = None
        Window.bind(on_resize=self._on_window_resize)
        if platform not in ("android", "ios") and hasattr(Window, "on_drop_file"):
            try:
                Window.bind(on_drop_file=self._on_file_drop_file)
            except Exception as e:
                print(f"Drag and drop is unavailable: {e}")
        self.bind(
            models_ready=self._update_home_action,
            services_running=self._update_home_action,
            download_active=self._update_home_action,
        )

    def _read_saved_theme(self):
        try:
            path = os.path.join(self.user_data_dir, "config", "preferences.json")
            with open(path) as f:
                return bool(json.load(f).get("dark", False))
        except Exception:
            return False

    def build(self):
        self.theme_dark = self._read_saved_theme()
        self.theme_label = "Dark" if self.theme_dark else "Light"
        theme.apply("dark" if self.theme_dark else "light")
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.accent_palette = "Teal"
        self.theme_cls.theme_style = "Dark" if self.theme_dark else "Light"
        self.title = "Face AI"
        try:
            self.icon = self.logo_path
        except Exception:
            pass
        if self.is_desktop:
            Window.size = self.initial_window_size
            Window.clearcolor = get_color_from_hex(theme.surface)
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
        Animation.cancel_all(panel)
        if scrim is not None:
            Animation.cancel_all(scrim)
        if self.is_wide:
            panel.width = dp(80) if self.nav_collapsed else dp(248)
            self.nav_offset = panel.width
            panel.x = 0
            panel.disabled = False
            self._drawer_open = False
            if scrim is not None:
                scrim.opacity = 0
                scrim.disabled = True
        else:
            panel.width = dp(248)
            self.nav_offset = 0
            panel.disabled = False
            if not self._drawer_open:
                panel.x = -panel.width
                # The kv width binding settles after this resize event; pin
                # the closed position to the final width so the rail cannot
                # peek over the content on narrow windows.
                Clock.schedule_once(
                    lambda dt: setattr(panel, "x", -panel.width), 0
                )

    def toggle_reduce_motion(self, instance=None):
        self.reduce_motion = not self.reduce_motion
        self.motion_label = "On" if self.reduce_motion else "Off"
        self.user_preferences["reduce_motion"] = self.reduce_motion
        self.save_config_file(self.user_preferences, self.usr_pref_path)
        try:
            self.root.ids.screen_manager.transition.duration = (
                0 if self.reduce_motion else 0.14
            )
        except Exception:
            pass
        self.show_toast_msg(
            "Motion reduced." if self.reduce_motion else "Motion animations restored."
        )

    def toggle_nav_collapse(self, instance=None):
        if not self.is_wide:
            return
        self.nav_collapsed = not self.nav_collapsed
        self._apply_nav_mode()

    def open_drawer(self, instance=None):
        if self.is_wide or not self.root:
            return
        panel = self.root.ids.nav_panel
        scrim = self.root.ids.drawer_scrim
        self._drawer_open = True
        panel.x = -panel.width
        scrim.disabled = False
        if self.reduce_motion:
            panel.x = 0
            scrim.opacity = 1
        else:
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
        if self.is_wide:
            Animation.cancel_all(panel)
            panel.x = 0
            if scrim is not None:
                scrim.opacity = 0
                scrim.disabled = True
            return
        if self.reduce_motion:
            panel.x = -panel.width
            if scrim is not None:
                scrim.opacity = 0
                scrim.disabled = True
            if not was_open:
                panel.x = -panel.width
            return
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
        if key == 27:
            if self._drawer_open:
                self.close_drawer()
                return True
            dialog = getattr(self, "txt_dialog", None)
            if dialog is not None:
                try:
                    dialog.dismiss()
                except Exception:
                    pass
                return True
        meta = "meta" in modifiers or "ctrl" in modifiers
        if not meta:
            return False
        screen = self.root.ids.screen_manager.current if self.root else ""
        if codepoint in ("1", "2", "3", "4", "5", "6"):
            target = {
                "1": "initScreen",
                "2": "accessScr",
                "3": "peopleScr",
                "4": "faceFindScr",
                "5": "securityScr",
                "6": "settingsScr",
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
        try:
            self.root.ids.screen_manager.transition.duration = (
                0 if self.reduce_motion else 0.14
            )
        except Exception:
            pass
        self.root.ids.screen_manager.current = name
        self.current_screen = name
        self.current_page_title = {
            "initScreen": "Home",
            "accessScr": "Door Access",
            "peopleScr": "People",
            "faceFindScr": "Face Finder",
            "securityScr": "Secure Vault",
            "settingsScr": "Settings",
        }.get(name, "Home")
        self._set_nav_selection(name)
        if self._drawer_open:
            self.close_drawer()

    def _set_nav_selection(self, current):
        labels = {
            "Home": "initScreen",
            "Access": "accessScr",
            "People": "peopleScr",
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

    # -- door access kiosk -----------------------------------------
    def _sync_door_labels(self):
        door = None
        if self.access_svc is not None:
            door = self.access_svc.door
        elif self.door is not None:
            door = self.door
        if door is None:
            return
        self.door = door
        self.door_name = door.door_name
        self.door_controller_label = door.status_text()
        self._refresh_access_status()

    def _refresh_access_status(self):
        if self.access_svc is None:
            self.access_controller_label = "Access registry unavailable"
            self.access_controller_detail = "The local access database could not be opened."
            self.access_controller_state = "disconnected"
            self.access_face_available = False
            self.access_face_warning = "Face access is unavailable."
            self.access_card_status = "No card reader connected"
            self.access_card_available = False
            return
        controller = self.access_svc.controller_status()
        face = self.access_svc.face_state()
        reader = self.access_svc.card_reader_status()
        self.access_controller_state = controller.get("state", "disconnected")
        if self.access_controller_state == "connected":
            self.access_controller_bg = theme.success_soft
            self.access_controller_fg = theme.success
        elif self.access_controller_state == "simulated":
            self.access_controller_bg = theme.primary_soft
            self.access_controller_fg = theme.primary_text
        elif self.access_controller_state == "unverified":
            self.access_controller_bg = theme.warning_soft
            self.access_controller_fg = theme.warning
        else:
            self.access_controller_bg = theme.error_soft
            self.access_controller_fg = theme.error
        self.access_controller_label = controller.get("label", "Controller unavailable")
        self.access_controller_detail = controller.get("detail", "")
        self.door_controller_label = self.access_controller_label
        self.access_fail_mode = self.access_svc.door.fail_mode
        self.access_two_factor = self.access_svc.door.require_two_factor
        self.access_policy_label = "Face/card + PIN" if self.access_two_factor else "Single factor"
        self.access_face_available = bool(face.get("enabled") and self.access_svc.ready)
        self.access_card_available = bool(reader.get("available"))
        self.access_card_status = reader.get("label", "No card reader connected")
        warning = ""
        if not self.services_running:
            warning = "The face engine is off. PIN, card and administrator assistance remain available."
        elif not face.get("enabled"):
            warning = face.get("detail", "Face access is unavailable at this door.")
        self.access_face_warning = warning

    def _access_camera_card(self):
        box = self.root.ids.get("access_box") if self.root else None
        return box.ids.access_camera if box else None

    def on_access_enter(self, instance=None):
        self.access_busy = False
        self.reset_access_result()
        card = self._access_camera_card()
        if card is not None:
            if self.services_running:
                self._attach_camera_to_card(card)
            else:
                card.status = "Engine off"
        if self.root is not None:
            box = self.root.ids.get("access_box")
            if box is not None:
                Clock.schedule_once(
                    lambda dt: setattr(box.ids.access_scroll, "scroll_y", 1.0), 0.08
                )
        self._refresh_access_status()
        self.refresh_access_events()

    def on_access_leave(self, instance=None):
        self.stop_camera()
        self.access_busy = False

    def on_people_enter(self, instance=None):
        self.refresh_people()
        self.refresh_access_events()
        self._refresh_access_status()

    def retry_access_camera(self):
        if self.access_svc is None:
            return
        if not self.services_running:
            self.show_toast_msg("Start the face engine first.", is_error=True)
            return
        card = self._access_camera_card()
        if card is None:
            return
        self._attach_camera_to_card(card)
        self.show_toast_msg("Retrying the camera...")

    def open_access_register(self, instance=None):
        if self.access_svc is None:
            self.show_toast_msg("The access registry is unavailable.", is_error=True)
            return
        if not self.services_running or not self.access_svc.ready:
            self.show_toast_msg("Start the face engine before registering a face.", is_error=True)
            return
        if self.current_screen != "accessScr":
            self.show_toast_msg("Opening the enrollment camera...")
        self._with_access_camera(self._open_registration_flow)

    def open_admin_register(self, instance=None):
        if self.access_svc is None:
            self.show_toast_msg("The access registry is unavailable.", is_error=True)
            return
        if self.access_svc.admin_required():
            self.show_toast_msg("An administrator is already configured.", is_error=True)
            return
        if not self.services_running or not self.access_svc.ready:
            self.show_toast_msg("Start the face engine before registering an administrator.", is_error=True)
            return
        self._with_access_camera(
            lambda: self._show_registration_dialog(None, None, default_role="Admin")
        )

    def open_existing_admin_pin(self, instance=None):
        if self.access_svc is None:
            self.show_toast_msg("The access registry is unavailable.", is_error=True)
            return
        if self.access_svc.admin_required():
            self.show_toast_msg("An administrator PIN is already configured.", is_error=True)
            return
        ref = self._tf("Administrator ID")
        pin = self._tf("New administrator PIN (4-8 digits)", password=True, numeric=True)
        confirm = self._tf("Confirm PIN", password=True, numeric=True)

        def submit(dialog):
            if not ref.text.strip():
                self.show_toast_msg("Enter the existing administrator ID.", is_error=True)
                return
            if not re.fullmatch(r"\d{4,8}", pin.text or ""):
                self.show_toast_msg("PIN must be 4-8 digits.", is_error=True)
                return
            if pin.text != confirm.text:
                self.show_toast_msg("PINs do not match.", is_error=True)
                return
            person = self.access_svc.db.find_person(ref.text.strip())
            if not person:
                self.show_toast_msg("That person is not in the directory.", is_error=True)
                return
            result = self.access_svc.set_pin(person["id"], pin.text)
            if not result.get("ok"):
                self.show_toast_msg(result.get("message", "Could not set the administrator PIN."), is_error=True)
                return
            dialog.dismiss()
            self.refresh_people()
            self.show_toast_msg("Administrator PIN configured.")

        self._dialog_form("Set up an existing administrator", [ref, pin, confirm], "SET PIN", submit)

    def _with_access_camera(self, callback):
        if self.current_screen == "accessScr":
            card = self._access_camera_card()
            if card is not None and self.camera is None and self.services_running:
                self._attach_camera_to_card(card)
                Clock.schedule_once(lambda dt: callback(), 0.5)
            else:
                callback()
            return
        self.goto_screen("accessScr")
        Clock.schedule_once(lambda dt: self._finish_access_camera_flow(callback), 1.4)

    def _finish_access_camera_flow(self, callback):
        if self.current_screen != "accessScr":
            return
        card = self._access_camera_card()
        if card is not None and self.camera is None and self.services_running:
            self._attach_camera_to_card(card)
            # The camera texture and the modal both animate. Let the camera
            # settle before opening the form so its open animation is not lost.
            Clock.schedule_once(lambda dt: callback(), 0.5)
        else:
            callback()

    def _open_registration_flow(self):
        if self.access_svc.admin_required():
            self._require_admin(
                "Register person",
                "An administrator PIN is required to add a person once an administrator exists.",
                lambda actor_ref, actor_pin: self._show_registration_dialog(actor_ref, actor_pin),
            )
        else:
            self._show_registration_dialog(None, None)

    def reset_access_result(self):
        self.access_state = "idle"
        self.access_title = "Ready to scan"
        self.access_message = "Look at the camera or choose an alternative method."
        self.access_detail1 = ""
        self.access_detail2 = ""

    def scan_access(self, instance=None):
        if self.access_busy:
            return
        if self.access_svc is None:
            self.show_toast_msg("The access registry is unavailable.", is_error=True)
            return
        if not self.access_face_available:
            self.show_toast_msg(
                self.access_face_warning or "Face access is unavailable. Use Alternative.",
                is_error=True,
            )
            self.open_alternative_access()
            return
        frame = self._capture_bgr_frame()
        if frame is None:
            self.show_toast_msg(
                "The camera is not ready yet. Wait a moment and retry.", is_error=True
            )
            return
        self._run_access_check(lambda: self.access_svc.authenticate_face(frame))

    def _method_label(self, method):
        return {
            "face": "FACE",
            "pin": "PIN",
            "card": "CARD",
            "admin": "ADMIN",
            "face+pin": "FACE+PIN",
            "card+pin": "CARD+PIN",
            "second_factor": "2FA",
        }.get(str(method or "").lower(), str(method or "").upper() or "ACCESS")

    def _apply_access_result(self, result):
        if not result:
            result = {"decision": "error", "message": "No access result returned."}
        decision = result.get("decision", "error")
        self.access_state = (
            decision
            if decision in ("granted", "denied", "error", "unavailable")
            else ("challenge" if decision == "second_factor_required" else "error")
        )
        person = result.get("person_name") or ""
        role = result.get("role") or ""
        dept = result.get("department") or ""
        method = result.get("method") or ""
        method_label = self._method_label(method)
        door = result.get("door_name") or self.door_name
        ts = result.get("ts") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line1 = "  -  ".join([p for p in (person, role, dept) if p])
        detail2 = f"{method_label}  -  {door}  -  {ts}"
        if decision == "granted":
            self.access_title = "Access granted"
            self.access_message = result.get("door_detail") or result.get("message") or "Door unlocked."
            self.access_detail1 = line1
            self.access_detail2 = detail2
            self.show_toast_msg(f"Access granted: {person or method_label}")
        elif decision == "second_factor_required":
            self.access_state = "challenge"
            self.access_title = "PIN required"
            self.access_message = result.get("message") or "Complete the second factor with a PIN."
            self.access_detail1 = line1
            self.access_detail2 = detail2
            self._pending_challenge = result.get("challenge_token")
            Clock.schedule_once(lambda dt: self._open_second_factor_dialog(result), 0.1)
        elif decision == "unavailable":
            self.access_title = "Alternative access unavailable"
            self.access_message = result.get("message", "That method is not available.")
            self.access_detail1 = ""
            self.access_detail2 = detail2
            self.show_toast_msg(self.access_message, is_error=True)
        elif decision == "denied":
            self.access_title = "Access denied"
            self.access_message = result.get("message", "Access was denied.")
            self.access_detail1 = line1 if person else ""
            self.access_detail2 = detail2
            self.show_toast_msg(self.access_message, is_error=True)
        else:
            self.access_state = "error"
            self.access_title = "Door controller error"
            self.access_message = result.get("message", "The door did not respond.")
            self.access_detail1 = line1
            self.access_detail2 = detail2
            self.show_toast_msg(self.access_message, is_error=True)

    def _run_access_check(self, operation):
        """Run credential verification and the door call off the UI thread."""
        if self.access_busy:
            return
        self.access_busy = True
        self.access_state = "checking"
        self.access_title = "Checking credentials"
        self.access_message = "Applying person, door and schedule policy..."
        self.access_detail1 = ""
        self.access_detail2 = ""

        def worker():
            try:
                result = operation()
            except Exception as e:
                print(f"Access check failed: {e}")
                result = {
                    "decision": "error",
                    "message": "The access check failed unexpectedly.",
                    "door_name": self.door_name,
                    "method": "access",
                }
            Clock.schedule_once(lambda dt: self._complete_access_check(result), 0)

        Thread(target=worker, daemon=True).start()

    def _complete_access_check(self, result):
        self.access_busy = False
        self._apply_access_result(result)
        self.refresh_access_events()

    # -- alternative methods --------------------------------------
    def _tf(self, hint, text="", password=False, numeric=False):
        return MDTextField(
            hint_text=hint,
            text=text,
            password=password,
            mode="rectangle",
            font_size=sp(12),
            size_hint_y=None,
            height=dp(50),
            input_filter="int" if numeric else None,
        )

    def _form_scroll(self, box, max_height=430):
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(2))
        scroll.size_hint = (1, None)
        scroll.height = min(dp(max_height), max(dp(120), Window.height - dp(270)))
        scroll.add_widget(box)
        return scroll

    def _dialog_form(self, title, fields, submit_label, submit_callback):
        box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_y=None,
            padding=[0, dp(28), 0, 0],
        )
        for field in fields:
            box.add_widget(field)
        content_height = (
            sum(field.height for field in fields)
            + dp(8) * max(0, len(fields) - 1)
            + dp(38)
        )
        box.height = content_height
        scroll = self._form_scroll(box)
        scroll.height = min(scroll.height, content_height)
        content = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=scroll.height,
        )
        content.add_widget(scroll)
        dialog = MDDialog(
            title=title,
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    theme_text_color="Custom",
                    text_color=theme.muted,
                    on_release=self.txt_dialog_closer,
                ),
                MDFlatButton(
                    text=submit_label,
                    theme_text_color="Custom",
                    text_color=theme.primary_text,
                    on_release=lambda inst: submit_callback(dialog),
                ),
            ],
            radius=[dp(18), dp(18), dp(18), dp(18)],
        )
        self.txt_dialog = dialog
        dialog.open()
        return dialog

    def open_alternative_access(self):
        if self.access_busy:
            return
        if self.access_svc is None:
            self.show_toast_msg("The access registry is unavailable.", is_error=True)
            return
        svc = self.access_svc
        methods = svc.door.allowed_methods
        reader = svc.card_reader_status()
        face = svc.face_state()
        lines = [
            "Use an authorized backup method. All methods apply the same person, door and schedule policy.",
            "",
            f"Face: {'available' if face.get('enabled') else 'unavailable'}  |  PIN: {'available' if 'pin' in methods else 'disabled'}",
            f"Card: {reader.get('label')}  |  Administrator assistance: {'available' if 'admin' in methods else 'disabled'}",
        ]
        buttons = [
            MDFlatButton(
                text="Cancel",
                theme_text_color="Custom",
                text_color=theme.muted,
                on_release=self.txt_dialog_closer,
            ),
            MDFlatButton(
                text="ADMIN",
                theme_text_color="Custom",
                text_color=theme.warning,
                on_release=lambda inst: self._from_alt_dialog(self._open_admin_assistance_dialog),
            ),
            MDFlatButton(
                text="CARD",
                theme_text_color="Custom",
                text_color=theme.primary_text if reader.get("available") else theme.muted,
                on_release=lambda inst: self._from_alt_dialog(self._open_card_dialog),
            ),
            MDFlatButton(
                text="PIN",
                theme_text_color="Custom",
                text_color=theme.primary_text if "pin" in methods else theme.muted,
                on_release=lambda inst: self._from_alt_dialog(self._open_pin_dialog),
            ),
        ]
        self.txt_dialog = MDDialog(
            title="Alternative access",
            text="\n".join(lines),
            buttons=buttons,
            radius=[dp(18), dp(18), dp(18), dp(18)],
        )
        self.txt_dialog.open()

    def _from_alt_dialog(self, callback):
        self.txt_dialog_closer()
        Clock.schedule_once(lambda dt: callback(), 0.15)

    def _open_pin_dialog(self):
        svc = self.access_svc
        if svc is None or "pin" not in svc.door.allowed_methods:
            self.show_toast_msg("PIN access is disabled at this door.", is_error=True)
            return
        ref = self._tf("Staff / resident ID")
        pin = self._tf("Personal PIN", password=True, numeric=True)

        def submit(dialog):
            if not ref.text.strip() or not pin.text:
                self.show_toast_msg("Enter your ID and PIN.", is_error=True)
                return
            person_ref = ref.text.strip()
            entered_pin = pin.text
            dialog.dismiss()
            self._run_access_check(lambda: svc.authenticate_pin(person_ref, entered_pin))

        self._dialog_form("PIN access", [ref, pin], "UNLOCK", submit)

    def _open_card_dialog(self):
        svc = self.access_svc
        reader = svc.card_reader_status() if svc else {}
        if svc is None or not reader.get("available"):
            self.show_text_dialog(
                "Card reader unavailable",
                reader.get("label", "No card reader is connected to this kiosk.")
                + "\n\nA card credential cannot be accepted without a configured reader.",
                buttons=[
                    MDFlatButton(
                        text="Close",
                        theme_text_color="Custom",
                        text_color=theme.primary_text,
                        on_release=self.txt_dialog_closer,
                    )
                ],
            )
            return
        if "card" not in svc.door.allowed_methods:
            self.show_toast_msg("Card access is disabled at this door.", is_error=True)
            return
        uid = self._tf("Scan or enter card UID")

        def submit(dialog):
            if not uid.text.strip():
                self.show_toast_msg("Present a card or enter its UID.", is_error=True)
                return
            card_uid = uid.text
            dialog.dismiss()
            self._run_access_check(lambda: svc.authenticate_card(card_uid))

        self._dialog_form("Card access", [uid], "READ CARD", submit)

    def _open_admin_assistance_dialog(self):
        svc = self.access_svc
        if svc is None or "admin" not in svc.door.allowed_methods:
            self.show_toast_msg("Administrator assistance is disabled at this door.", is_error=True)
            return
        subject = self._tf("Subject staff / resident ID")
        reason = self._tf("Reason (audit logged)")
        admin_ref = self._tf("Administrator ID")
        admin_pin = self._tf("Administrator PIN", password=True, numeric=True)
        approver_ref = self._tf("Approver ID (if required)")
        approver_pin = self._tf("Approver PIN", password=True, numeric=True)

        def submit(dialog):
            if not subject.text.strip() or len(reason.text.strip()) < 5:
                self.show_toast_msg("Enter the subject and a reason of at least 5 characters.", is_error=True)
                return
            if not admin_ref.text.strip() or not admin_pin.text:
                self.show_toast_msg("Administrator credentials are required.", is_error=True)
                return
            actor = admin_ref.text.strip()
            actor_pin = admin_pin.text
            subject_ref = subject.text.strip()
            recorded_reason = reason.text.strip()
            approver = approver_ref.text.strip()
            approver_code = approver_pin.text
            dialog.dismiss()
            self._run_access_check(
                lambda: svc.authorize_admin_access(
                    actor, actor_pin, subject_ref, recorded_reason,
                    approver, approver_code,
                )
            )

        self._dialog_form(
            "Administrator assistance",
            [subject, reason, admin_ref, admin_pin, approver_ref, approver_pin],
            "AUTHORIZE",
            submit,
        )

    def _open_second_factor_dialog(self, result):
        svc = self.access_svc
        token = result.get("challenge_token")
        if svc is None or not token:
            return
        pin = self._tf("PIN for this person", password=True, numeric=True)

        def submit(dialog):
            if not pin.text:
                self.show_toast_msg("Enter the PIN to complete the second factor.", is_error=True)
                return
            entered = pin.text
            dialog.dismiss()
            self._pending_challenge = None
            self._run_access_check(lambda: svc.complete_challenge(token, entered))

        self._dialog_form("Second factor required", [pin], "VERIFY", submit)

    def _require_admin(self, title, detail, callback):
        if self.access_svc is None:
            self.show_toast_msg("The access registry is unavailable.", is_error=True)
            return
        if not self.access_svc.admin_required():
            self.show_toast_msg(
                "No administrator PIN is configured. Register or promote an administrator first.",
                is_error=True,
            )
            return
        admin_ref = self._tf("Administrator ID")
        admin_pin = self._tf("Administrator PIN", password=True, numeric=True)

        def submit(dialog):
            result = self.access_svc.verify_admin(admin_ref.text.strip(), admin_pin.text)
            if not result.get("ok"):
                self.show_toast_msg(result.get("message", "Administrator authorization failed."), is_error=True)
                return
            dialog.dismiss()
            callback(admin_ref.text.strip(), admin_pin.text)

        self._dialog_form(title, [admin_ref, admin_pin], "AUTHORIZE", submit)

    # -- registration modal ---------------------------------------
    def _show_registration_dialog(self, actor_ref=None, actor_pin=None, default_role="Staff"):
        if self.access_svc is None or not self.access_svc.ready:
            self.show_toast_msg("Start the face engine before registering.", is_error=True)
            return
        name = self._tf("Full name *")
        ext_id = self._tf("Staff / resident ID")
        role = self._tf("Role (Admin, Staff, Resident)", text=default_role)
        dept = self._tf("Department / zone")
        doors = self._tf("Doors (all or comma separated)", text="all")
        days = self._tf("Days (0=Mon ... 6=Sun)", text="0,1,2,3,4,5,6")
        start = self._tf("Start (HH:MM)", text="00:00")
        end = self._tf("End (HH:MM)", text="23:59")
        pin = self._tf("PIN (optional, 4-8 digits)", password=True, numeric=True)
        pin2 = self._tf("Confirm PIN", password=True, numeric=True)
        note = MDLabel(
            text="Face enrollment captures one clear face from the live camera. The first PIN must belong to an administrator role.",
            font_size=sp(10),
            size_hint_y=None,
            height=dp(34),
            text_size=(dp(480), None),
            theme_text_color="Custom",
            text_color=theme.muted,
        )

        def submit(dialog):
            if len(name.text.strip()) < 2:
                self.show_toast_msg("Enter a full name.", is_error=True)
                return
            if pin.text or pin2.text:
                if pin.text != pin2.text or not re.fullmatch(r"\d{4,8}", pin.text or ""):
                    self.show_toast_msg("PINs must match and contain 4-8 digits.", is_error=True)
                    return
            details = {
                "full_name": name.text.strip(),
                "external_id": ext_id.text.strip(),
                "role": role.text.strip(),
                "department": dept.text.strip(),
                "doors": doors.text.strip() or "all",
                "schedule_days": days.text.strip() or "0,1,2,3,4,5,6",
                "schedule_start": start.text.strip() or "00:00",
                "schedule_end": end.text.strip() or "23:59",
            }
            frame = self._capture_bgr_frame()
            if frame is None:
                self.show_toast_msg("The camera is not ready yet.", is_error=True)
                return
            result = self.access_svc.register_person(
                details, frame, actor_ref=actor_ref, actor_pin=actor_pin
            )
            if not result.get("ok"):
                self.show_toast_msg(result.get("message", "Could not register that person."), is_error=True)
                return
            person = result.get("person") or {}
            pin_note = ""
            if pin.text:
                pin_result = self.access_svc.set_pin(
                    person["id"], pin.text, actor_ref=actor_ref, actor_pin=actor_pin
                )
                if not pin_result.get("ok"):
                    pin_note = f" PIN not set: {pin_result.get('message')}"
            dialog.dismiss()
            self.show_toast_msg(f"{person.get('full_name', 'Person')} registered.{pin_note}")
            self.refresh_people()
            self.refresh_access_events()
            self._refresh_access_status()

        self._dialog_form(
            "Register a person",
            [name, ext_id, role, dept, doors, days, start, end, note, pin, pin2],
            "CAPTURE & REGISTER",
            submit,
        )

    # -- access activity ------------------------------------------
    def _fill_events(self, box, events):
        box.clear_widgets()
        if not events:
            box.add_widget(self._placeholder_label("No access events yet."))
            return
        for event in events:
            method = event.get("method") or "face"
            detail = f"{event.get('door_name', '')}  -  {event.get('reason', '')}"
            row = AccessEventRow(
                name=event.get("person_name") or "",
                decision=event.get("decision") or "",
                detail=detail,
                method_label=self._method_label(method),
                time_text=(event.get("ts") or "")[5:16],
            )
            box.add_widget(row)

    def refresh_access_events(self, instance=None):
        if not self.root:
            return
        events = self.access_svc.list_events(60) if self.access_svc else []
        access_events = self.root.ids.access_box.ids.access_events_box
        people_events = self.root.ids.people_box.ids.people_log_box
        self._fill_events(access_events, events[:6])
        self._fill_events(people_events, events[:60])
        self._fill_audit(self.root.ids.people_box.ids.people_audit_box)

    def _fill_audit(self, box):
        box.clear_widgets()
        if self.access_svc is None:
            box.add_widget(self._placeholder_label("Audit unavailable."))
            return
        events = self.access_svc.list_audit(24)
        if not events:
            box.add_widget(self._placeholder_label("No administrative changes recorded."))
            return
        labels = {
            "person_enrolled": "Person enrolled",
            "person_updated": "Person updated",
            "person_activated": "Person activated",
            "person_suspended": "Person suspended",
            "person_deleted": "Person deleted",
            "face_enrolled": "Face template added",
            "pin_set": "PIN set or reset",
            "pin_revoked": "PIN revoked",
            "card_enrolled": "Card enrolled",
            "card_revoked": "Card revoked",
            "card_lost": "Card marked lost",
            "admin_auth": "Administrator verified",
            "admin_auth_denied": "Administrator check denied",
            "controller_error": "Door controller error",
        }
        for event in events:
            who = event.get("actor_name") or "System"
            target = event.get("person_name") or ""
            detail = event.get("detail") or ""
            if target and target != who:
                detail = f"{who} -> {target}  -  {detail}"
            elif detail:
                detail = f"{who}  -  {detail}"
            box.add_widget(
                AuditEventRow(
                    action=labels.get(event.get("action"), str(event.get("action", "")).replace("_", " ").title()),
                    detail=detail,
                    time_text=(event.get("ts") or "")[5:16],
                )
            )

    def export_access_log(self, instance=None):
        if self.access_svc is None:
            self.show_toast_msg("The access registry is unavailable.", is_error=True)
            return
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.op_dir, f"access_log_{stamp}.csv")
        try:
            self.access_svc.export_events(path)
        except Exception as e:
            print(f"Could not export access log: {e}")
            self.show_toast_msg("Could not export the access log.", is_error=True)
            return
        self.show_toast_msg(f"Access log exported: {os.path.basename(path)}")

    def open_door_config(self, instance=None):
        if not os.path.exists(self.door_config_path) and self.door is not None:
            self.door.reload()
        self.open_file(self.door_config_path)

    def reload_door_config(self, instance=None):
        if self.access_svc is not None:
            self.access_svc.reload_door()
            self.door = self.access_svc.door
        elif self.door is not None:
            self.door.reload()
        else:
            self.door = DoorController(self.door_config_path)
        self._sync_door_labels()
        self._refresh_access_status()
        self.show_toast_msg("Door configuration reloaded.")

    def _placeholder_label(self, text):
        return MDLabel(
            text=text,
            font_size=sp(10),
            size_hint_y=None,
            height=dp(26),
            theme_text_color="Custom",
            text_color=theme.muted,
        )

    def refresh_people(self, instance=None):
        if not self.root:
            return
        box = self.root.ids.people_box.ids.people_registry_box
        box.clear_widgets()
        if self.access_svc is None:
            box.add_widget(self._placeholder_label("The registry is unavailable."))
            self.people_count_text = "Registry unavailable"
            self.people_admin_missing = True
            return
        self.people_admin_missing = not self.access_svc.admin_required()
        people = self.access_svc.list_people(self.people_search, self.people_filter)
        for person in people:
            meta = "  ·  ".join(
                [
                    value
                    for value in (
                        person.get("external_id"),
                        person.get("role"),
                        person.get("department"),
                    )
                    if value
                ]
            )
            doors = person.get("doors") or "all"
            schedule = f"{person.get('schedule_start', '00:00')}-{person.get('schedule_end', '23:59')}"
            meta = (meta + "  ·  " + doors + "  ·  " + schedule) if meta else f"{doors}  ·  {schedule}"
            face = "FACE" if person.get("face_count") else "NO FACE"
            pin_status = person.get("pin_status", "not_set")
            pin = (
                "PIN"
                if pin_status == "active"
                else ("PIN LOCKED" if pin_status == "locked" else ("PIN REVOKED" if pin_status == "revoked" else "NO PIN"))
            )
            cards = int(person.get("card_count") or 0)
            creds = f"{face}  ·  {pin}  ·  {cards} CARD" + ("" if cards == 1 else "S")
            row = PeopleRow(
                full_name=person["full_name"],
                meta=meta,
                credentials=creds,
                active=bool(person.get("active")),
            )
            row.manage_callback = lambda p=person: self.manage_person(p["id"])
            box.add_widget(row)
        if not people:
            if self.people_search or self.people_filter != "all":
                box.add_widget(self._placeholder_label("No people match this search or filter."))
            else:
                box.add_widget(self._placeholder_label("No people registered yet."))
        count = len(people)
        self.people_count_text = (
            "None shown" if count == 0 else f"{count} shown"
        )

    def set_people_search(self, text):
        if text == self.people_search:
            return
        self.people_search = text
        self.refresh_people()

    def set_people_filter(self, value):
        if value not in ("all", "active", "suspended", "no_face"):
            return
        self.people_filter = value
        self.refresh_people()

    # -- person management ----------------------------------------
    def manage_person(self, person_id):
        if self.access_svc is None:
            self.show_toast_msg("The access registry is unavailable.", is_error=True)
            return
        if not self.access_svc.admin_required():
            self.show_toast_msg(
                "Set up an administrator PIN before managing credentials.", is_error=True
            )
            return
        self._require_admin(
            "Manage person",
            "Administrator authorization is required to edit people or their credentials.",
            lambda actor_ref, actor_pin: self._show_person_dialog(
                person_id, actor_ref, actor_pin
            ),
        )

    def _show_person_dialog(self, person_id, actor_ref, actor_pin):
        profile = self.access_svc.person_profile(person_id) if self.access_svc else None
        if not profile:
            self.show_toast_msg("Person not found.", is_error=True)
            return
        box = MDBoxLayout(
            orientation="vertical", spacing=dp(8), size_hint_y=None, adaptive_height=True
        )
        header = MDLabel(
            text=profile["full_name"],
            font_size=sp(20),
            bold=True,
            size_hint_y=None,
            height=dp(30),
            theme_text_color="Custom",
            text_color=theme.text,
        )
        box.add_widget(header)
        status = "Active" if profile.get("active") else "Suspended"
        detail = (
            f"{profile.get('external_id') or 'No ID'}  ·  {profile.get('role') or 'No role'}"
            f"  ·  {profile.get('department') or 'No department'}\n"
            f"Doors: {profile.get('doors') or 'all'}  ·  "
            f"Schedule: {profile.get('schedule_start', '00:00')}-{profile.get('schedule_end', '23:59')} "
            f"days {profile.get('schedule_days', '')}\n"
            f"Status: {status}  ·  Face templates: {profile.get('face_count', 0)}  ·  "
            f"PIN: {profile.get('pin_status', 'not_set')}"
        )
        info = MDLabel(
            text=detail,
            font_size=sp(11),
            size_hint_y=None,
            height=dp(76),
            text_size=(dp(520), None),
            theme_text_color="Custom",
            text_color=theme.muted,
        )
        box.add_widget(info)

        def act(callback):
            self.txt_dialog_closer()
            Clock.schedule_once(lambda dt: callback(), 0.12)

        actions = [
            ("Edit details", lambda: act(lambda: self._open_person_edit(profile, actor_ref, actor_pin))),
            ("Set / reset PIN", lambda: act(lambda: self._open_person_pin(profile, actor_ref, actor_pin))),
            ("Enroll face", lambda: act(lambda: self._open_re_enroll_face(profile, actor_ref, actor_pin))),
            ("Revoke PIN", lambda: act(lambda: self._revoke_person_pin(profile, actor_ref, actor_pin))),
            ("Add card", lambda: act(lambda: self._open_person_card(profile, actor_ref, actor_pin))),
            (
                "Activate" if not profile.get("active") else "Suspend",
                lambda: act(lambda: self._set_person_active(profile, not profile.get("active"), actor_ref, actor_pin)),
            ),
            ("Delete", lambda: act(lambda: self._confirm_person_delete(profile, actor_ref, actor_pin))),
        ]
        cols = 2 if self.is_wide else 1
        rows = (len(actions) + cols - 1) // cols
        grid = MDGridLayout(cols=cols, spacing=dp(6), size_hint_y=None)
        grid.height = dp(38) * rows + dp(6) * max(0, rows - 1)
        for label, callback in actions:
            btn = MDFlatButton(
                text=label,
                font_size=sp(10),
                theme_text_color="Custom",
                text_color=theme.error if label in ("Delete", "Suspend") else theme.primary_text,
            )
            btn.bind(on_release=lambda inst, cb=callback: cb())
            grid.add_widget(btn)
        box.add_widget(grid)

        cards = profile.get("cards") or []
        box.add_widget(
            MDLabel(
                text="Cards",
                font_size=sp(13),
                bold=True,
                size_hint_y=None,
                height=dp(24),
                theme_text_color="Custom",
                text_color=theme.text,
            )
        )
        if not cards:
            box.add_widget(
                MDLabel(
                    text="No card credentials enrolled.",
                    font_size=sp(10),
                    size_hint_y=None,
                    height=dp(24),
                    theme_text_color="Custom",
                    text_color=theme.muted,
                )
            )
        for card in cards:
            row = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(34),
                spacing=dp(8),
            )
            row.add_widget(
                MDLabel(
                    text=f"{card.get('card_ref', 'card')}  ·  {card.get('status', '')}  ·  {card.get('valid_until') or 'no expiry'}",
                    font_size=sp(10),
                    theme_text_color="Custom",
                    text_color=theme.muted,
                )
            )
            for label, lost in (("Lost", True), ("Revoke", False)):
                btn = MDFlatButton(
                    text=label,
                    font_size=sp(9),
                    theme_text_color="Custom",
                    text_color=theme.error,
                )
                btn.bind(
                    on_release=lambda inst, cid=card["id"], is_lost=lost: act(
                        lambda: self._card_action(cid, is_lost, actor_ref, actor_pin)
                    )
                )
                row.add_widget(btn)
            box.add_widget(row)

        scroll = self._form_scroll(box, max_height=380)
        content = MDBoxLayout(orientation="vertical", size_hint_y=None, height=scroll.height)
        content.add_widget(scroll)
        dialog = MDDialog(
            title="Person and credentials",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="Close",
                    theme_text_color="Custom",
                    text_color=theme.muted,
                    on_release=self.txt_dialog_closer,
                )
            ],
            radius=[dp(18), dp(18), dp(18), dp(18)],
        )
        self.txt_dialog = dialog
        dialog.open()

    def _open_re_enroll_face(self, profile, actor_ref, actor_pin):
        if self.access_svc is None or not self.access_svc.ready:
            self.show_toast_msg("Start the face engine before enrolling a face.", is_error=True)
            return
        self.show_toast_msg("Opening the enrollment camera...")
        self.goto_screen("accessScr")
        Clock.schedule_once(
            lambda dt: self._show_re_enroll_capture(profile, actor_ref, actor_pin), 1.4
        )

    def _show_re_enroll_capture(self, profile, actor_ref, actor_pin):
        if self.current_screen != "accessScr":
            return
        self.show_text_dialog(
            "Enroll another face sample",
            f"Look straight at the live camera and capture a clear, single face for {profile['full_name']}. "
            "Existing templates and credentials stay in place.",
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    theme_text_color="Custom",
                    text_color=theme.muted,
                    on_release=self.txt_dialog_closer,
                ),
                MDFlatButton(
                    text="CAPTURE",
                    theme_text_color="Custom",
                    text_color=theme.primary_text,
                    on_release=lambda inst: self._capture_re_enroll(profile, actor_ref, actor_pin),
                ),
            ],
        )

    def _capture_re_enroll(self, profile, actor_ref, actor_pin):
        self.txt_dialog_closer()
        frame = self._capture_bgr_frame()
        if frame is None:
            self.show_toast_msg("The camera is not ready yet.", is_error=True)
            return
        result = self.access_svc.enroll_face(
            profile["id"], frame, actor_ref=actor_ref, actor_pin=actor_pin
        )
        self.refresh_people()
        if result.get("ok"):
            self.show_toast_msg("Face template added.")
        else:
            self.show_toast_msg(result.get("message", "Could not enroll that face."), is_error=True)

    def _open_person_edit(self, profile, actor_ref, actor_pin):
        name = self._tf("Full name", text=profile.get("full_name", ""))
        ext_id = self._tf("Staff / resident ID", text=profile.get("external_id", ""))
        role = self._tf("Role", text=profile.get("role", ""))
        dept = self._tf("Department / zone", text=profile.get("department", ""))
        doors = self._tf("Allowed doors", text=profile.get("doors", "all"))
        days = self._tf("Access days (0=Mon ... 6=Sun)", text=profile.get("schedule_days", "0,1,2,3,4,5,6"))
        start = self._tf("Access start (HH:MM)", text=profile.get("schedule_start", "00:00"))
        end = self._tf("Access end (HH:MM)", text=profile.get("schedule_end", "23:59"))

        def submit(dialog):
            if len(name.text.strip()) < 2:
                self.show_toast_msg("Enter a full name.", is_error=True)
                return
            result = self.access_svc.update_person(
                profile["id"],
                {
                    "full_name": name.text.strip(),
                    "external_id": ext_id.text.strip(),
                    "role": role.text.strip(),
                    "department": dept.text.strip(),
                    "doors": doors.text.strip() or "all",
                    "schedule_days": days.text.strip() or "0,1,2,3,4,5,6",
                    "schedule_start": start.text.strip() or "00:00",
                    "schedule_end": end.text.strip() or "23:59",
                },
                actor_ref=actor_ref,
                actor_pin=actor_pin,
            )
            if not result.get("ok"):
                self.show_toast_msg(result.get("message", "Could not update person."), is_error=True)
                return
            dialog.dismiss()
            self.refresh_people()
            self.show_toast_msg("Person updated.")

        self._dialog_form("Edit person", [name, ext_id, role, dept, doors, days, start, end], "SAVE", submit)

    def _open_person_pin(self, profile, actor_ref, actor_pin):
        pin = self._tf("New PIN (4-8 digits)", password=True, numeric=True)
        confirm = self._tf("Confirm PIN", password=True, numeric=True)

        def submit(dialog):
            if not re.fullmatch(r"\d{4,8}", pin.text or ""):
                self.show_toast_msg("PIN must be 4-8 digits.", is_error=True)
                return
            if pin.text != confirm.text:
                self.show_toast_msg("PINs do not match.", is_error=True)
                return
            result = self.access_svc.set_pin(
                profile["id"], pin.text, actor_ref=actor_ref, actor_pin=actor_pin
            )
            if not result.get("ok"):
                self.show_toast_msg(result.get("message", "Could not set PIN."), is_error=True)
                return
            dialog.dismiss()
            self.refresh_people()
            self.show_toast_msg("PIN set.")

        self._dialog_form(f"Set PIN for {profile['full_name']}", [pin, confirm], "SET PIN", submit)

    def _revoke_person_pin(self, profile, actor_ref, actor_pin):
        result = self.access_svc.revoke_pin(
            profile["id"], actor_ref=actor_ref, actor_pin=actor_pin
        )
        self.refresh_people()
        if result.get("ok"):
            self.show_toast_msg("PIN revoked.")
        else:
            self.show_toast_msg(result.get("message", "Could not revoke PIN."), is_error=True)

    def _open_person_card(self, profile, actor_ref, actor_pin):
        uid = self._tf("Card UID from reader")
        expiry = self._tf("Expiry (YYYY-MM-DD, optional)")
        reader = self.access_svc.card_reader_status() if self.access_svc else {}
        note = MDLabel(
            text=reader.get("label", "No card reader connected")
            + "\nManual UID enrollment is an administrative action; card authentication still requires a configured reader.",
            font_size=sp(10),
            size_hint_y=None,
            height=dp(40),
            text_size=(dp(480), None),
            theme_text_color="Custom",
            text_color=theme.muted,
        )

        def submit(dialog):
            result = self.access_svc.assign_card(
                profile["id"],
                uid.text.strip(),
                expiry.text.strip(),
                actor_ref=actor_ref,
                actor_pin=actor_pin,
            )
            if not result.get("ok"):
                self.show_toast_msg(result.get("message", "Could not add card."), is_error=True)
                return
            dialog.dismiss()
            self.refresh_people()
            self.show_toast_msg(result.get("message", "Card enrolled."))

        self._dialog_form(f"Add card for {profile['full_name']}", [note, uid, expiry], "ADD CARD", submit)

    def _set_person_active(self, profile, active, actor_ref, actor_pin):
        result = self.access_svc.set_active(
            profile["id"], active, actor_ref=actor_ref, actor_pin=actor_pin
        )
        self.refresh_people()
        if result.get("ok"):
            self.show_toast_msg("Person activated." if active else "Person suspended.")
        else:
            self.show_toast_msg(result.get("message", "Could not change status."), is_error=True)

    def _confirm_person_delete(self, profile, actor_ref, actor_pin):
        self.show_text_dialog(
            "Delete person?",
            f"{profile['full_name']} will be deleted with their face templates, PIN and cards. "
            "Their past access events remain in the audit log.",
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    theme_text_color="Custom",
                    text_color=theme.muted,
                    on_release=self.txt_dialog_closer,
                ),
                MDFlatButton(
                    text="DELETE",
                    theme_text_color="Custom",
                    text_color=theme.error,
                    on_release=lambda inst: self._delete_person_admin(
                        profile["id"], actor_ref, actor_pin
                    ),
                ),
            ],
        )

    def _delete_person_admin(self, person_id, actor_ref, actor_pin):
        self.txt_dialog_closer()
        result = self.access_svc.delete_person(
            person_id, actor_ref=actor_ref, actor_pin=actor_pin
        )
        self.refresh_people()
        if result.get("ok"):
            self.show_toast_msg("Person deleted.")
        else:
            self.show_toast_msg(result.get("message", "Could not delete person."), is_error=True)

    def _card_action(self, card_id, lost, actor_ref, actor_pin):
        result = self.access_svc.revoke_card(
            card_id, actor_ref=actor_ref, actor_pin=actor_pin, lost=lost
        )
        self.refresh_people()
        if result.get("ok"):
            self.show_toast_msg(result.get("message", "Card updated."))
        else:
            self.show_toast_msg(result.get("message", "Could not update card."), is_error=True)

    def toggle_theme(self, instance=None):
        self.set_theme(not self.theme_dark)

    def set_theme(self, dark):
        dark = bool(dark)
        self.theme_dark = dark
        self.theme_label = "Dark" if dark else "Light"
        theme.apply("dark" if dark else "light")
        try:
            self.theme_cls.theme_style = "Dark" if dark else "Light"
        except Exception as e:
            print(f"Could not switch the material theme: {e}")
        Window.clearcolor = get_color_from_hex(theme.surface)
        try:
            self.root.canvas.ask_update()
            Window.canvas.ask_update()
        except Exception:
            pass
        self.user_preferences["dark"] = dark
        if os.path.exists(self.usr_pref_path):
            self.save_config_file(self.user_preferences, self.usr_pref_path)
        Clock.schedule_once(lambda dt: self._refresh_after_theme(), .05)

    def _refresh_after_theme(self):
        if not self.root:
            return
        self.refresh_people()
        self.refresh_access_events()
        self._refresh_access_status()
        self.refresh_recent_outputs()
        self.refresh_output_count()
        if self.sec_file_box is not None:
            self.refresh_sec_file_list()
        self.reset_access_result()

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
        self.access_db_path = os.path.join(db_dir, "access.db")
        self.door_config_path = os.path.join(self.config_dir, "doors.json")
        self.access_snapshot_dir = os.path.join(self.op_dir, "access")
        os.makedirs(self.access_snapshot_dir, exist_ok=True)
        try:
            self.access_svc = AccessSvc(
                self.access_db_path,
                None,
                self.door_config_path,
                self.access_snapshot_dir,
            )
            self.door = self.access_svc.door
            self._sync_door_labels()
        except Exception as e:
            print(f"Could not initialise the access registry: {e}")
            self.access_svc = None
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
        self.user_preferences["dark"] = old_pref.get("dark", self.theme_dark)
        self.reduce_motion = bool(old_pref.get("reduce_motion", False))
        self.motion_label = "On" if self.reduce_motion else "Off"
        self.face_tip_visible = not self.user_preferences["fm_dont_again"]
        self.vault_tip_visible = not self.user_preferences["sec_dont_again"]
        if bool(self.user_preferences["dark"]) != self.theme_dark:
            self.set_theme(bool(self.user_preferences["dark"]))
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
        Clock.schedule_once(lambda dt: self.refresh_people())
        Clock.schedule_once(lambda dt: self.refresh_access_events())
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

        if is_error:
            duration = max(duration, 6)
        lines = max(1, len(str(message)) // 52 + 1)

        previous = getattr(self, "_toast", None)
        if previous is not None and previous.parent:
            previous.parent.remove_widget(previous)
        toast = MDCard(
            orientation="horizontal",
            size_hint=(None, None),
            width=min(Window.width - dp(32), dp(430)),
            height=dp(46) if lines == 1 else dp(62),
            padding=(dp(14), 0),
            spacing=dp(10),
            radius=[dp(14)],
            elevation=3,
            md_bg_color=get_color_from_hex(theme.error if is_error else "#1F2937"),
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
                height=toast.height - dp(8),
                pos_hint={"center_y": 0.5},
            )
        )
        Window.add_widget(toast)
        toast.pos = (Window.width / 2 - toast.width / 2, dp(24))
        toast.opacity = 0 if not self.reduce_motion else 1
        if not self.reduce_motion:
            Animation(opacity=1, d=0.15).start(toast)
        self._toast = toast

        def dismiss():
            # Drop the elevation before fading: KivyMD's shadow is a separate
            # canvas layer and can outlive an opacity animation.
            toast.elevation = 0
            if self.reduce_motion:
                if toast.parent:
                    toast.parent.remove_widget(toast)
                return
            anim = Animation(opacity=0, d=0.2)
            anim.bind(
                on_complete=lambda *a: (
                    toast.parent.remove_widget(toast) if toast.parent else None
                )
            )
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
            self._refresh_access_status()
            if self.current_screen == "accessScr":
                card = self._access_camera_card()
                if card is not None and self.camera is None:
                    self._attach_camera_to_card(card)
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
            if self.access_svc is not None:
                self.access_svc.face_ai = self.face_ai
            else:
                self.access_svc = AccessSvc(
                    self.access_db_path,
                    self.face_ai,
                    self.door_config_path,
                    self.access_snapshot_dir,
                )
                self.door = self.access_svc.door
            self._sync_door_labels()
            self._refresh_access_status()
            if self.current_screen == "accessScr":
                card = self._access_camera_card()
                if card is not None and self.camera is None:
                    self._attach_camera_to_card(card)
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
        self.goto_screen("faceFindScr")

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

    def update_match_step(self):
        if self.is_onnx_running:
            self.match_step_index = 3
            self.match_step_text = "3/4  -  Matching..."
        elif self.match_has_results:
            self.match_step_index = 4
            self.match_step_text = "4/4  -  Inspect results"
        elif self.src_image_path and self.trgt_image_path:
            self.match_step_index = 3
            self.match_step_text = "3/4  -  Run match"
        elif self.src_image_path:
            self.match_step_index = 2
            self.match_step_text = "2/4  -  Add target"
        else:
            self.match_step_index = 1
            self.match_step_text = "1/4  -  Source face"

    def update_ready_to_match(self):
        self.ready_to_match = bool(self.src_image_path and self.trgt_image_path)
        self._refresh_result_placeholders()
        self.update_match_step()

    def cancel_face_match(self, instance=None):
        if not self.is_onnx_running:
            return
        self._match_token += 1
        self.is_onnx_running = False
        self.match_has_results = False
        self._refresh_result_placeholders()
        self.update_match_step()
        self.show_toast_msg("Match cancelled.")

    def _on_file_drop_file(self, window, file_path, x, y):
        if not self.root or self.root.ids.screen_manager.current != "faceFindScr":
            return
        try:
            if isinstance(file_path, bytes):
                file_path = file_path.decode("utf-8")
        except Exception:
            return
        if not str(file_path).lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            self.show_toast_msg("Drop a JPG, PNG or WEBP image.", is_error=True)
            return
        self.img_purpose = "src" if not self.src_image_path else "trgt"
        if self.select_img_path(str(file_path)):
            which = "source" if self.img_purpose == "src" else "target"
            self.show_toast_msg(f"Dropped image added to the {which}.")

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
            return False
        tile.image_source = path
        tile.file_name = os.path.basename(path)
        self.match_has_results = False
        self.update_ready_to_match()
        return True

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
                        text_color=theme.success,
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
        self._match_token += 1
        token = self._match_token
        self.match_has_results = False
        self.is_onnx_running = True
        self.update_match_step()
        self._show_matching_state()
        Thread(
            target=self._run_face_match,
            args=(self.src_image_path, self.trgt_image_path, token),
            daemon=True,
        ).start()

    def _run_face_match(self, img1_path, img2_path, token):
        """Run the comparison, guaranteeing the UI leaves its busy state."""
        def deliver(resp):
            Clock.schedule_once(lambda dt: self.face_match_callback(resp, token))

        try:
            self.face_ai.face_match_group(
                img1_path=img1_path,
                img2_path=img2_path,
                callback=deliver,
            )
        except Exception as e:
            print(f"Face match failed: {e}")
            deliver(
                {
                    "stat": False,
                    "msg": "Something went wrong while matching. Please try again.",
                    "src": "",
                    "trgt": "",
                }
            )

    def face_match_callback(self, resp, token=None):
        if token is not None and token != self._match_token:
            return
        self.is_onnx_running = False
        if not resp or not resp.get("stat"):
            self.match_has_results = False
            self.update_match_step()
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
        self.match_has_results = True
        self.update_match_step()
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
                        text_color=theme.error,
                        on_release=self.delete_selected_file
                    ),
                    MDFlatButton(
                        text="Save",
                        theme_text_color="Custom",
                        text_color=theme.success,
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
                    text_color=theme.error,
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
        self._match_token += 1
        self.is_onnx_running = False
        self.match_has_results = False
        self.src_image_path = None
        self.trgt_image_path = None
        self.img_purpose = ""
        fm = self.root.ids.face_match_scr.ids
        for tile_id in ("fm_src_tile", "fm_trgt_tile"):
            tile = fm[tile_id]
            tile.image_source = ""
            tile.file_name = ""
        self.update_ready_to_match()
        self.update_match_step()

    # Security section starts here
    def on_security_enter(self):
        self.verifying = False
        self.on_security_leave()  # clear existing things and lock
        self.sec_uix = self.root.ids.security_box.ids.sec_elements_box
        permissions_ok = self.check_request_total_permission()
        if not permissions_ok:
            self._show_vault_notice(
                "Camera access needed",
                "Allow camera access in your system settings, then return to the vault.",
                icon="camera-off-outline",
            )
            return
        if not self.face_ai or not self.services_running:
            self._show_vault_notice(
                "Vault is locked",
                "Start the face engine to unlock your encrypted files. Nothing leaves this device.",
                icon="shield-lock-outline",
                offer_start=True,
            )
            return
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

    def _show_vault_notice(self, title, detail, icon="information-outline", offer_start=False):
        from kivymd.uix.label import MDIcon

        self.sec_uix.clear_widgets()
        width = min(Window.width - dp(48), dp(560))
        card = AppCard(
            orientation="vertical",
            size_hint=(None, None),
            size=(width, dp(292)),
            padding=dp(24),
            spacing=dp(10),
        )
        badge = IconBadge(icon=icon, size=(dp(48), dp(48)), size_hint=(None, None))
        card.add_widget(badge)
        title_label = MDLabel(
            text=title,
            font_size=sp(21),
            bold=True,
            size_hint_y=None,
            height=dp(30),
            theme_text_color="Custom",
            text_color=get_color_from_hex(theme.text),
        )
        card.add_widget(title_label)
        detail_label = MDLabel(
            text=detail,
            font_size=sp(12),
            size_hint_y=None,
            height=dp(46),
            text_size=(width - dp(48), None),
            theme_text_color="Custom",
            text_color=get_color_from_hex(theme.muted),
        )
        card.add_widget(detail_label)
        if offer_start:
            start = MDFillRoundFlatIconButton(
                text="Start face engine",
                icon="power",
                font_size=sp(12),
                size_hint=(None, None),
                size=(dp(210), dp(44)),
                md_bg_color=get_color_from_hex(theme.primary),
                theme_text_color="Custom",
                text_color=get_color_from_hex(theme.text_on_primary),
                theme_icon_color="Custom",
                icon_color=get_color_from_hex(theme.text_on_primary),
            )
            start.bind(on_release=lambda inst: self.start_engine_for_vault())
            card.add_widget(start)
        card.add_widget(Widget())
        note = MDLabel(
            text="Files stay encrypted while the engine is off.",
            font_size=sp(10),
            size_hint_y=None,
            height=dp(18),
            theme_text_color="Custom",
            text_color=get_color_from_hex(theme.muted),
        )
        card.add_widget(note)
        row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(308))
        row.add_widget(Widget())
        row.add_widget(card)
        row.add_widget(Widget())
        self.sec_uix.add_widget(row)
        self.sec_uix.add_widget(Widget())

    def start_engine_for_vault(self, instance=None):
        self.start_face_services()
        self._vault_engine_attempts = 0
        Clock.schedule_once(self._wait_for_vault_engine, 0.4)

    def _wait_for_vault_engine(self, dt=None):
        if self.current_screen != "securityScr":
            return
        if self.services_running:
            self.on_security_enter()
            return
        self._vault_engine_attempts = getattr(self, "_vault_engine_attempts", 0) + 1
        if self._vault_engine_attempts < 25:
            Clock.schedule_once(self._wait_for_vault_engine, 0.4)

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
        card = CameraCard()
        self._attach_camera_to_card(card)
        return card

    def _attach_camera_to_card(self, card):
        cam_indx = self._camera_index()
        resolution = (960, 720) if platform == "android" else (640, 480)
        if platform == "android":
            now = datetime.datetime.now()
            self.tmp_login_filename = os.path.join(
                self.sec_file_dir,
                f"login_{now.strftime('%Y%m%d')}_{now.strftime('%H%M%S')}.jpg",
            )
        self.camera_card = card
        if cam_indx < 0:
            card.show_error("No camera was found on this device.")
            self.show_toast_msg("No camera found on this device.", is_error=True)
            return card
        try:
            if self._camera_stop_event is not None:
                Clock.unschedule(self._camera_stop_event)
                self._camera_stop_event = None
            if not self.camera:
                self.camera = Camera(
                    index=cam_indx,
                    resolution=resolution,
                    fit_mode="contain",
                    play=True,
                )
            else:
                # Reuse the one AVFoundation camera. Tearing down and
                # recreating it on every navigation was unstable on macOS.
                if self.camera.parent:
                    self.camera.parent.remove_widget(self.camera)
                self.camera.play = True
            holder = card.ids.cam_holder
            self._camera_holder = holder
            if platform == "android":
                self.camera.size_hint = (1, 1)
            else:
                self.camera.size_hint = (None, None)
                self.camera.fit_mode = "fill"
                if not self._camera_configured:
                    with self.camera.canvas.before:
                        PushMatrix()
                        self._camera_rotate = Rotate(
                            angle=-90, origin=self.camera.center
                        )
                    with self.camera.canvas.after:
                        PopMatrix()
                    self._camera_configured = True
                holder.bind(size=lambda *a: self._fit_rotated_camera(holder))
                Clock.schedule_once(lambda dt: self._fit_rotated_camera(holder))
            holder.add_widget(self.camera)
            card.status = "LIVE" if self.camera.texture else "Starting..."
            if not self._camera_status_bound:
                self.camera.bind(texture=self._on_camera_texture)
                self._camera_status_bound = True
            Clock.schedule_once(lambda dt: self._refresh_camera_status(card), 1.2)
        except Exception as e:
            print(f"Error setting up the camera: {e}")
            card.show_error("The camera could not be started.\nCheck the camera permission.")
            self.show_toast_msg("The camera could not be started.", is_error=True)
        return card

    def _on_camera_texture(self, instance, texture):
        self._refresh_camera_status(self.camera_card)

    def _fit_rotated_camera(self, holder):
        if platform == "android" or not self.camera:
            return
        if holder is not self._camera_holder:
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

    def stop_camera(self):
        self._camera_holder = None
        if self.camera:
            if self.camera.parent:
                self.camera.parent.remove_widget(self.camera)
            if self._camera_stop_event is not None:
                Clock.unschedule(self._camera_stop_event)
            # Give AVFoundation time to finish startRunning before asking it
            # to stop, and keep the single camera instance alive.
            self._camera_stop_event = Clock.schedule_once(
                self._really_stop_camera, 1.2
            )
        self.camera_card = None
        self.verifying = False

    def _really_stop_camera(self, dt=None):
        self._camera_stop_event = None
        if self.camera_card is not None:
            return
        if self.camera:
            try:
                self.camera.play = False
            except Exception as e:
                print(f"Could not stop the camera cleanly: {e}")

    def _capture_bgr_frame(self):
        if not self.camera or not self.camera.texture:
            return None
        try:
            import cv2
            import numpy as np
            texture = self.camera.texture
            width, height = texture.size
            arr = np.frombuffer(texture.pixels, dtype=np.uint8).reshape((height, width, 4))
            img = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            if platform == "android":
                img = np.flipud(img)
            else:
                img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
            return img
        except Exception as e:
            print(f"Could not capture a camera frame: {e}")
            return None

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

    def set_vault_search(self, text):
        if text == self.vault_search:
            return
        self.vault_search = text
        self.refresh_sec_file_list()

    def toggle_vault_sort(self, instance=None):
        self.vault_sort = "name" if self.vault_sort == "date" else "date"
        self.vault_sort_label = "Newest" if self.vault_sort == "date" else "Name A-Z"
        self.refresh_sec_file_list()

    def refresh_sec_file_list(self, instance=None):
        if not self.sec_file_box:
            return
        secMdList = self.sec_file_box.ids.sec_file_list
        secMdList.clear_widgets()
        files = []
        for name in self.get_sec_file_list(self.sec_file_dir):
            full_path = os.path.join(self.sec_file_dir, name)
            try:
                stamp = os.path.getmtime(full_path)
                size = os.path.getsize(full_path)
            except OSError:
                stamp, size = 0, 0
            files.append({"name": str(name), "stamp": stamp, "size": size})
        query = self.vault_search.strip().lower()
        if query:
            files = [f for f in files if query in f["name"].lower()]
        if self.vault_sort == "name":
            files.sort(key=lambda f: f["name"].lower())
        else:
            files.sort(key=lambda f: f["stamp"], reverse=True)
        for info in files:
            fileElem = SecSingleFile()
            fileElem.filename = info["name"]
            size = info["size"]
            size_txt = (
                f"{size / 1024:.0f} KB"
                if size < 1024 * 1024
                else f"{size / (1024 * 1024):.1f} MB"
            )
            if info["stamp"]:
                date_txt = datetime.datetime.fromtimestamp(info["stamp"]).strftime("%d %b %Y")
                fileElem.detail = f"Encrypted - {size_txt} - {date_txt}"
            else:
                fileElem.detail = "Encrypted - tap to download"
            secMdList.add_widget(fileElem)
        count = len(files)
        self.vault_count_text = (
            "0 files" if count == 0 else f"{count} encrypted file" + ("" if count == 1 else "s")
        )
        empty = self.sec_file_box.ids.sec_empty
        if query and not files:
            empty.text = "No matching files"
            empty.detail = "Try a different search."
        else:
            empty.text = "No files yet"
            empty.detail = "Upload a file to keep it encrypted on this device."
        self._toggle_vault_empty(count == 0)

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
            img = self._capture_bgr_frame()
            if img is None:
                raise ValueError("camera frame is not ready")
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
        self.vault_busy = True
        self.show_toast_msg(f"Encrypting {filename}...")
        Thread(
            target=self._encrypt_vault_file,
            args=(file_path, target_file, filename),
            daemon=True,
        ).start()

    def _encrypt_vault_file(self, file_path, target_file, filename):
        """Encrypt off the UI thread, then hand the result back to the main thread."""
        try:
            if platform == "android":
                # encryption not required on android as the internal path is secure
                import shutil
                shutil.copyfile(file_path, target_file)
            else:
                from cryptography.fernet import Fernet
                with open(self.encrypt_key, "rb") as key_file:
                    key = key_file.read()
                fernet = Fernet(key)
                with open(file_path, "rb") as file:
                    original_data = file.read()
                encrypted_data = fernet.encrypt(original_data)
                tmp_file = target_file + ".part"
                with open(tmp_file, "wb") as tfile:
                    tfile.write(encrypted_data)
                os.replace(tmp_file, target_file)
            print(f"File {filename} successfully uploaded to vault")
            Clock.schedule_once(lambda dt: self._vault_upload_done(filename, None))
        except Exception as e:
            print(f"Error saving file: {e}")
            try:
                os.remove(target_file + ".part")
            except OSError:
                pass
            error = e
            Clock.schedule_once(
                lambda dt, err=error: self._vault_upload_done(filename, err)
            )

    def _vault_upload_done(self, filename, error):
        self.vault_busy = False
        if error is not None:
            self.show_toast_msg("Could not encrypt that file.", is_error=True)
            return
        self.refresh_sec_file_list()
        self.show_toast_msg(f"{filename} is now encrypted in your vault.")

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
                    text_color=theme.error,
                    on_release=self.delete_selected_file,
                ),
            ],
        )

    def on_security_leave(self):
        if self.camera:
            print("Camera has been stopped")
        self.stop_camera()
        # Leaving the vault re-locks it; face auth is required on re-entry.
        self.login_success = False
        self.sec_file_box = None
        if self.sec_uix:
            self.sec_uix.clear_widgets()

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
                    text_color=theme.error,
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
            "Shortcuts: Ctrl/Cmd+1..6 switch sections, Ctrl/Cmd+O picks a photo,\n"
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
                text_color=theme.primary_text,
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