from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty
from kivy.utils import platform

from kivymd.uix.boxlayout import MDBoxLayout

# Local imports (their kv rules are registered here as well).
from screens.ui import AppCard, SettingsRow  # noqa: F401


Builder.load_string('''
#:import theme screens.palette.theme
#:import AppCard screens.ui.AppCard
#:import SettingsRow screens.ui.SettingsRow


<SettingsBox>:
    orientation: "vertical"
    padding: 0, 0, 0, self.bottom_pad

    MDScrollView:
        id: settings_scroll
        do_scroll_x: False
        scroll_type: ["bars", "content"]
        bar_width: 0

        MDBoxLayout:
            orientation: "vertical"
            adaptive_height: True
            spacing: dp(12)
            padding: dp(20), dp(14), dp(20), dp(14)

            MDLabel:
                text: "Settings & help"
                font_size: sp(20)
                bold: True
                size_hint_y: None
                height: dp(30)
                theme_text_color: "Custom"
                text_color: theme.text
            MDLabel:
                text: "Manage storage, review privacy and reach the developer."
                font_size: sp(11)
                size_hint_y: None
                height: dp(18)
                theme_text_color: "Custom"
                text_color: theme.muted

            # --- storage -------------------------------------------------
            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: dp(10)
                spacing: dp(2)

                MDLabel:
                    text: "STORAGE"
                    font_size: sp(9)
                    bold: True
                    size_hint_y: None
                    height: dp(18)
                    theme_text_color: "Custom"
                    text_color: theme.muted

                SettingsRow:
                    icon: "broom"
                    tint: theme.warning_soft
                    fg: theme.warning
                    title: "Delete generated images"
                    subtitle: app.output_count_label
                    on_release: app.show_all_delete_alert()

                SettingsRow:
                    icon: "folder-open-outline"
                    title: "Open app data folder"
                    subtitle: "Models, vault and generated results"
                    disabled: not app.is_desktop
                    on_release: app.open_data_folder()

            # --- appearance ----------------------------------------------
            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: dp(10)
                spacing: dp(2)

                MDLabel:
                    text: "APPEARANCE"
                    font_size: sp(9)
                    bold: True
                    size_hint_y: None
                    height: dp(18)
                    theme_text_color: "Custom"
                    text_color: theme.muted

                SettingsRow:
                    icon: "weather-night" if not app.theme_dark else "white-balance-sunny"
                    title: "Dark mode"
                    subtitle: app.theme_label + "  -  tap to switch theme"
                    on_release: app.toggle_theme()

                SettingsRow:
                    icon: "animation-outline"
                    title: "Reduce motion"
                    subtitle: app.motion_label + "  -  disable drawer and toast animations"
                    on_release: app.toggle_reduce_motion()

            # --- door access ---------------------------------------------
            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: dp(10)
                spacing: dp(2)

                MDLabel:
                    text: "DOOR ACCESS"
                    font_size: sp(9)
                    bold: True
                    size_hint_y: None
                    height: dp(18)
                    theme_text_color: "Custom"
                    text_color: theme.muted

                SettingsRow:
                    icon: "door-open"
                    tint: theme.primary_soft
                    title: "Door"
                    subtitle: app.door_name + "  -  " + app.door_controller_label
                    chevron: False

                SettingsRow:
                    icon: "file-cog-outline"
                    title: "Door controller config"
                    subtitle: "Edit controller, webhook URL, secret and threshold"
                    on_release: app.open_door_config()

                SettingsRow:
                    icon: "refresh"
                    title: "Reload door config"
                    subtitle: "Apply changes without restarting the app"
                    on_release: app.reload_door_config()

            # --- about ---------------------------------------------------
            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: dp(10)
                spacing: dp(2)

                MDLabel:
                    text: "ABOUT"
                    font_size: sp(9)
                    bold: True
                    size_hint_y: None
                    height: dp(18)
                    theme_text_color: "Custom"
                    text_color: theme.muted

                SettingsRow:
                    icon: "information-outline"
                    title: "Face AI"
                    subtitle: "Version " + app.app_version + " - ONNX runtime"
                    chevron: False

                SettingsRow:
                    icon: "shield-lock-outline"
                    tint: theme.success_soft
                    fg: theme.success
                    title: "Private by default"
                    subtitle: "Detection, matching and the vault run on this device"
                    chevron: False

                SettingsRow:
                    icon: "github"
                    title: "Source code"
                    subtitle: "github.com/daslearning-org/face-ai"
                    on_release: app.open_link(self, "https://github.com/daslearning-org/face-ai")

            # --- help ----------------------------------------------------
            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: dp(10)
                spacing: dp(2)

                MDLabel:
                    text: "HELP & SUPPORT"
                    font_size: sp(9)
                    bold: True
                    size_hint_y: None
                    height: dp(18)
                    theme_text_color: "Custom"
                    text_color: theme.muted

                SettingsRow:
                    icon: "file-document-outline"
                    title: "Documentation"
                    subtitle: "Read the setup guide on the blog"
                    on_release: app.open_link(self, "https://blog.daslearning.in/llm_ai/ml/face-ai.html")

                SettingsRow:
                    icon: "card-account-phone"
                    title: "Contact the developer"
                    subtitle: "Questions, feedback or bug reports"
                    on_release: app.open_link(self, "https://daslearning.in/contact/")

                SettingsRow:
                    icon: "update"
                    title: "Check for update"
                    subtitle: "See the latest release"
                    on_release: app.update_checker(self)

                SettingsRow:
                    icon: "google-play"
                    title: "More apps"
                    subtitle: "Try the other apps from daslearning"
                    on_release: app.open_link(self, "https://daslearning.in/apps/")

                SettingsRow:
                    icon: "lightbulb-on-outline"
                    title: "Show help tips again"
                    subtitle: "Re-enable the inline hints on Face Finder and the vault"
                    on_release: app.reset_tips()

            MDLabel:
                text: "Face AI  -  everything stays on this device"
                font_size: sp(9)
                halign: "center"
                size_hint_y: None
                height: dp(20)
                theme_text_color: "Custom"
                text_color: theme.muted
''')


class SettingsBox(MDBoxLayout):
    """Settings, storage management and help links."""

    top_pad = NumericProperty(0)
    bottom_pad = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "settings_main_bx"
        if platform == "android":
            try:
                from android.display_cutout import get_height_of_bar

                self.top_pad = int(get_height_of_bar("status"))
                self.bottom_pad = int(get_height_of_bar("navigation"))
            except Exception as e:
                print(f"Failed android 15 padding: {e}")
                self.top_pad = 32
                self.bottom_pad = 48
