from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDFillRoundFlatIconButton
from kivymd.uix.label import MDLabel

from kivy.lang import Builder
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
from kivy.metrics import dp, sp
from kivy.uix.widget import Widget
from kivy.utils import platform

Builder.load_string('''

<ModelDownloder>:
    text: "Downlaod Models"
    icon: "download"
    pos_hint: {'center_x': 0.5}
    size_hint_x: 0.6
    font_size: sp(24)
    on_release: app.start_model_download()


<InitBox>:
    orientation: 'vertical'
    spacing: dp(20)
    padding: 8, 16, 8, self.bottom_pad # left, top, right, bottom

    MDGridLayout: # download section
        cols: 1
        adaptive_height: True
        padding: 0, 8, 0, 0

        MDLabel:
            id: model_check_label
            text: "You need to download the model file first (one time activity). Then you can start the session"
            halign: "center"
            font_size: sp(18)
            #size_hint_x: 0.4
            markup: True
            adaptive_height: True

        MDBoxLayout:
            id: model_btn_box
            orientation: 'vertical'
            #size_hint_x: 0.6

            # the btn to be added here

    Widget:
        size_hint_y: 1

    MDGridLayout: # proceed section
        cols: 2
        spacing: dp(8)

        MDFillRoundFlatIconButton:
            id: start_svc_btn
            text: "Start Services"
            icon: "play"
            pos_hint: {'center_x': 0.5}
            size_hint_x: 0.3
            font_size: sp(18)
            #md_bg_color: 'pink'
            on_release: app.start_face_services()

        MDFillRoundFlatIconButton:
            text: "Proceed"
            icon: "door-open"
            pos_hint: {'center_x': 0.5}
            size_hint_x: 0.7
            font_size: sp(18)
            md_bg_color: 'green'
            on_release: app.goto_face_matcher()

    Widget:
        size_hint_y: 1
''')

class ModelDownloder(MDFillRoundFlatIconButton):
    pass

class StartSvcBtn(MDFillRoundFlatIconButton):
    pass

class InitBox(MDBoxLayout):
    """ Takes configuration inputs """
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
