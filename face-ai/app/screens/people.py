from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.utils import platform

from kivymd.uix.boxlayout import MDBoxLayout

# Local imports (their kv rules are registered here as well).
from screens.access import AccessEventRow  # noqa: F401
from screens.ui import AppCard, IconBadge, StatusPill  # noqa: F401


Builder.load_string('''
#:import theme screens.palette.theme
#:import AppCard screens.ui.AppCard
#:import IconBadge screens.ui.IconBadge
#:import StatusPill screens.ui.StatusPill
#:import AccessEventRow screens.access.AccessEventRow
#:import TooltipMDIconButton screens.ui.TooltipMDIconButton


<PersonRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(68)
    padding: dp(10)
    spacing: dp(10)
    radius: [dp(14)]
    ripple_behavior: True
    on_release: root.manage_callback() if root.manage_callback else None

    IconBadge:
        icon: "account"
        bg: theme.primary_soft
        fg: theme.primary_text
        size: dp(38), dp(38)
        pos_hint: {"center_y": .5}

    MDBoxLayout:
        orientation: "vertical"
        size_hint_y: None
        height: dp(46)
        spacing: dp(1)
        pos_hint: {"center_y": .5}
        MDLabel:
            text: root.full_name
            font_size: sp(13)
            bold: True
            shorten: True
            shorten_from: "right"
            text_size: self.width, None
            theme_text_color: "Custom"
            text_color: theme.text
        MDLabel:
            text: root.meta
            font_size: sp(9)
            shorten: True
            shorten_from: "right"
            text_size: self.width, None
            theme_text_color: "Custom"
            text_color: theme.muted
        MDLabel:
            text: root.credentials
            font_size: sp(9)
            bold: True
            shorten: True
            shorten_from: "right"
            text_size: self.width, None
            theme_text_color: "Custom"
            text_color: theme.primary_text if root.active else theme.muted

    Widget:
        size_hint_x: None
        width: 0

    StatusPill:
        text: "Active" if root.active else "Suspended"
        icon: "check-circle-outline" if root.active else "minus-circle-outline"
        bg: theme.success_soft if root.active else theme.error_soft
        fg: theme.success if root.active else theme.error
        opacity: 1 if app.is_wide else 0
        disabled: not app.is_wide
        width: self.pill_width if app.is_wide else 0
        size_hint_x: None
        pos_hint: {"center_y": .5}

    TooltipMDIconButton:
        icon: "dots-vertical"
        tooltip_text: "Manage person"
        theme_icon_color: "Custom"
        icon_color: theme.muted
        pos_hint: {"center_y": .5}
        on_release: root.manage_callback() if root.manage_callback else None


<AuditEventRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(40)
    spacing: dp(8)
    padding: dp(2), 0

    MDIcon:
        icon: "shield-check-outline"
        theme_text_color: "Custom"
        text_color: theme.muted
        font_size: sp(14)
        size_hint: None, None
        size: dp(18), dp(18)
        pos_hint: {"center_y": .5}

    MDBoxLayout:
        orientation: "vertical"
        size_hint_y: None
        height: dp(34)
        spacing: 0
        pos_hint: {"center_y": .5}
        MDLabel:
            text: root.action
            font_size: sp(10)
            bold: True
            theme_text_color: "Custom"
            text_color: theme.text
        MDLabel:
            text: root.detail
            font_size: sp(9)
            shorten: True
            shorten_from: "right"
            text_size: self.width, None
            theme_text_color: "Custom"
            text_color: theme.muted

    MDLabel:
        text: root.time_text
        font_size: sp(9)
        size_hint_x: None
        width: dp(62) if app.is_wide else dp(48)
        halign: "right"
        theme_text_color: "Custom"
        text_color: theme.muted


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
                height: dp(58)
                spacing: dp(8)
                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(58)
                    spacing: 0
                    MDLabel:
                        text: "People"
                        font_size: sp(28)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: theme.text
                    MDLabel:
                        text: "Directory, credentials and access policy."
                        font_size: sp(12)
                        theme_text_color: "Custom"
                        text_color: theme.muted
                TooltipMDIconButton:
                    icon: "account-plus-outline"
                    tooltip_text: "Register a person"
                    theme_icon_color: "Custom"
                    icon_color: theme.primary_text
                    pos_hint: {"center_y": .5}
                    on_release: app.open_access_register()
                TooltipMDIconButton:
                    icon: "download-outline"
                    tooltip_text: "Export access log"
                    theme_icon_color: "Custom"
                    icon_color: theme.muted
                    pos_hint: {"center_y": .5}
                    on_release: app.export_access_log()

            MDCard:
                orientation: "horizontal"
                size_hint_y: None
                height: self.minimum_height if app.people_admin_missing else 0
                opacity: 1 if app.people_admin_missing else 0
                disabled: not app.people_admin_missing
                padding: dp(12), dp(9)
                spacing: dp(10)
                radius: [dp(13)]
                elevation: 0
                md_bg_color: theme.warning_soft
                border_color: theme.transparent
                MDIcon:
                    icon: "shield-alert-outline"
                    theme_text_color: "Custom"
                    text_color: theme.warning
                    font_size: sp(16)
                    size_hint: None, None
                    size: dp(18), dp(18)
                    pos_hint: {"center_y": .5}
                MDLabel:
                    text: "No administrator PIN. Set one to manage credentials."
                    font_size: sp(10)
                    adaptive_height: True
                    text_size: self.width, None
                    theme_text_color: "Custom"
                    text_color: theme.warning
                MDTextButton:
                    text: "SET PIN"
                    font_size: sp(9)
                    theme_text_color: "Custom"
                    text_color: theme.warning
                    pos_hint: {"center_y": .5}
                    on_release: app.open_existing_admin_pin()
                MDTextButton:
                    text: "REGISTER"
                    font_size: sp(9)
                    theme_text_color: "Custom"
                    text_color: theme.warning
                    pos_hint: {"center_y": .5}
                    on_release: app.open_admin_register()

            MDTextField:
                id: people_search
                text: app.people_search
                hint_text: "Search people by name, ID, role or department" if app.is_wide else "Search people"
                mode: "rectangle"
                font_size: sp(11)
                size_hint_y: None
                height: dp(42)
                on_text: app.set_people_search(self.text)

            MDBoxLayout:
                size_hint_y: None
                height: dp(32)
                spacing: dp(6)
                MDFillRoundFlatButton:
                    text: "All"
                    font_size: sp(9)
                    size_hint: None, None
                    size: dp(52), dp(30)
                    md_bg_color: theme.primary if app.people_filter == "all" else theme.primary_soft
                    theme_text_color: "Custom"
                    text_color: theme.text_on_primary if app.people_filter == "all" else theme.primary_text
                    on_release: app.set_people_filter("all")
                MDFillRoundFlatButton:
                    text: "Active"
                    font_size: sp(9)
                    size_hint: None, None
                    size: dp(64), dp(30)
                    md_bg_color: theme.primary if app.people_filter == "active" else theme.primary_soft
                    theme_text_color: "Custom"
                    text_color: theme.text_on_primary if app.people_filter == "active" else theme.primary_text
                    on_release: app.set_people_filter("active")
                MDFillRoundFlatButton:
                    text: "Suspended"
                    font_size: sp(9)
                    size_hint: None, None
                    size: dp(86), dp(30)
                    md_bg_color: theme.primary if app.people_filter == "suspended" else theme.primary_soft
                    theme_text_color: "Custom"
                    text_color: theme.text_on_primary if app.people_filter == "suspended" else theme.primary_text
                    on_release: app.set_people_filter("suspended")
                MDFillRoundFlatButton:
                    text: "No face"
                    font_size: sp(9)
                    size_hint: None, None
                    size: dp(74), dp(30)
                    md_bg_color: theme.primary if app.people_filter == "no_face" else theme.primary_soft
                    theme_text_color: "Custom"
                    text_color: theme.text_on_primary if app.people_filter == "no_face" else theme.primary_text
                    on_release: app.set_people_filter("no_face")
                Widget:

            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(4)
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(26)
                    MDLabel:
                        text: "Directory"
                        font_size: sp(16)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: theme.text
                    Widget:
                    MDLabel:
                        text: app.people_count_text
                        font_size: sp(10)
                        halign: "right"
                        size_hint_x: None
                        width: dp(160) if app.is_wide else dp(92)
                        theme_text_color: "Custom"
                        text_color: theme.muted
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
                spacing: dp(4)
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(26)
                    MDLabel:
                        text: "Access log"
                        font_size: sp(16)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: theme.text
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
                    spacing: dp(1)

            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(4)
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(26)
                    MDLabel:
                        text: "Administrative audit"
                        font_size: sp(16)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: theme.text
                    Widget:
                    MDLabel:
                        text: "Credentials and permissions"
                        font_size: sp(9)
                        halign: "right"
                        size_hint_x: None
                        width: dp(150) if app.is_wide else dp(112)
                        theme_text_color: "Custom"
                        text_color: theme.muted
                MDBoxLayout:
                    id: people_audit_box
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(1)
''')


class PersonRow(AppCard):
    full_name = StringProperty("")
    meta = StringProperty("")
    credentials = StringProperty("")
    active = BooleanProperty(True)
    manage_callback = ObjectProperty(None)


class PeopleRow(PersonRow):
    """Backward-compatible alias for existing imports."""


class AuditEventRow(MDBoxLayout):
    action = StringProperty("")
    detail = StringProperty("")
    time_text = StringProperty("")


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
