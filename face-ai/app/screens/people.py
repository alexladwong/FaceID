from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.utils import platform

from kivymd.uix.boxlayout import MDBoxLayout

# Local imports (their kv rules are registered here as well).
from screens.ui import AppCard, IconBadge, StatusPill  # noqa: F401


Builder.load_string('''
#:import tokens screens.tokens
#:import AppCard screens.ui.AppCard
#:import IconBadge screens.ui.IconBadge
#:import StatusPill screens.ui.StatusPill


<PeopleRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(58)
    spacing: dp(10)
    padding: dp(2), 0

    IconBadge:
        icon: "account"
        bg: tokens.PRIMARY_SOFT
        fg: tokens.PRIMARY
        size: dp(36), dp(36)
        pos_hint: {"center_y": .5}

    MDBoxLayout:
        orientation: "vertical"
        size_hint_y: None
        height: dp(38)
        spacing: dp(1)
        pos_hint: {"center_y": .5}
        MDLabel:
            text: root.full_name
            font_size: sp(12)
            bold: True
            theme_text_color: "Custom"
            text_color: tokens.TEXT
        MDLabel:
            text: root.meta
            font_size: sp(9)
            theme_text_color: "Custom"
            text_color: tokens.MUTED
            shorten: True
            shorten_from: "right"
            text_size: self.width, None

    Widget:

    StatusPill:
        text: "Active" if root.active else "Inactive"
        icon: "check-circle-outline" if root.active else "minus-circle-outline"
        bg: tokens.SUCCESS_SOFT if root.active else "#F1F3F9"
        fg: tokens.SUCCESS if root.active else tokens.MUTED
        pos_hint: {"center_y": .5}

    MDIconButton:
        icon: "trash-can-outline"
        theme_icon_color: "Custom"
        icon_color: tokens.MUTED
        pos_hint: {"center_y": .5}
        on_release: root.delete_callback() if root.delete_callback else None


<PeopleBox>:
    orientation: "vertical"
    padding: 0, 0, 0, self.bottom_pad

    MDScrollView:
        id: people_scroll
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
                spacing: dp(8)
                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(44)
                    spacing: 0
                    MDLabel:
                        text: "People"
                        font_size: sp(22)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: tokens.TEXT
                    MDLabel:
                        text: "Registry, door permissions and the access audit trail."
                        font_size: sp(11)
                        theme_text_color: "Custom"
                        text_color: tokens.MUTED
                Widget:
                MDTextButton:
                    text: "Register someone"
                    font_size: sp(11)
                    size_hint_x: None
                    width: dp(128)
                    pos_hint: {"center_y": .5}
                    on_release: app.open_access_register()
                MDTextButton:
                    text: "Export log"
                    font_size: sp(11)
                    size_hint_x: None
                    width: dp(90)
                    pos_hint: {"center_y": .5}
                    on_release: app.export_access_log()

            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(6)
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(26)
                    MDLabel:
                        text: "Registered people"
                        font_size: sp(15)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: tokens.TEXT
                    Widget:
                    MDLabel:
                        text: app.people_count_text
                        font_size: sp(10)
                        halign: "right"
                        size_hint_x: None
                        width: dp(190)
                        theme_text_color: "Custom"
                        text_color: tokens.MUTED
                MDBoxLayout:
                    id: people_registry_box
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(2)

            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(6)
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(26)
                    MDLabel:
                        text: "Access log"
                        font_size: sp(15)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: tokens.TEXT
                    Widget:
                    MDTextButton:
                        text: "Export CSV"
                        font_size: sp(10)
                        pos_hint: {"center_y": .5}
                        on_release: app.export_access_log()
                MDBoxLayout:
                    id: people_log_box
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(2)
''')


class PeopleRow(MDBoxLayout):
    full_name = StringProperty("")
    meta = StringProperty("")
    active = BooleanProperty(True)
    delete_callback = ObjectProperty(None)


class PeopleBox(MDBoxLayout):
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
