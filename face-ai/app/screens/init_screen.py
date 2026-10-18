from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty
from kivy.utils import platform

from kivymd.uix.boxlayout import MDBoxLayout

# Local imports (their kv rules are registered here as well).
from screens.ui import (  # noqa: F401
    AppCard,
    EmptyState,
    FeatureChip,
    IconBadge,
    StatusPill,
)


Builder.load_string('''
#:import theme screens.palette.theme
#:import AppCard screens.ui.AppCard
#:import EmptyState screens.ui.EmptyState
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
            spacing: dp(16)
            padding: dp(24), dp(18), dp(24), dp(18)

            # --- page header --------------------------------------------
            MDBoxLayout:
                size_hint_y: None
                height: dp(42)
                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(42)
                    spacing: dp(0)
                    MDLabel:
                        text: "Home"
                        font_size: sp(22)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: theme.text
                    MDLabel:
                        text: "Your private face workspace" if app.is_wide else "Private face workspace"
                        font_size: sp(11)
                        theme_text_color: "Custom"
                        text_color: theme.muted
                StatusPill:
                    text: "Offline"
                    icon: "wifi-off"
                    bg: theme.primary_soft
                    fg: theme.primary_text
                    pos_hint: {"center_y": .5}

            # --- hero ----------------------------------------------------
            MDCard:
                orientation: "vertical"
                size_hint_y: None
                height: dp(154)
                padding: dp(20)
                radius: [dp(22)]
                elevation: 0
                md_bg_color: theme.primary
                border_color: theme.transparent

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(54)
                    spacing: dp(14)
                    MDCard:
                        size_hint: None, None
                        size: dp(52), dp(52)
                        radius: [dp(15)]
                        elevation: 0
                        md_bg_color: theme.white_18
                        border_color: theme.transparent
                        MDIcon:
                            icon: "face-recognition"
                            theme_text_color: "Custom"
                            text_color: theme.text_on_primary
                            font_size: sp(28)
                            pos_hint: {"center_x": .5, "center_y": .5}
                    MDBoxLayout:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(46)
                        spacing: dp(1)
                        pos_hint: {"center_y": .5}
                        MDLabel:
                            text: "Welcome to Face AI"
                            font_size: sp(19)
                            bold: True
                            theme_text_color: "Custom"
                            text_color: theme.text_on_primary
                        MDLabel:
                            text: "Detect, match and unlock - all on this device."
                            font_size: sp(11)
                            theme_text_color: "Custom"
                            text_color: theme.text_on_primary_soft

                Widget:
                    size_hint_y: 1

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(42)
                    spacing: dp(10)
                    MDFillRoundFlatIconButton:
                        text: app.home_action_label
                        icon: app.home_action_icon
                        font_size: sp(12)
                        size_hint: None, None
                        size: dp(196), dp(42)
                        md_bg_color: 1, 1, 1, 1
                        theme_text_color: "Custom"
                        text_color: theme.primary_dark
                        theme_icon_color: "Custom"
                        icon_color: theme.primary_dark
                        disabled: app.download_active
                        on_release: app.home_action()
                    Widget:
                    FeatureChip:
                        text: "100% offline"
                        icon: "wifi-off"
                        width: self.pill_width if app.is_wide else 0
                        opacity: 1 if app.is_wide else 0
                    FeatureChip:
                        text: "Encrypted vault"
                        icon: "shield-lock-outline"
                        width: self.pill_width if app.is_wide else 0
                        opacity: 1 if app.is_wide else 0

            # --- status cards -------------------------------------------
            MDGridLayout:
                cols: 3 if app.is_wide else 1
                spacing: dp(12)
                size_hint_y: None
                height: dp(94) if app.is_wide else dp(306)

                AppCard:
                    orientation: "horizontal"
                    padding: dp(14)
                    spacing: dp(12)
                    IconBadge:
                        icon: "cube-outline"
                        bg: theme.primary_soft
                        fg: theme.primary_text
                        size: dp(38), dp(38)
                        pos_hint: {"center_y": .5}
                    MDBoxLayout:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(42)
                        spacing: dp(1)
                        pos_hint: {"center_y": .5}
                        MDLabel:
                            text: "Models"
                            font_size: sp(11)
                            theme_text_color: "Custom"
                            text_color: theme.muted
                        MDLabel:
                            text: "Ready" if app.models_ready else "Missing"
                            font_size: sp(16)
                            bold: True
                            theme_text_color: "Custom"
                            text_color: theme.success if app.models_ready else theme.warning

                AppCard:
                    orientation: "horizontal"
                    padding: dp(14)
                    spacing: dp(12)
                    IconBadge:
                        icon: "brain"
                        bg: theme.success_soft
                        fg: theme.success
                        size: dp(38), dp(38)
                        pos_hint: {"center_y": .5}
                    MDBoxLayout:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(42)
                        spacing: dp(1)
                        pos_hint: {"center_y": .5}
                        MDLabel:
                            text: "Face engine"
                            font_size: sp(11)
                            theme_text_color: "Custom"
                            text_color: theme.muted
                        MDLabel:
                            text: "Running" if app.services_running else "Stopped"
                            font_size: sp(16)
                            bold: True
                            theme_text_color: "Custom"
                            text_color: theme.success if app.services_running else theme.muted

                AppCard:
                    orientation: "horizontal"
                    padding: dp(14)
                    spacing: dp(12)
                    on_release: app.goto_screen("securityScr")
                    IconBadge:
                        icon: "shield-lock-outline"
                        bg: theme.primary_soft
                        fg: theme.primary_text
                        size: dp(38), dp(38)
                        pos_hint: {"center_y": .5}
                    MDBoxLayout:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(42)
                        spacing: dp(1)
                        pos_hint: {"center_y": .5}
                        MDLabel:
                            text: "Secure vault  -  encrypted at rest"
                            font_size: sp(10)
                            theme_text_color: "Custom"
                            text_color: theme.muted
                        MDLabel:
                            text: "Unlocked" if app.login_success else "Locked"
                            font_size: sp(16)
                            bold: True
                            theme_text_color: "Custom"
                            text_color: theme.success if app.login_success else theme.text
                    MDIcon:
                        icon: "chevron-right"
                        theme_text_color: "Custom"
                        text_color: theme.muted
                        font_size: sp(18)
                        size_hint: None, None
                        size: dp(20), dp(20)
                        pos_hint: {"center_y": .5}

            # --- first-run setup ----------------------------------------
            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height if not app.models_ready else 0
                opacity: 1 if not app.models_ready else 0
                disabled: app.models_ready
                spacing: dp(10)

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(22)
                    MDLabel:
                        text: "First-time setup"
                        font_size: sp(15)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: theme.text
                    Widget:
                    MDLabel:
                        text: "one time"
                        font_size: sp(10)
                        size_hint_x: None
                        width: dp(56)
                        halign: "right"
                        theme_text_color: "Custom"
                        text_color: theme.muted
                MDLabel:
                    text: "Download the ONNX models once (~140 MB), then the face engine starts automatically. Everything runs on this device."
                    font_size: sp(11)
                    size_hint_y: None
                    height: self.texture_size[1]
                    text_size: self.width, None
                    theme_text_color: "Custom"
                    text_color: theme.muted
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(38)
                    spacing: dp(12)
                    MDFillRoundFlatIconButton:
                        text: "Downloading..." if app.download_active else "Download models"
                        icon: "download"
                        font_size: sp(11)
                        size_hint: None, None
                        size: dp(176), dp(38)
                        disabled: app.download_active
                        on_release: app.start_model_download()
                    MDProgressBar:
                        value: app.download_progress_value
                        size_hint_y: None
                        height: dp(6)
                        color: theme.primary
                    MDLabel:
                        text: app.download_status_text
                        font_size: sp(9)
                        size_hint_x: None
                        width: dp(120)
                        halign: "right"
                        theme_text_color: "Custom"
                        text_color: theme.muted

            # --- recent matches -----------------------------------------
            MDBoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(26)
                    MDLabel:
                        text: "Recent matches"
                        font_size: sp(15)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: theme.text
                    Widget:
                    MDTextButton:
                        text: "Open folder"
                        font_size: sp(11)
                        opacity: 1 if app.is_desktop else 0
                        disabled: not app.is_desktop
                        pos_hint: {"center_y": .5}
                        on_release: app.open_outputs_folder()

                MDScrollView:
                    id: recent_scroll
                    do_scroll_x: True
                    do_scroll_y: False
                    bar_width: 0
                    size_hint_y: None
                    height: 0
                    opacity: 0

                    MDBoxLayout:
                        id: recent_grid
                        orientation: "horizontal"
                        size_hint_y: 1
                        size_hint_x: None
                        width: self.minimum_width
                        spacing: dp(10)

                EmptyState:
                    id: recent_empty
                    icon: "image-filter-center-focus"
                    text: "No matches yet"
                    detail: "Generated photos appear here after a Face Finder run."
                    size_hint_y: None
                    height: dp(112)

            # --- privacy -------------------------------------------------
            AppCard:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(64)
                padding: dp(14)
                spacing: dp(12)
                IconBadge:
                    icon: "folder-lock-outline"
                    bg: theme.primary_soft
                    fg: theme.muted
                    size: dp(34), dp(34)
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
                        text_color: theme.text
                    MDLabel:
                        text: "Models, vault and results never leave this device."
                        font_size: sp(10)
                        adaptive_height: True
                        theme_text_color: "Custom"
                        text_color: theme.muted
                Widget:
                MDTextButton:
                    text: "Open data folder"
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
                text_color: theme.muted
''')


class InitBox(MDBoxLayout):
    """Dashboard: setup state, quick actions and recent results."""

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
