from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, StringProperty
from kivy.utils import platform

from kivymd.uix.boxlayout import MDBoxLayout

# Local imports (their kv rules are registered here as well).
from screens.security import CameraCard  # noqa: F401
from screens.ui import (  # noqa: F401
    AppCard,
    IconBadge,
    StatusPill,
)


Builder.load_string('''
#:import theme screens.palette.theme
#:import AppCard screens.ui.AppCard
#:import CameraCard screens.security.CameraCard
#:import IconBadge screens.ui.IconBadge
#:import StatusPill screens.ui.StatusPill
#:import TooltipMDIconButton screens.ui.TooltipMDIconButton


<AccessResultCard>:
    orientation: "vertical"
    size_hint_y: None
    height: dp(118)
    padding: dp(14)
    spacing: dp(4)

    MDBoxLayout:
        size_hint_y: None
        height: dp(42)
        spacing: dp(10)
        IconBadge:
            icon: "account-check-outline" if root.state == "granted" else ("alert-circle-outline" if root.state in ("denied", "error", "unavailable") else ("shield-key-outline" if root.state == "challenge" else "face-recognition"))
            bg: theme.success_soft if root.state == "granted" else (theme.error_soft if root.state in ("denied", "error", "unavailable") else theme.primary_soft)
            fg: theme.success if root.state == "granted" else (theme.error if root.state in ("denied", "error", "unavailable") else theme.primary_text)
            size: dp(40), dp(40)
            pos_hint: {"center_y": .5}
        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: dp(40)
            spacing: 0
            pos_hint: {"center_y": .5}
            MDLabel:
                text: root.title
                font_size: sp(16)
                bold: True
                theme_text_color: "Custom"
                text_color: theme.text
            MDLabel:
                text: root.message
                font_size: sp(10)
                shorten: True
                shorten_from: "right"
                text_size: self.width, None
                theme_text_color: "Custom"
                text_color: theme.muted

    MDLabel:
        text: root.detail_line1
        font_size: sp(12)
        bold: True
        size_hint_y: None
        height: dp(18) if root.detail_line1 else 0
        opacity: 1 if root.detail_line1 else 0
        theme_text_color: "Custom"
        text_color: theme.text

    MDLabel:
        text: root.detail_line2
        font_size: sp(10)
        size_hint_y: None
        height: dp(16) if root.detail_line2 else 0
        opacity: 1 if root.detail_line2 else 0
        theme_text_color: "Custom"
        text_color: theme.muted

    Widget:
        size_hint_y: 1


<AccessEventRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(46)
    spacing: dp(8)
    padding: dp(2), 0

    MDIcon:
        icon: "check-circle" if root.decision == "granted" else ("alert-circle" if root.decision in ("denied", "error") else "clock-outline")
        theme_text_color: "Custom"
        text_color: theme.success if root.decision == "granted" else (theme.error if root.decision in ("denied", "error") else theme.warning)
        font_size: sp(15)
        size_hint: None, None
        size: dp(18), dp(18)
        pos_hint: {"center_y": .5}

    MDBoxLayout:
        orientation: "vertical"
        size_hint_y: None
        height: dp(36)
        spacing: 0
        pos_hint: {"center_y": .5}
        MDLabel:
            text: root.name if root.name else "Unidentified credential"
            font_size: sp(11)
            bold: True
            shorten: True
            shorten_from: "right"
            text_size: self.width, None
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

    Widget:
        size_hint_x: None
        width: 0

    MDLabel:
        text: root.method_label
        font_size: sp(9)
        bold: True
        size_hint_x: None
        width: dp(62) if app.is_wide else dp(50)
        halign: "right"
        theme_text_color: "Custom"
        text_color: theme.primary_text if root.decision == "granted" else theme.muted

    MDLabel:
        text: root.time_text
        font_size: sp(9)
        size_hint_x: None
        width: dp(62) if app.is_wide else dp(48)
        halign: "right"
        theme_text_color: "Custom"
        text_color: theme.muted


<AccessBox>:
    orientation: "vertical"
    padding: 0, 0, 0, self.bottom_pad

    MDScrollView:
        id: access_scroll
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
                spacing: dp(6)
                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(58)
                    spacing: 0
                    MDLabel:
                        text: "Door Access"
                        font_size: sp(28)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: theme.text
                    MDLabel:
                        text: app.door_name + "  -  face, PIN, card or administrator assistance"
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

            MDBoxLayout:
                size_hint_y: None
                height: dp(26)
                spacing: dp(8)
                StatusPill:
                    text: app.access_controller_label
                    icon: "door-open"
                    bg: app.access_controller_bg
                    fg: app.access_controller_fg
                    pos_hint: {"center_y": .5}
                StatusPill:
                    text: app.access_policy_label
                    icon: "shield-key-outline" if app.access_two_factor else "shield-check-outline"
                    bg: theme.warning_soft if app.access_two_factor else theme.surface
                    fg: theme.warning if app.access_two_factor else theme.muted
                    pos_hint: {"center_y": .5}
                Widget:

            MDCard:
                orientation: "horizontal"
                size_hint_y: None
                height: self.minimum_height if app.access_face_warning else 0
                opacity: 1 if app.access_face_warning else 0
                disabled: not app.access_face_warning
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
                    text: app.access_face_warning
                    font_size: sp(10)
                    adaptive_height: True
                    text_size: self.width, None
                    theme_text_color: "Custom"
                    text_color: theme.warning
                MDTextButton:
                    text: "START" if not app.services_running else "RETRY"
                    font_size: sp(10)
                    theme_text_color: "Custom"
                    text_color: theme.warning
                    pos_hint: {"center_y": .5}
                    on_release: app.start_face_services()

            MDBoxLayout:
                orientation: "horizontal" if app.is_wide else "vertical"
                size_hint_y: None
                height: dp(304) if app.is_wide else dp(560)
                spacing: dp(14)

                CameraCard:
                    id: access_camera
                    size_hint_x: 0.56 if app.is_wide else 1
                    preview_height: dp(196) if app.is_wide else dp(168)
                    retry_callback: app.retry_access_camera

                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_x: 0.44 if app.is_wide else 1
                    spacing: dp(10)

                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(46)
                        spacing: dp(8)
                        MDFillRoundFlatIconButton:
                            text: "Checking..." if app.access_busy else "Scan & unlock"
                            icon: "face-recognition"
                            font_size: sp(12)
                            size_hint_x: 0.56
                            height: dp(46)
                            disabled: app.access_busy or not app.access_face_available
                            on_release: app.scan_access()
                        MDFillRoundFlatIconButton:
                            text: "Alternative"
                            icon: "key-variant"
                            font_size: sp(12)
                            size_hint_x: 0.44
                            height: dp(46)
                            md_bg_color: theme.primary_soft
                            theme_text_color: "Custom"
                            text_color: theme.primary_text
                            theme_icon_color: "Custom"
                            icon_color: theme.primary_text
                            disabled: app.access_busy
                            on_release: app.open_alternative_access()

                    AccessResultCard:
                        id: access_result
                        state: app.access_state
                        title: app.access_title
                        message: app.access_message
                        detail_line1: app.access_detail1
                        detail_line2: app.access_detail2

                    AppCard:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(84)
                        padding: dp(12)
                        spacing: dp(2)
                        MDBoxLayout:
                            size_hint_y: None
                            height: dp(22)
                            spacing: dp(8)
                            MDIcon:
                                icon: "door-open"
                                font_size: sp(14)
                                theme_text_color: "Custom"
                                text_color: theme.muted
                                size_hint: None, None
                                size: dp(16), dp(16)
                                pos_hint: {"center_y": .5}
                            MDLabel:
                                text: app.access_controller_label
                                font_size: sp(11)
                                bold: True
                                theme_text_color: "Custom"
                                text_color: theme.text
                            Widget:
                            MDLabel:
                                text: "Fail-safe" if app.access_fail_mode == "fail_safe" else "Fail-secure"
                                font_size: sp(9)
                                theme_text_color: "Custom"
                                text_color: theme.muted
                        MDLabel:
                            text: app.access_controller_detail
                            font_size: sp(9)
                            shorten: True
                            shorten_from: "right"
                            text_size: self.width, None
                            theme_text_color: "Custom"
                            text_color: theme.muted
                        MDLabel:
                            text: "Card reader: " + app.access_card_status
                            font_size: sp(9)
                            shorten: True
                            shorten_from: "right"
                            text_size: self.width, None
                            theme_text_color: "Custom"
                            text_color: theme.muted
                        Widget:
                            size_hint_y: 1

            AppCard:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(4)
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(28)
                    MDLabel:
                        text: "Recent access"
                        font_size: sp(16)
                        bold: True
                        theme_text_color: "Custom"
                        text_color: theme.text
                    Widget:
                    MDTextButton:
                        text: "Export log"
                        font_size: sp(10)
                        pos_hint: {"center_y": .5}
                        on_release: app.export_access_log()
                MDBoxLayout:
                    id: access_events_box
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(1)

            MDLabel:
                text: "Pilot guardrail: face matching alone is not proof of identity. Simulated mode is not a physical door; real hardware requires a verified liveness provider."
                font_size: sp(9)
                size_hint_y: None
                height: dp(28)
                text_size: self.width, None
                theme_text_color: "Custom"
                text_color: theme.muted
''')


class AccessResultCard(AppCard):
    state = StringProperty("idle")
    title = StringProperty("Ready to scan")
    message = StringProperty("Look at the camera or choose an alternative method.")
    detail_line1 = StringProperty("")
    detail_line2 = StringProperty("")


class AccessEventRow(MDBoxLayout):
    name = StringProperty("")
    detail = StringProperty("")
    method_label = StringProperty("FACE")
    decision = StringProperty("")
    time_text = StringProperty("")


class AccessBox(MDBoxLayout):
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
