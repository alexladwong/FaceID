from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivy.utils import platform

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import TwoLineAvatarIconListItem

from screens.palette import theme

# Local imports (their kv rules are registered here as well).
from screens.ui import (  # noqa: F401
    AppCard,
    BusyState,
    EmptyState,
    IconBadge,
    InfoBanner,
    StatusPill,
)


Builder.load_string('''
#:import theme screens.palette.theme
#:import parse_color kivy.parser.parse_color
#:import AppCard screens.ui.AppCard
#:import BusyState screens.ui.BusyState
#:import EmptyState screens.ui.EmptyState
#:import IconBadge screens.ui.IconBadge
#:import InfoBanner screens.ui.InfoBanner
#:import StatusPill screens.ui.StatusPill


<SecurityBox>:
    orientation: "vertical"
    padding: 0, 0, 0, self.bottom_pad

    MDBoxLayout:
        orientation: "vertical"
        padding: dp(24), dp(18), dp(24), dp(18)
        spacing: dp(14)

        MDBoxLayout:
            size_hint_y: None
            height: dp(58)
            MDBoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: dp(58)
                spacing: 0
                MDLabel:
                    text: "Secure Vault"
                    font_size: sp(28)
                    bold: True
                    theme_text_color: "Custom"
                    text_color: theme.text
                MDLabel:
                    text: "Face-protected files, encrypted and stored only on this device."
                    font_size: sp(12)
                    theme_text_color: "Custom"
                    text_color: theme.muted

        MDBoxLayout:
            id: sec_elements_box
            orientation: "vertical"
            spacing: dp(12)


<SecSingleFile>:
    text: root.filename
    secondary_text: root.detail
    on_release: app.download_sec_file(root)
    IconLeftWidget:
        icon: "delete-outline"
        on_release: app.popup_sec_file_delete(root)
    IconRightWidget:
        icon: "download-outline"
        on_release: app.download_sec_file(root)


<LoadingCard>:
    orientation: "vertical"
    size_hint_y: None
    height: dp(150)
    BusyState:
        text: root.text
        detail: root.detail


<CameraCard>:
    orientation: "vertical"
    size_hint_y: None
    height: root.preview_height + dp(88)
    padding: dp(14)
    spacing: dp(8)
    MDBoxLayout:
        size_hint_y: None
        height: dp(24)
        spacing: dp(8)
        MDIcon:
            icon: "camera-outline"
            theme_text_color: "Custom"
            text_color: theme.primary_text
            font_size: sp(15)
            size_hint: None, None
            size: dp(18), dp(18)
            pos_hint: {"center_y": .5}
        MDLabel:
            text: "Live camera"
            font_size: sp(12)
            bold: True
            theme_text_color: "Custom"
            text_color: theme.text
            valign: "middle"
            size_hint_y: None
            height: dp(24)
            text_size: self.width, None
        Widget:
        MDLabel:
            id: cam_status
            text: root.status
            font_size: sp(9)
            halign: "right"
            valign: "middle"
            size_hint_y: None
            height: dp(24)
            text_size: self.width, None
            theme_text_color: "Custom"
            text_color: theme.muted
        MDIconButton:
            icon: "refresh"
            icon_size: dp(16)
            size_hint: None, None
            size: dp(24), dp(24)
            theme_icon_color: "Custom"
            icon_color: theme.muted
            opacity: 1 if root.retry_callback else 0
            width: dp(24) if root.retry_callback else 0
            disabled: not root.retry_callback
            on_release: root.retry_callback() if root.retry_callback else None
    MDBoxLayout:
        size_hint_y: None
        height: root.preview_height
        Widget:
        FloatLayout:
            id: cam_holder
            size_hint: None, 1
            width: min(root.width - dp(64), root.preview_height * root.preview_ratio)
            canvas.before:
                Color:
                    rgba: parse_color("#000000")
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(14)]
                StencilPush:
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(14)]
            canvas.after:
                StencilPop
        Widget:
    MDLabel:
        text: "If the preview stays black, allow camera access in System Settings -> Privacy -> Camera."
        font_size: sp(9)
        theme_text_color: "Custom"
        text_color: theme.muted
        size_hint_y: None
        height: dp(16) if app.is_desktop else 0
        opacity: 1 if app.is_desktop else 0
        text_size: self.width, None


<RegisterCard>:
    orientation: "vertical"
    size_hint_y: None
    height: self.minimum_height
    padding: dp(16)
    spacing: dp(10)
    MDBoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(12)
        IconBadge:
            icon: "face-recognition"
            bg: theme.primary_soft
            fg: theme.primary_text
            size: dp(40), dp(40)
            pos_hint: {"center_y": .5}
        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: dp(36)
            spacing: dp(1)
            pos_hint: {"center_y": .5}
            MDLabel:
                text: "Register your face"
                font_size: sp(14)
                bold: True
                adaptive_height: True
                theme_text_color: "Custom"
                text_color: theme.text
            MDLabel:
                text: "No face is enrolled yet. Save one to lock the vault."
                font_size: sp(10)
                adaptive_height: True
                theme_text_color: "Custom"
                text_color: theme.muted
    MDTextField:
        id: sec_name_inp_txt
        hint_text: "Your name"
        mode: "rectangle"
        multiline: False
        font_size: sp(13)
        size_hint_y: None
        height: dp(58)
        helper_text: "At least 3 characters"
        helper_text_mode: "on_focus"
    MDFillRoundFlatIconButton:
        id: sec_capture_btn
        text: "Saving..." if app.verifying else "Save my face"
        icon: "camera-outline"
        font_size: sp(12)
        size_hint_y: None
        height: dp(42)
        disabled: app.verifying
        on_release: app.sec_capture_frame(sec_name_inp_txt, True)


<LoginCard>:
    orientation: "vertical"
    size_hint_y: None
    height: self.minimum_height
    padding: dp(16)
    spacing: dp(10)
    MDBoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(12)
        IconBadge:
            icon: "shield-lock-outline"
            bg: theme.success_soft
            fg: theme.success
            size: dp(40), dp(40)
            pos_hint: {"center_y": .5}
        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: dp(36)
            spacing: dp(1)
            pos_hint: {"center_y": .5}
            MDLabel:
                text: "Vault is locked"
                font_size: sp(14)
                bold: True
                adaptive_height: True
                theme_text_color: "Custom"
                text_color: theme.text
            MDLabel:
                text: "Look at the camera and unlock with your face."
                font_size: sp(10)
                adaptive_height: True
                theme_text_color: "Custom"
                text_color: theme.muted
    MDFillRoundFlatIconButton:
        id: sec_login_btn
        text: "Checking..." if app.verifying else "Unlock with face"
        icon: "face-recognition"
        font_size: sp(12)
        size_hint_y: None
        height: dp(44)
        disabled: app.verifying
        on_release: app.sec_capture_frame(None, False)


<SecurityTipsCard>:
    orientation: "vertical"
    size_hint_y: None
    height: self.minimum_height
    padding: dp(16)
    spacing: dp(7)

    MDLabel:
        text: "For a good face check"
        font_size: sp(13)
        bold: True
        size_hint_y: None
        height: dp(20)
        theme_text_color: "Custom"
        text_color: theme.text

    MDBoxLayout:
        size_hint_y: None
        height: dp(22)
        spacing: dp(8)
        MDIcon:
            icon: "check-circle-outline"
            theme_text_color: "Custom"
            text_color: theme.success
            font_size: sp(13)
            size_hint: None, None
            size: dp(16), dp(16)
            pos_hint: {"center_y": .5}
        MDLabel:
            text: "Look straight at the camera"
            font_size: sp(10)
            theme_text_color: "Custom"
            text_color: theme.muted

    MDBoxLayout:
        size_hint_y: None
        height: dp(22)
        spacing: dp(8)
        MDIcon:
            icon: "check-circle-outline"
            theme_text_color: "Custom"
            text_color: theme.success
            font_size: sp(13)
            size_hint: None, None
            size: dp(16), dp(16)
            pos_hint: {"center_y": .5}
        MDLabel:
            text: "Keep a single face in frame"
            font_size: sp(10)
            theme_text_color: "Custom"
            text_color: theme.muted

    MDBoxLayout:
        size_hint_y: None
        height: dp(22)
        spacing: dp(8)
        MDIcon:
            icon: "check-circle-outline"
            theme_text_color: "Custom"
            text_color: theme.success
            font_size: sp(13)
            size_hint: None, None
            size: dp(16), dp(16)
            pos_hint: {"center_y": .5}
        MDLabel:
            text: "Good lighting helps matching"
            font_size: sp(10)
            theme_text_color: "Custom"
            text_color: theme.muted

    MDLabel:
        text: "Your face is processed on this device and never uploaded."
        font_size: sp(9)
        theme_text_color: "Custom"
        text_color: theme.success
        size_hint_y: None
        height: self.texture_size[1]
        text_size: self.width, None


<SecAfterLogin>:
    orientation: "vertical"
    spacing: dp(10)

    MDBoxLayout:
        size_hint_y: None
        height: dp(28)
        spacing: dp(8)
        MDIcon:
            icon: "shield-check"
            theme_text_color: "Custom"
            text_color: theme.success
            font_size: sp(20)
            size_hint: None, None
            size: dp(24), dp(24)
            pos_hint: {"center_y": .5}
        MDLabel:
            text: "Your vault"
            font_size: sp(18)
            bold: True
            valign: "middle"
            size_hint_y: None
            height: dp(28)
            text_size: self.width, None
            theme_text_color: "Custom"
            text_color: theme.text
        Widget:
        MDIconButton:
            icon: "lock-outline"
            theme_icon_color: "Custom"
            icon_color: theme.muted
            pos_hint: {"center_y": .5}
            on_release: app.lock_vault()
        StatusPill:
            text: "Encrypted"
            icon: "lock-outline"
            bg: theme.success_soft
            fg: theme.success
            pos_hint: {"center_y": .5}

    InfoBanner:
        id: vault_tip
        text: "Files are encrypted before they are stored. Download them with your face unlocked."
        opacity: 1 if app.vault_tip_visible else 0
        height: self.minimum_height if app.vault_tip_visible else 0
        disabled: not app.vault_tip_visible
        close_callback: app.dismiss_vault_tip

    MDBoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(8)

        MDFillRoundFlatIconButton:
            text: "Working..." if app.vault_busy else "Upload"
            icon: "progress-clock" if app.vault_busy else "folder-key-outline"
            font_size: sp(11)
            size_hint: None, None
            size: dp(108) if app.is_wide else dp(84), dp(38)
            disabled: app.vault_busy
            on_release: app.upload_to_vault()

        MDFillRoundFlatIconButton:
            text: "Refresh"
            icon: "refresh"
            font_size: sp(11)
            size_hint: None, None
            size: dp(100) if app.is_wide else dp(80), dp(38)
            md_bg_color: theme.primary_soft
            theme_text_color: "Custom"
            text_color: theme.primary_text
            theme_icon_color: "Custom"
            icon_color: theme.primary_text
            on_release: app.refresh_sec_file_list()

        MDFillRoundFlatIconButton:
            text: "Add face"
            icon: "face-recognition"
            font_size: sp(11)
            size_hint: None, None
            size: dp(108) if app.is_wide else dp(88), dp(38)
            md_bg_color: theme.primary_soft
            theme_text_color: "Custom"
            text_color: theme.primary_text
            theme_icon_color: "Custom"
            icon_color: theme.primary_text
            on_release: app.add_new_face()

        Widget:
        MDLabel:
            text: app.vault_count_text
            font_size: sp(9)
            size_hint_x: None
            width: dp(104) if app.is_wide else 0
            opacity: 1 if app.is_wide else 0
            halign: "right"
            theme_text_color: "Custom"
            text_color: theme.muted
            pos_hint: {"center_y": .5}

    MDBoxLayout:
        size_hint_y: None
        height: dp(38)
        spacing: dp(8)
        MDTextField:
            id: sec_search
            text: app.vault_search
            hint_text: "Search the vault"
            mode: "rectangle"
            font_size: sp(11)
            size_hint_y: None
            height: dp(38)
            on_text: app.set_vault_search(self.text)
        MDTextButton:
            id: sec_sort
            text: app.vault_sort_label
            font_size: sp(10)
            size_hint_x: None
            width: dp(86)
            theme_text_color: "Custom"
            text_color: theme.primary_text
            on_release: app.toggle_vault_sort()

    MDCard:
        orientation: "vertical"
        size_hint_y: 1
        radius: [dp(16)]
        elevation: 0
        padding: dp(6)
        md_bg_color: theme.card
        border_color: theme.line

        MDScrollView:
            id: sec_file_scroll
            do_scroll_x: False
            MDList:
                id: sec_file_list

        EmptyState:
            id: sec_empty
            icon: "folder-lock-outline"
            text: "No files yet"
            detail: "Upload a file to keep it encrypted on this device."
''')


