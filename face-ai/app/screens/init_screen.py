from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty
from kivy.utils import platform

from kivymd.uix.boxlayout import MDBoxLayout

# Local imports (their kv rules are registered here as well).
from screens.ui import (  # noqa: F401
    AppCard,
    EmptyState,
    IconBadge,
    QuickAction,
    StatusPill,
)


Builder.load_string('''
#:import theme screens.palette.theme
#:import AppCard screens.ui.AppCard
#:import EmptyState screens.ui.EmptyState
#:import IconBadge screens.ui.IconBadge
#:import QuickAction screens.ui.QuickAction
#:import StatusPill screens.ui.StatusPill
#:import TooltipMDIconButton screens.ui.TooltipMDIconButton


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
            spacing: dp(18)
            padding: dp(24), dp(18), dp(24), dp(18)

            # --- page header --------------------------------------------
            MDBoxLayout:
                size_hint_y: None
                height: dp(48)
                spacing: dp(8)
                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(48)
                    spacing: 0
                    MDLabel:
                        text: "Home"
                        font_size: sp(28)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: theme.text
                    MDLabel:
                        text: "Your private face workspace" if app.is_wide else "Private face workspace"
                        font_size: sp(12)
                        theme_text_color: "Custom"
                        text_color: theme.muted
                StatusPill:
                    text: "Offline"
                    icon: "wifi-off"
                    bg: theme.primary_soft
                    fg: theme.primary_text
                    pos_hint: {"center_y": .5}

            # --- first-run setup ----------------------------------------
            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height if not app.models_ready else 0
                opacity: 1 if not app.models_ready else 0
                disabled: app.models_ready
                padding: dp(18)
                spacing: dp(10)

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(22)
                    MDLabel:
                        text: "First-time setup"
                        font_size: sp(16)
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

            # --- engine command card ------------------------------------
            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: dp(290) if app.is_wide else dp(346)
                padding: dp(22)
                spacing: dp(10)

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(42)
                    spacing: dp(12)
                    IconBadge:
                        icon: "face-recognition"
                        bg: theme.primary_soft
                        fg: theme.primary_text
                        size: dp(42), dp(42)
                        pos_hint: {"center_y": .5}
                    MDBoxLayout:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(40)
                        spacing: dp(1)
                        pos_hint: {"center_y": .5}
                        MDLabel:
                            text: "Face engine"
                            font_size: sp(13)
                            bold: True
                            theme_text_color: "Custom"
                            text_color: theme.text
                        MDLabel:
                            text: "On-device matching"
                            font_size: sp(10)
                            theme_text_color: "Custom"
                            text_color: theme.muted
                    Widget:
                    StatusPill:
                        text: "Running" if app.services_running else "Off"
                        icon: "check-circle-outline" if app.services_running else "power"
                        bg: theme.success_soft if app.services_running else theme.surface
                        fg: theme.success if app.services_running else theme.muted
                        opacity: 1 if app.is_wide else 0
                        width: self.pill_width if app.is_wide else 0
                        size_hint_x: None
                        pos_hint: {"center_y": .5}

                MDLabel:
                    text: ("Ready for a local match" if app.services_running else ("Set up local recognition" if not app.models_ready else "Start your face engine"))
                    font_size: sp(24) if app.is_wide else sp(21)
                    bold: True
                    size_hint_y: None
                    height: dp(32)
                    theme_text_color: "Custom"
                    text_color: theme.text

                MDLabel:
                    text: "Detect, match and unlock without sending a frame off this device."
                    font_size: sp(12)
                    size_hint_y: None
                    height: dp(34)
                    text_size: self.width, None
                    theme_text_color: "Custom"
                    text_color: theme.muted

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(42)
                    spacing: dp(10)
                    MDFillRoundFlatIconButton:
                        text: app.home_action_label
                        icon: app.home_action_icon
                        font_size: sp(12)
                        size_hint: None, None
                        size: dp(204), dp(42)
                        disabled: app.download_active
                        on_release: app.home_action()
                    TooltipMDIconButton:
                        tooltip_text: "Stop face engine"
                        icon: "stop-circle-outline"
                        size_hint: None, None
                        size: dp(42), dp(42)
                        theme_icon_color: "Custom"
                        icon_color: theme.error
                        md_bg_color: theme.error_soft
                        opacity: 1 if app.services_running else 0
                        disabled: not app.services_running
                        width: dp(42) if app.services_running else 0
                        on_release: app.stop_face_services()
                    MDFillRoundFlatIconButton:
                        text: "Open vault"
                        icon: "shield-lock-outline"
                        font_size: sp(12)
                        size_hint: None, None
                        size: dp(150), dp(42)
                        md_bg_color: theme.primary_soft
                        theme_text_color: "Custom"
                        text_color: theme.primary_text
                        theme_icon_color: "Custom"
                        icon_color: theme.primary_text
                        opacity: 1 if app.is_wide else 0
                        disabled: not app.is_wide
                        width: dp(150) if app.is_wide else 0
                        on_release: app.goto_screen("securityScr")
                    Widget:

                MDGridLayout:
                    cols: 4 if app.is_wide else 2
                    spacing: dp(8)
                    size_hint_y: None
                    height: dp(44) if app.is_wide else dp(84)

                    MDBoxLayout:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(36)
                        spacing: 0
                        pos_hint: {"center_y": .5}
                        MDLabel:
                            text: "MODELS"
                            font_size: sp(8)
                            bold: True
                            theme_text_color: "Custom"
                            text_color: theme.muted
                        MDLabel:
                            text: "Ready" if app.models_ready else "Missing"
                            font_size: sp(12)
                            bold: True
                            theme_text_color: "Custom"
                            text_color: theme.success if app.models_ready else theme.warning

                    MDBoxLayout:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(36)
                        spacing: 0
                        pos_hint: {"center_y": .5}
                        MDLabel:
                            text: "ENGINE"
                            font_size: sp(8)
                            bold: True
                            theme_text_color: "Custom"
                            text_color: theme.muted
                        MDLabel:
                            text: "Running" if app.services_running else "Stopped"
                            font_size: sp(12)
                            bold: True
                            theme_text_color: "Custom"
                            text_color: theme.success if app.services_running else theme.muted

                    MDBoxLayout:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(36)
                        spacing: 0
                        pos_hint: {"center_y": .5}
                        MDLabel:
                            text: "VAULT"
                            font_size: sp(8)
                            bold: True
                            theme_text_color: "Custom"
                            text_color: theme.muted
                        MDLabel:
                            text: "Unlocked" if app.login_success else "Locked"
                            font_size: sp(12)
                            bold: True
                            theme_text_color: "Custom"
                            text_color: theme.success if app.login_success else theme.text

                    MDBoxLayout:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(36)
                        spacing: 0
                        pos_hint: {"center_y": .5}
                        MDLabel:
                            text: "DATA"
                            font_size: sp(8)
                            bold: True
                            theme_text_color: "Custom"
                            text_color: theme.muted
                        MDLabel:
                            text: "On device"
                            font_size: sp(12)
                            bold: True
                            theme_text_color: "Custom"
                            text_color: theme.text

            # --- quick actions ------------------------------------------
            MDBoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(10)
                MDLabel:
                    text: "Quick actions"
                    font_size: sp(16)
                    bold: True
                    size_hint_y: None
                    height: dp(24)
                    theme_text_color: "Custom"
                    text_color: theme.text
                MDGridLayout:
                    cols: 4 if app.is_wide else (2 if Window.width >= 360 else 1)
                    spacing: dp(10)
                    size_hint_y: None
                    height: dp(100) if app.is_wide else (dp(210) if Window.width >= 360 else dp(430))
                    QuickAction:
                        icon: "account-search-outline"
                        title: "Face Finder"
                        subtitle: "Match two photos"
                        on_release: app.goto_screen("faceFindScr")
                    QuickAction:
                        icon: "shield-lock-outline"
                        title: "Secure Vault"
                        subtitle: "Encrypted files"
                        on_release: app.goto_screen("securityScr")
                    QuickAction:
                        icon: "door-open"
                        title: "Door Access"
                        subtitle: "Scan to unlock"
                        tint: theme.success_soft
                        fg: theme.success
                        on_release: app.goto_screen("accessScr")
                    QuickAction:
                        icon: "account-group-outline"
                        title: "People"
                        subtitle: "Registry and audit"
                        tint: theme.warning_soft
                        fg: theme.warning
                        on_release: app.goto_screen("peopleScr")

            # --- recent matches -----------------------------------------
            MDBoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(28)
                    MDLabel:
                        text: "Recent matches"
                        font_size: sp(16)
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
                    fg: theme.primary_text
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
