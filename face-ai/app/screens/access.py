from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, StringProperty
from kivy.utils import platform

from kivymd.uix.boxlayout import MDBoxLayout

# Local imports (their kv rules are registered here as well).
from screens.security import CameraCard  # noqa: F401
from screens.ui import (  # noqa: F401
    AppCard,
    IconBadge,
    StatusPill,
)


Builder.load_string('''
#:import tokens screens.tokens
#:import AppCard screens.ui.AppCard
#:import CameraCard screens.security.CameraCard
#:import IconBadge screens.ui.IconBadge
#:import StatusPill screens.ui.StatusPill


<AccessResultCard>:
    orientation: "vertical"
    size_hint_y: None
    padding: dp(16)
    spacing: dp(6)

    MDBoxLayout:
        size_hint_y: None
        height: dp(46)
        spacing: dp(12)

        IconBadge:
            icon: "account-check-outline" if root.state == "granted" else ("alert-circle-outline" if root.state in ("denied", "error") else "face-recognition")
            bg: tokens.SUCCESS_SOFT if root.state == "granted" else (tokens.ERROR_SOFT if root.state in ("denied", "error") else tokens.PRIMARY_SOFT)
            fg: tokens.SUCCESS if root.state == "granted" else (tokens.ERROR if root.state in ("denied", "error") else tokens.PRIMARY)
            size: dp(44), dp(44)
            pos_hint: {"center_y": .5}

        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: dp(44)
            spacing: dp(1)
            pos_hint: {"center_y": .5}
            MDLabel:
                text: root.title
                font_size: sp(16)
                bold: True
                theme_text_color: "Custom"
                text_color: tokens.TEXT
            MDLabel:
                text: root.message
                font_size: sp(10)
                size_hint_y: None
                height: dp(28)
                text_size: self.width, None
                theme_text_color: "Custom"
                text_color: tokens.MUTED

    MDLabel:
        text: root.detail_line1
        font_size: sp(12)
        bold: True
        size_hint_y: None
        height: dp(18) if root.detail_line1 else 0
        opacity: 1 if root.detail_line1 else 0
        theme_text_color: "Custom"
        text_color: tokens.TEXT

    MDLabel:
        text: root.detail_line2
        font_size: sp(10)
        size_hint_y: None
        height: dp(16) if root.detail_line2 else 0
        opacity: 1 if root.detail_line2 else 0
        theme_text_color: "Custom"
        text_color: tokens.MUTED


<AccessFormCard>:
    orientation: "vertical"
    size_hint_y: None
    padding: dp(16)
    spacing: dp(8)

    MDLabel:
        text: "Register a person"
        font_size: sp(15)
        bold: True
        size_hint_y: None
        height: dp(22)
        theme_text_color: "Custom"
        text_color: tokens.TEXT

    MDLabel:
        text: "Capture one clear, front-facing face. The camera frame is enrolled with the details below."
        font_size: sp(10)
        size_hint_y: None
        height: dp(26)
        text_size: self.width, None
        theme_text_color: "Custom"
        text_color: tokens.MUTED

    MDGridLayout:
        cols: 2 if app.is_wide else 1
        spacing: dp(10)
        size_hint_y: None
        height: dp(112) if app.is_wide else dp(224)

        MDTextField:
            id: acc_name
            hint_text: "Full name *"
            mode: "rectangle"
            font_size: sp(12)
            size_hint_y: None
            height: dp(50)
        MDTextField:
            id: acc_ext_id
            hint_text: "Staff / resident ID"
            mode: "rectangle"
            font_size: sp(12)
            size_hint_y: None
            height: dp(50)
        MDTextField:
            id: acc_role
            hint_text: "Role"
            mode: "rectangle"
            font_size: sp(12)
            size_hint_y: None
            height: dp(50)
        MDTextField:
            id: acc_dept
            hint_text: "Department / zone"
            mode: "rectangle"
            font_size: sp(12)
            size_hint_y: None
            height: dp(50)

    MDTextField:
        id: acc_doors
        hint_text: "Allowed doors (all, or comma separated)"
        text: "all"
        mode: "rectangle"
        font_size: sp(12)
        size_hint_y: None
        height: dp(50)

    MDFillRoundFlatIconButton:
        id: acc_register_btn
        text: "Capture & register face"
        icon: "account-plus"
        font_size: sp(12)
        size_hint_y: None
        height: dp(44)
        disabled: app.access_busy or not app.services_running
        on_release: app.register_access_person(acc_name, acc_ext_id, acc_role, acc_dept, acc_doors)


<AccessEventRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(42)
    spacing: dp(10)
    padding: dp(2), 0

    MDIcon:
        icon: "check-circle" if root.decision == "granted" else ("alert-circle" if root.decision in ("denied", "error") else "information")
        theme_text_color: "Custom"
        text_color: tokens.SUCCESS if root.decision == "granted" else (tokens.ERROR if root.decision in ("denied", "error") else tokens.MUTED)
        font_size: sp(16)
        size_hint: None, None
        size: dp(20), dp(20)
        pos_hint: {"center_y": .5}

    MDBoxLayout:
        orientation: "vertical"
        size_hint_y: None
        height: dp(34)
        spacing: dp(1)
        pos_hint: {"center_y": .5}
        MDLabel:
            text: root.name if root.name else "Unknown face"
            font_size: sp(11)
            bold: True
            theme_text_color: "Custom"
            text_color: tokens.TEXT
        MDLabel:
            text: root.detail
            font_size: sp(9)
            theme_text_color: "Custom"
            text_color: tokens.MUTED
            shorten: True
            shorten_from: "right"
            text_size: self.width, None

    Widget:

    MDLabel:
        text: root.time_text
        font_size: sp(9)
        size_hint_x: None
        width: dp(132)
        halign: "right"
        theme_text_color: "Custom"
        text_color: tokens.MUTED


<AccessBox>:
    orientation: "vertical"
    padding: 0, 0, 0, self.bottom_pad

    MDScrollView:
        id: access_scroll
        do_scroll_x: False
        bar_width: 0

        MDBoxLayout:
            orientation: "vertical"
            adaptive_height: True
            padding: dp(24), dp(18), dp(24), dp(18)
            spacing: dp(14)

            MDBoxLayout:
                size_hint_y: None
                height: dp(44)
                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(44)
                    spacing: 0
                    MDLabel:
                        text: "Door Access"
                        font_size: sp(22)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: tokens.TEXT
                    MDLabel:
                        text: app.door_name + "  -  scan a registered face to unlock"
                        font_size: sp(11)
                        theme_text_color: "Custom"
                        text_color: tokens.MUTED
                Widget:
                StatusPill:
                    text: app.door_controller_label
                    icon: "door-open"
                    bg: tokens.PRIMARY_SOFT
                    fg: tokens.PRIMARY
                    pos_hint: {"center_y": .5}

            MDCard:
                orientation: "horizontal"
                size_hint_y: None
                height: self.minimum_height if not app.services_running else 0
                opacity: 1 if not app.services_running else 0
                disabled: app.services_running
                padding: dp(12), dp(9)
                spacing: dp(10)
                radius: [dp(13)]
                elevation: 0
                md_bg_color: tokens.WARNING_SOFT
                border_color: tokens.TRANSPARENT
                MDIcon:
                    icon: "alert-outline"
                    theme_text_color: "Custom"
                    text_color: tokens.WARNING
                    font_size: sp(16)
                    size_hint: None, None
                    size: dp(18), dp(18)
                    pos_hint: {"center_y": .5}
                MDLabel:
                    text: "The face engine is off. Start it to scan or register."
                    font_size: sp(11)
                    adaptive_height: True
                    text_size: self.width, None
                    theme_text_color: "Custom"
                    text_color: tokens.WARNING
                MDTextButton:
                    text: "START"
                    font_size: sp(10)
                    theme_text_color: "Custom"
                    text_color: tokens.WARNING
                    pos_hint: {"center_y": .5}
                    on_release: app.start_face_services()

            FloatLayout:
                id: access_camera_frame
                size_hint_y: None
                height: dp(368)
                CameraCard:
                    id: access_camera
                    size_hint: None, None
                    size: min(self.parent.width, dp(560)), dp(368)
                    pos_hint: {"center_x": .5, "center_y": .5}

            MDBoxLayout:
                size_hint_y: None
                height: dp(38)
                spacing: dp(8)
                MDFillRoundFlatIconButton:
                    text: "Scan access"
                    icon: "face-recognition"
                    font_size: sp(11)
                    size_hint: None, None
                    size: dp(146), dp(38)
                    md_bg_color: tokens.PRIMARY if app.access_mode == "scan" else tokens.PRIMARY_SOFT
                    theme_text_color: "Custom"
                    text_color: (1, 1, 1, 1) if app.access_mode == "scan" else tokens.PRIMARY
                    theme_icon_color: "Custom"
                    icon_color: (1, 1, 1, 1) if app.access_mode == "scan" else tokens.PRIMARY
                    on_release: app.set_access_mode("scan")
                MDFillRoundFlatIconButton:
                    text: "Register person"
                    icon: "account-plus"
                    font_size: sp(11)
                    size_hint: None, None
                    size: dp(158), dp(38)
                    md_bg_color: tokens.PRIMARY if app.access_mode == "register" else tokens.PRIMARY_SOFT
                    theme_text_color: "Custom"
                    text_color: (1, 1, 1, 1) if app.access_mode == "register" else tokens.PRIMARY
                    theme_icon_color: "Custom"
                    icon_color: (1, 1, 1, 1) if app.access_mode == "register" else tokens.PRIMARY
                    on_release: app.set_access_mode("register")
                Widget:

            AccessResultCard:
                id: access_result
                height: dp(158) if app.access_mode == "scan" else 0
                opacity: 1 if app.access_mode == "scan" else 0
                disabled: app.access_mode != "scan"
                state: app.access_state
                title: app.access_title
                message: app.access_message
                detail_line1: app.access_detail1
                detail_line2: app.access_detail2

            MDFillRoundFlatIconButton:
                text: "Scanning..." if app.access_busy else "Scan & unlock"
                icon: "fingerprint"
                font_size: sp(13)
                size_hint_y: None
                height: dp(46) if app.access_mode == "scan" else 0
                opacity: 1 if app.access_mode == "scan" else 0
                disabled: app.access_busy or not app.services_running
                on_release: app.scan_access()

            AccessFormCard:
                id: access_form
                height: self.minimum_height if app.access_mode == "register" else 0
                opacity: 1 if app.access_mode == "register" else 0
                disabled: app.access_mode != "register"

            MDCard:
                orientation: "horizontal"
                size_hint_y: None
                height: self.minimum_height
                padding: dp(12), dp(9)
                spacing: dp(10)
                radius: [dp(13)]
                elevation: 0
                md_bg_color: tokens.WARNING_SOFT
                border_color: tokens.TRANSPARENT
                MDIcon:
                    icon: "shield-alert-outline"
                    theme_text_color: "Custom"
                    text_color: tokens.WARNING
                    font_size: sp(16)
                    size_hint: None, None
                    size: dp(18), dp(18)
                    pos_hint: {"center_y": .5}
                MDLabel:
                    text: "Pilot security: this is face matching only. A printed photo can spoof it. Add liveness detection and a second factor before connecting a real door."
                    font_size: sp(10)
                    adaptive_height: True
                    text_size: self.width, None
                    theme_text_color: "Custom"
                    text_color: tokens.WARNING

            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(6)
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(26)
                    MDLabel:
                        text: "Recent access"
                        font_size: sp(15)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: tokens.TEXT
                    Widget:
                    MDTextButton:
                        text: "Export log"
                        font_size: sp(11)
                        pos_hint: {"center_y": .5}
                        on_release: app.export_access_log()
                MDBoxLayout:
                    id: access_events_box
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(2)
''')


class AccessResultCard(AppCard):
    state = StringProperty("idle")
    title = StringProperty("Ready to scan")
    message = StringProperty("Look at the camera and press Scan & unlock.")
    detail_line1 = StringProperty("")
    detail_line2 = StringProperty("")


class AccessFormCard(AppCard):
    pass


class AccessEventRow(MDBoxLayout):
    name = StringProperty("")
    detail = StringProperty("")
    decision = StringProperty("")
    time_text = StringProperty("")


class AccessBox(MDBoxLayout):
    top_pad = NumericProperty(0)
    bottom_pad = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if platform == "android":
            try:
                from android.display_cutout import get_height_of_bar

                self.top_pad = int(get_height_of_bar("status"))
                self.bottom_pad = int(get_height_of_bar("navigation"))
            except Exception as e:
                print(f"Failed android 15 padding: {e}")
                self.top_pad = 32
                self.bottom_pad = 48