class SecurityBox(MDBoxLayout):
    """Secure vault: enrollment/login via camera, then an encrypted file list."""

    top_pad = NumericProperty(0)
    bottom_pad = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "security_main_bx"
        if platform == "android":
            try:
                from android.display_cutout import get_height_of_bar

                self.top_pad = int(get_height_of_bar("status"))
                self.bottom_pad = int(get_height_of_bar("navigation"))
            except Exception as e:
                print(f"Failed android 15 padding: {e}")
                self.top_pad = 32
                self.bottom_pad = 48


class SecSingleFile(TwoLineAvatarIconListItem):
    filename = StringProperty("")
    detail = StringProperty("Encrypted - tap to download")


class SecAfterLogin(MDBoxLayout):
    pass


class CameraCard(AppCard):
    status = StringProperty("Starting camera...")
    preview_ratio = NumericProperty(4 / 3)
    preview_height = NumericProperty(dp(280))
    retry_callback = ObjectProperty(None)

    def show_error(self, message):
        self.status = "Unavailable"
        holder = self.ids.cam_holder
        holder.clear_widgets()
        holder.add_widget(
            MDBoxLayout(
                orientation="vertical",
                padding=dp(18),
                spacing=dp(8),
                pos_hint={"center_x": .5, "center_y": .5},
                size_hint=(1, 1),
            )
        )
        box = holder.children[0]
        from kivymd.uix.label import MDIcon, MDLabel

        box.add_widget(
            MDIcon(
                icon="camera-off-outline",
                theme_text_color="Custom",
                text_color=theme.muted,
                font_size=sp(34),
                size_hint_y=None,
                height=dp(40),
                pos_hint={"center_x": .5},
            )
        )
        box.add_widget(
            MDLabel(
                text=message,
                halign="center",
                font_size=sp(10),
                theme_text_color="Custom",
                text_color=theme.muted,
                size_hint_y=None,
                height=dp(30),
                text_size=(dp(220), None),
                pos_hint={"center_x": .5},
            )
        )


class RegisterCard(AppCard):
    pass


class LoginCard(AppCard):
    pass


class SecurityTipsCard(AppCard):
    pass


class LoadingCard(AppCard):
    text = StringProperty("")
    detail = StringProperty("")
