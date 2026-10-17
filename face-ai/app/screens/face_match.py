from kivy.lang import Builder
from kivy.metrics import dp, sp

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.button import MDFillRoundFlatIconButton
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
from kivy.metrics import dp, sp
from kivy.utils import platform

Builder.load_string('''
#:import parse_color kivy.parser.parse_color
<TempSpinWait>:
    id: temp_spin
    orientation: 'horizontal'
    adaptive_height: True
    padding: dp(8)

    MDLabel:
        text: root.text_to_show
        font_style: "Subtitle1"
        adaptive_width: True

    MDSpinner:
        size_hint: None, None
        size: dp(14), dp(14)
        active: True


<FaceMatchBox>:
    orientation: 'vertical'
    padding: 4, 0, 4, self.bottom_pad # left, top, right, bottom
    spacing: dp(4)

    MDGridLayout: # original image
        cols: 2
        size_hint_y: 0.4
        id: fm_up_box
        spacing: dp(4)
        padding: dp(4)

        MDBoxLayout:
            orientation: 'vertical'
            spacing: dp(4)

            MDFillRoundFlatIconButton:
                id: btn_fm_src_upload
                text: "Source Image"
                icon: "upload"
                font_size: sp(18)
                #md_bg_color: '#333036'
                pos_hint: {"center_x": .5, "center_y": 1}
                #size_hint_x: 0.2
                on_release: app.open_img_file_manager("btn_fm_src_upload")

            MDBoxLayout:
                id: fm_up_src_box
                canvas.before:
                    Color:
                        rgb: parse_color('#c0d9bd')
                    RoundedRectangle:
                        size: self.width, self.height
                        pos: self.pos
                        radius: [0, 20, 20, 20] # clockwise from top-left
                # add fit image here for source image

        MDBoxLayout:
            orientation: 'vertical'
            spacing: dp(4)

            MDFillRoundFlatIconButton:
                id: btn_fm_tgt_upload
                text: "Target Image"
                icon: "upload"
                font_size: sp(18)
                #md_bg_color: '#333036'
                pos_hint: {"center_x": .5, "center_y": 1}
                #size_hint_x: 0.2
                on_release: app.open_img_file_manager("btn_fm_tgt_upload")

            MDBoxLayout:
                id: fm_up_trgt_box
                canvas.before:
                    Color:
                        rgb: parse_color('#c0d9bd')
                    RoundedRectangle:
                        size: self.width, self.height
                        pos: self.pos
                        radius: [20, 0, 20, 20] # clockwise from top-left
                # add fit image here for source image

    MDGridLayout: # action buttons
        cols: 3
        size_hint_y: 0.1
        spacing: dp(4)
        padding: 14, 4, 14, 4 # left, top, right, bottom

        MDFillRoundFlatIconButton:
            id: btn_submit
            text: "Detect"
            icon: "send"
            font_size: sp(18)
            md_bg_color: 'orange'
            pos_hint: {"center_x": .5, "center_y": .5}
            size_hint_x: 0.6
            on_release: app.submit_face_match()

        MDFillRoundFlatIconButton:
            id: btn_reset
            text: "Reset"
            icon: "undo-variant"
            font_size: sp(18)
            md_bg_color: '#333036'
            pos_hint: {"center_x": .5, "center_y": .5}
            size_hint_x: 0.4
            on_release: app.reset_face_matcher()

    MDGridLayout: # generated images
        cols: 2
        size_hint_y: 0.5
        id: fm_gen_box
        spacing: dp(4)
        padding: 0, 0, 0, 4

        MDBoxLayout:
            id: fm_gen_src_box
            orientation: 'vertical'
            canvas.before:
                Color:
                    rgb: parse_color('#abdbf5')
                RoundedRectangle:
                    size: self.width, self.height
                    pos: self.pos
                    radius: [20, 20, 20, 0] # clockwise from top-left
            # add fit image here for source image

        MDBoxLayout:
            id: fm_gen_trgt_box
            orientation: 'vertical'
            canvas.before:
                Color:
                    rgb: parse_color('#abdbf5')
                RoundedRectangle:
                    size: self.width, self.height
                    pos: self.pos
                    radius: [20, 20, 0, 20] # clockwise from top-left
            # add fit image here for target image


''')

class TempSpinWait(MDBoxLayout):
    text_to_show = StringProperty("Please wait...")

class FaceMatchBox(MDBoxLayout):
    top_pad = NumericProperty(0)
    bottom_pad = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "face_matcher_box"
        if platform == "android":
            try:
                from android.display_cutout import get_height_of_bar
                self.top_pad = int(get_height_of_bar('status'))
                self.bottom_pad = int(get_height_of_bar('navigation'))
            except Exception as e:
                print(f"Failed android 15 padding: {e}")
                self.top_pad = 32
                self.bottom_pad = 48
