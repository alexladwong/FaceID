from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty
from kivy.utils import platform

from kivymd.uix.boxlayout import MDBoxLayout

# Local imports (their kv rules are registered here as well).
from screens.ui import AppCard, FeatureChip, IconBadge, StatusPill  # noqa: F401


Builder.load_string('''
#:import tokens screens.tokens
#:import AppCard screens.ui.AppCard
#:import FeatureChip screens.ui.FeatureChip
#:import IconBadge screens.ui.IconBadge
#:import StatusPill screens.ui.StatusPill


<InitBox>:
    orientation: "vertical"
    padding: 0, 0, 0, self.bottom_pad

    MDScrollView:
        id: init_scroll
        do_scroll_x: False
        scroll_type: ["bars", "content"]
        bar_width: 0

        MDBoxLayout:
            orientation: "vertical"
            adaptive_height: True
            spacing: dp(12)
            padding: dp(20), dp(14), dp(20), dp(14)

            # --- brand hero ---------------------------------------------
            MDCard:
                orientation: "vertical"
                size_hint_y: None
                height: dp(176)
                padding: dp(18)
                radius: [dp(22)]
                elevation: 0
                md_bg_color: tokens.PRIMARY
                border_color: tokens.TRANSPARENT

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(56)
                    spacing: dp(14)

                    MDCard:
                        size_hint: None, None
                        size: dp(56), dp(56)
                        radius: [dp(16)]
                        elevation: 0
                        md_bg_color: tokens.WHITE_18
                        border_color: tokens.TRANSPARENT
                        MDIcon:
                            icon: "face-recognition"
                            theme_text_color: "Custom"
                            text_color: tokens.ON_PRIMARY
                            font_size: sp(30)
                            pos_hint: {"center_x": .5, "center_y": .5}

                    MDBoxLayout:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(46)
                        spacing: dp(1)
                        pos_hint: {"center_y": .5}

                        MDLabel:
                            text: "Welcome to Face AI"
                            font_size: sp(20)
                            bold: True
                            theme_text_color: "Custom"
                            text_color: tokens.ON_PRIMARY
                        MDLabel:
                            text: "Detect, match and unlock - fully offline."
                            font_size: sp(11)
                            theme_text_color: "Custom"
                            text_color: tokens.ON_PRIMARY_SOFT

                Widget:
                    size_hint_y: 1

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(26)
                    spacing: dp(6)

                    FeatureChip:
                        text: "100% offline"
                        icon: "wifi-off"
                    FeatureChip:
                        text: "On-device AI"
                        icon: "chip"
                    FeatureChip:
                        text: "Encrypted vault"
                        icon: "shield-lock-outline"
                    Widget:

            # --- setup steps --------------------------------------------
            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(10)

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(22)

                    MDLabel:
                        text: "Get started"
                        font_size: sp(15)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: tokens.TEXT
                    Widget:
                    MDLabel:
                        text: "2 steps"
                        font_size: sp(10)
                        halign: "right"
                        size_hint_x: None
                        width: dp(52)
                        theme_text_color: "Custom"
                        text_color: tokens.MUTED

                # Step 1 - models
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(54)
                    spacing: dp(12)

                    IconBadge:
                        icon: "cube-outline"
                        bg: tokens.PRIMARY_SOFT
                        fg: tokens.PRIMARY
                        size: dp(40), dp(40)
                        pos_hint: {"center_y": .5}

                    MDBoxLayout:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(36)
                        spacing: dp(1)
                        pos_hint: {"center_y": .5}
                        MDLabel:
                            text: "Model files"
                            font_size: sp(13)
                            bold: True
                            adaptive_height: True
                            theme_text_color: "Custom"
                            text_color: tokens.TEXT
                        MDLabel:
                            text: "One-time download - about 140 MB"
                            font_size: sp(10)
                            adaptive_height: True
                            theme_text_color: "Custom"
                            text_color: tokens.MUTED

                    Widget:

                    FloatLayout:
                        size_hint: None, 1
                        size: dp(124), 1
                        MDFillRoundFlatButton:
                            text: "Download"
                            font_size: sp(11)
                            size_hint: None, None
                            size: dp(112), dp(36)
                            pos_hint: {"center_x": .5, "center_y": .5}
                            opacity: 0 if app.models_ready else 1
                            disabled: app.models_ready or app.download_active
                            on_release: app.start_model_download()
                        StatusPill:
                            text: "Ready"
                            icon: "check-circle-outline"
                            bg: tokens.SUCCESS_SOFT
                            fg: tokens.SUCCESS
                            opacity: 1 if app.models_ready else 0
                            disabled: not app.models_ready
                            pos_hint: {"center_x": .5, "center_y": .5}

                # download progress
                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(34) if app.download_active else 0
                    opacity: 1 if app.download_active else 0
                    spacing: dp(3)

                    MDProgressBar:
                        value: app.download_progress_value
                        size_hint_y: None
                        height: dp(6)
                        color: tokens.PRIMARY
                    MDLabel:
                        text: app.download_status_text
                        font_size: sp(9)
                        theme_text_color: "Custom"
                        text_color: tokens.MUTED

                # Step 2 - engine
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(54)
                    spacing: dp(12)

                    IconBadge:
                        icon: "brain"
                        bg: tokens.SUCCESS_SOFT
                        fg: tokens.SUCCESS
                        size: dp(40), dp(40)
                        pos_hint: {"center_y": .5}

                    MDBoxLayout:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(36)
                        spacing: dp(1)
                        pos_hint: {"center_y": .5}
                        MDLabel:
                            text: "Face engine"
                            font_size: sp(13)
                            bold: True
                            adaptive_height: True
                            theme_text_color: "Custom"
                            text_color: tokens.TEXT
                        MDLabel:
                            text: "Runs detection and matching on this device"
                            font_size: sp(10)
                            adaptive_height: True
                            theme_text_color: "Custom"
                            text_color: tokens.MUTED

                    Widget:

                    FloatLayout:
                        size_hint: None, 1
                        size: dp(124), 1
                        MDFillRoundFlatButton:
                            text: "Start"
                            font_size: sp(11)
                            size_hint: None, None
                            size: dp(112), dp(36)
                            pos_hint: {"center_x": .5, "center_y": .5}
                            opacity: 0 if app.services_running else 1
                            disabled: app.services_running or not app.models_ready
                            on_release: app.start_face_services()
                        StatusPill:
                            text: "Running"
                            icon: "play-circle-outline"
                            bg: tokens.SUCCESS_SOFT
                            fg: tokens.SUCCESS
                            opacity: 1 if app.services_running else 0
                            disabled: not app.services_running
                            pos_hint: {"center_x": .5, "center_y": .5}

                MDLabel:
                    text: "Start the engine to unlock matching and the vault." if not app.services_running else "Ready. Open Face Finder or the vault from the menu."
                    font_size: sp(10)
                    halign: "center"
                    text_size: self.width, None
                    size_hint_y: None
                    height: self.texture_size[1]
                    theme_text_color: "Custom"
                    text_color: tokens.MUTED

                MDFillRoundFlatIconButton:
                    text: "Continue to Face Finder"
                    icon: "arrow-right"
                    font_size: sp(13)
                    size_hint_y: None
                    height: dp(46)
                    disabled: not app.services_running
                    on_release: app.goto_face_matcher()

            # --- where data lives ---------------------------------------
            AppCard:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(64)
                padding: dp(14)
                spacing: dp(12)

                IconBadge:
                    icon: "folder-lock-outline"
                    bg: "#F1F3F9"
                    fg: tokens.MUTED
                    size: dp(36), dp(36)
                    pos_hint: {"center_y": .5}

                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(34)
                    spacing: dp(1)
                    pos_hint: {"center_y": .5}
                    MDLabel:
                        text: "Private by default"
                        font_size: sp(12)
                        bold: True
                        adaptive_height: True
                        theme_text_color: "Custom"
                        text_color: tokens.TEXT
                    MDLabel:
                        text: "Models, vault and results never leave this device."
                        font_size: sp(10)
                        adaptive_height: True
                        theme_text_color: "Custom"
                        text_color: tokens.MUTED

                Widget:

                MDTextButton:
                    text: "Open folder"
                    font_size: sp(10)
                    opacity: 1 if app.is_desktop else 0
                    disabled: not app.is_desktop
                    pos_hint: {"center_y": .5}
                    on_release: app.open_data_folder()

            MDLabel:
                text: "Face AI  -  version " + app.app_version
                font_size: sp(9)
                halign: "center"
                size_hint_y: None
                height: dp(16)
                theme_text_color: "Custom"
                text_color: tokens.MUTED
''')


class InitBox(MDBoxLayout):
    """Home screen: first-run setup and a shortcut into the app."""

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
