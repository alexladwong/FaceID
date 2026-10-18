from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty
from kivy.utils import platform

from kivymd.uix.boxlayout import MDBoxLayout

# Local imports (their kv rules are registered here as well).
from screens.ui import (  # noqa: F401
    BusyState,
    EmptyState,
    InfoBanner,
    ResultPane,
    UploadTile,
)


Builder.load_string('''
#:import theme screens.palette.theme
#:import InfoBanner screens.ui.InfoBanner
#:import ResultPane screens.ui.ResultPane
#:import UploadTile screens.ui.UploadTile


<FaceMatchBox>:
    orientation: "vertical"
    padding: 0, 0, 0, self.bottom_pad

    MDScrollView:
        id: fm_scroll
        do_scroll_x: False
        scroll_type: ["bars", "content"]
        bar_width: 0

        MDBoxLayout:
            orientation: "vertical"
            adaptive_height: True
            spacing: dp(12)
            padding: dp(24), dp(18), dp(24), dp(18)

            # page header
            MDBoxLayout:
                size_hint_y: None
                height: dp(44)
                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(44)
                    spacing: 0
                    MDLabel:
                        text: "Face Finder"
                        font_size: sp(22)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: theme.text
                    MDLabel:
                        text: "Compare a source face with a target photo."
                        font_size: sp(11)
                        theme_text_color: "Custom"
                        text_color: theme.muted
                StatusPill:
                    text: "Engine ready" if app.services_running else "Engine off"
                    icon: "check-circle-outline" if app.services_running else "alert-circle-outline"
                    bg: theme.success_soft if app.services_running else theme.warning_soft
                    fg: theme.success if app.services_running else theme.warning
                    opacity: 1 if app.is_wide else 0
                    disabled: not app.is_wide
                    width: self.pill_width if app.is_wide else 0
                    size_hint_x: None
                    pos_hint: {"center_y": .5}

            MDBoxLayout:
                size_hint_y: None
                height: dp(30)
                MDLabel:
                    text: app.match_step_text
                    font_size: sp(11)
                    bold: True
                    theme_text_color: "Custom"
                    text_color: theme.primary_text
                Widget:
                MDBoxLayout:
                    size_hint_x: None
                    width: dp(116)
                    spacing: dp(5)
                    MDIcon:
                        icon: "circle"
                        font_size: sp(8)
                        theme_text_color: "Custom"
                        text_color: theme.success if app.services_running else theme.muted
                        size_hint: None, None
                        size: dp(10), dp(10)
                        pos_hint: {"center_y": .5}
                    MDLabel:
                        text: "Engine running" if app.services_running else "Engine off"
                        font_size: sp(9)
                        theme_text_color: "Custom"
                        text_color: theme.success if app.services_running else theme.muted

            # engine warning
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
                md_bg_color: theme.warning_soft
                border_color: theme.transparent

                MDIcon:
                    icon: "alert-outline"
                    theme_text_color: "Custom"
                    text_color: theme.warning
                    font_size: sp(16)
                    size_hint: None, None
                    size: dp(18), dp(18)
                    pos_hint: {"center_y": .5}
                MDLabel:
                    text: "The face engine is off. Start it to run matches."
                    font_size: sp(11)
                    adaptive_height: True
                    text_size: self.width, None
                    theme_text_color: "Custom"
                    text_color: theme.warning
                MDTextButton:
                    text: "START"
                    font_size: sp(10)
                    theme_text_color: "Custom"
                    text_color: theme.warning
                    pos_hint: {"center_y": .5}
                    on_release: app.start_face_services()

            InfoBanner:
                text: "Pick one clear, front-facing face as the source, then any photo with faces as the target." + (" You can also drag and drop image files here." if app.is_desktop else "")
                opacity: 1 if app.face_tip_visible else 0
                height: self.minimum_height if app.face_tip_visible else 0
                disabled: not app.face_tip_visible
                close_callback: app.dismiss_face_tip

            # pickers
            MDGridLayout:
                cols: 2 if app.is_wide else 1
                rows: 1 if app.is_wide else 2
                spacing: dp(12)
                size_hint_y: None
                height: dp(224) if app.is_wide else dp(460)

                UploadTile:
                    id: fm_src_tile
                    purpose: "src"
                    title: "Source face"
                    subtitle: "One clear face"
                    icon_name: "account-outline"
                    disabled: app.is_onnx_running
                    on_release: app.open_img_file_manager("src")

                UploadTile:
                    id: fm_trgt_tile
                    purpose: "trgt"
                    title: "Target photo"
                    subtitle: "One or more faces"
                    icon_name: "account-group-outline"
                    disabled: app.is_onnx_running
                    on_release: app.open_img_file_manager("trgt")

            # actions
            MDBoxLayout:
                size_hint_y: None
                height: dp(46)
                spacing: dp(10)

                MDFillRoundFlatIconButton:
                    id: btn_submit
                    text: "Matching..." if app.is_onnx_running else "Find matches"
                    icon: "progress-clock" if app.is_onnx_running else "magnify"
                    font_size: sp(13)
                    size_hint_x: .64
                    disabled: app.is_onnx_running or not app.ready_to_match
                    on_release: app.submit_face_match()

                MDRoundFlatButton:
                    id: btn_reset
                    text: "Cancel" if app.is_onnx_running else "Reset"
                    font_size: sp(13)
                    size_hint_x: .36
                    theme_text_color: "Custom"
                    text_color: theme.error if app.is_onnx_running else theme.text
                    on_release: app.cancel_face_match() if app.is_onnx_running else app.reset_face_matcher()

            # results
            MDBoxLayout:
                orientation: "horizontal" if app.is_wide else "vertical"
                size_hint_y: None
                height: dp(232) if app.is_wide else dp(476)
                spacing: dp(12)

                ResultPane:
                    id: fm_gen_src_pane
                    title: "Source - matched face"

                ResultPane:
                    id: fm_gen_trgt_pane
                    title: "Target - detections"
''')


class FaceMatchBox(MDBoxLayout):
    """Face Finder: choose a source face and a target photo, then match."""

    top_pad = NumericProperty(0)
    bottom_pad = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "face_matcher_box"
        if platform == "android":
            try:
                from android.display_cutout import get_height_of_bar

                self.top_pad = int(get_height_of_bar("status"))
                self.bottom_pad = int(get_height_of_bar("navigation"))
            except Exception as e:
                print(f"Failed android 15 padding: {e}")
                self.top_pad = 32
                self.bottom_pad = 48
