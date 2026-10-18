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
    StepChip,
    UploadTile,
)


Builder.load_string('''
#:import theme screens.palette.theme
#:import InfoBanner screens.ui.InfoBanner
#:import ResultPane screens.ui.ResultPane
#:import StepChip screens.ui.StepChip
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
                height: dp(52)
                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(52)
                    spacing: 0
                    MDLabel:
                        text: "Face Finder"
                        font_size: sp(28)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: theme.text
                    MDLabel:
                        text: "Compare a source face with a target photo."
                        font_size: sp(12)
                        theme_text_color: "Custom"
                        text_color: theme.muted

            MDBoxLayout:
                size_hint_y: None
                height: dp(34)
                spacing: dp(6)
                StepChip:
                    number: "1"
                    label: "Source"
                    active: app.match_step_index == 1
                StepChip:
                    number: "2"
                    label: "Target"
                    active: app.match_step_index == 2
                StepChip:
                    number: "3"
                    label: "Match"
                    active: app.match_step_index == 3
                StepChip:
                    number: "4"
                    label: "Results"
                    active: app.match_step_index == 4

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
