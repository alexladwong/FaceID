"""Reusable interface building blocks shared by the Face AI screens."""

from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import (
    BooleanProperty,
    ColorProperty,
    NumericProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivymd.uix.behaviors import HoverBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDIconButton
from kivymd.uix.tooltip import MDTooltip

from screens.palette import theme


class TooltipMDIconButton(MDIconButton, MDTooltip):
    """Icon button with a compact material tooltip (used by the icon rail)."""


class AppCard(MDCard):
    """A card with the app's own border colour (KivyMD only honours
    ``line_color`` in the M3 material style)."""

    border_color = ColorProperty(theme.line)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class IconBadge(FloatLayout):
    """Rounded tinted square with a centred Material icon."""

    icon = StringProperty("information-outline")
    bg = ColorProperty(theme.primary_soft)
    fg = ColorProperty(theme.primary)


class Pill(MDCard):
    """Compact icon + label pill that measures its own width.

    MDLabel forces ``text_size = (width, None)``, so binding the label width to
    its texture width makes the text wrap one character per line. Measuring the
    text up-front with ``CoreLabel`` keeps the pill a stable size.
    """

    text = StringProperty("")
    icon = StringProperty("check-circle-outline")
    fg = ColorProperty(theme.success)
    bg = ColorProperty(theme.success_soft)
    font_size = NumericProperty(sp(10))
    icon_size = NumericProperty(sp(12))
    text_width = NumericProperty(0)
    pill_width = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(
            text=self._measure,
            font_size=self._measure,
            icon_size=self._measure,
            padding=self._measure,
            spacing=self._measure,
        )
        Clock.schedule_once(self._measure, 0)

    def _measure(self, *args):
        if not self.text:
            self.pill_width = 0
            return
        label = CoreLabel(text=self.text, font_size=self.font_size, bold=True)
        label.refresh()
        self.text_width = label.texture.size[0] + dp(4)
        left, _top, right, _bottom = self.padding
        self.pill_width = (
            left + self.icon_size + self.spacing + self.text_width + right
        )


class FeatureChip(Pill):
    """Small translucent pill used on the brand hero."""

    fg = ColorProperty(theme.text_on_primary)
    bg = ColorProperty(theme.white_12)


class StatusPill(Pill):
    """Compact state indicator (Ready / Running / Encrypted)."""


class InfoBanner(MDCard):
    """Inline, dismissible hint."""

    text = StringProperty("")
    close_callback = ObjectProperty(None)


class EmptyState(MDBoxLayout):
    """Centred icon + title + detail shown when there is nothing to display."""

    icon = StringProperty("image-outline")
    text = StringProperty("")
    detail = StringProperty("")


class BusyState(MDBoxLayout):
    """Centred spinner + label for operations in progress."""

    text = StringProperty("")
    detail = StringProperty("")


class NoticeCard(AppCard):
    """Card used for a blocking problem (no camera, database error...)."""

    icon = StringProperty("alert-circle-outline")
    title = StringProperty("")
    detail = StringProperty("")
    tint = ColorProperty(theme.error_soft)
    fg = ColorProperty(theme.error)


class UploadTile(AppCard):
    """Tappable image picker with a preview area."""

    title = StringProperty("Source face")
    subtitle = StringProperty("One clear face")
    icon_name = StringProperty("account-outline")
    purpose = StringProperty("src")
    image_source = StringProperty("")
    file_name = StringProperty("")
    loaded = BooleanProperty(False)
    failed = BooleanProperty(False)

    def on_image_source(self, *args):
        self.loaded = False
        self.failed = False


class ResultPane(AppCard):
    """Card that holds a result image, a spinner or an empty state."""

    title = StringProperty("")


class RecentTile(AppCard):
    """Thumbnail of a generated match shown on the dashboard."""

    image_source = StringProperty("")


class SettingsRow(ButtonBehavior, HoverBehavior, MDBoxLayout):
    """Single tappable row inside a settings card."""

    icon = StringProperty("cog-outline")
    title = StringProperty("")
    subtitle = StringProperty("")
    tint = ColorProperty(theme.primary_soft)
    fg = ColorProperty(theme.primary)
    chevron = BooleanProperty(True)
    hover_bg = ColorProperty(theme.transparent)


Builder.load_string('''
#:import theme screens.palette.theme
#:import parse_color kivy.parser.parse_color


<AppCard>:
    orientation: "vertical"
    radius: [dp(18)]
    elevation: 0
    md_bg_color: theme.card
    border_color: theme.line
    canvas.after:
        Color:
            rgba: root.border_color
        Line:
            width: dp(1)
            rounded_rectangle: (self.x, self.y, self.width, self.height, root.radius[0])


<IconBadge>:
    size_hint: None, None
    bg: theme.primary_soft
    fg: theme.primary_text
    canvas.before:
        Color:
            rgba: root.bg
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]
    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: root.fg
        font_size: sp(20)
        size_hint: None, None
        size: dp(24), dp(24)
        pos_hint: {"center_x": .5, "center_y": .5}


<FeatureChip>:
    orientation: "horizontal"
    size_hint: None, None
    height: dp(26)
    width: root.pill_width
    padding: dp(9), 0, dp(11), 0
    spacing: dp(5)
    radius: [dp(13)]
    elevation: 0
    border_color: theme.transparent
    md_bg_color: root.bg
    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: root.fg
        font_size: root.icon_size
        size_hint: None, None
        size: root.icon_size, root.icon_size
        pos_hint: {"center_y": .5}
    MDLabel:
        text: root.text
        theme_text_color: "Custom"
        text_color: root.fg
        font_size: root.font_size
        bold: True
        size_hint: None, None
        width: root.text_width
        height: self.texture_size[1]
        pos_hint: {"center_y": .5}


<StatusPill>:
    orientation: "horizontal"
    size_hint: None, None
    height: dp(26)
    width: root.pill_width
    padding: dp(8), 0, dp(10), 0
    spacing: dp(4)
    radius: [dp(13)]
    elevation: 0
    border_color: theme.transparent
    md_bg_color: root.bg
    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: root.fg
        font_size: root.icon_size
        size_hint: None, None
        size: root.icon_size, root.icon_size
        pos_hint: {"center_y": .5}
    MDLabel:
        text: root.text
        theme_text_color: "Custom"
        text_color: root.fg
        font_size: root.font_size
        bold: True
        size_hint: None, None
        width: root.text_width
        height: self.texture_size[1]
        pos_hint: {"center_y": .5}


<EmptyState>:
    orientation: "vertical"
    spacing: dp(5)
    padding: dp(8)
    Widget:
        size_hint_y: 1
    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: theme.muted
        font_size: sp(30)
        size_hint: None, None
        size: dp(40), dp(34)
        pos_hint: {"center_x": .5}
    MDLabel:
        text: root.text
        halign: "center"
        font_size: sp(12)
        bold: True
        theme_text_color: "Custom"
        text_color: theme.text
        size_hint_y: None
        height: self.texture_size[1]
        text_size: self.width, None
    MDLabel:
        text: root.detail
        halign: "center"
        font_size: sp(10)
        theme_text_color: "Custom"
        text_color: theme.muted
        size_hint_y: None
        height: self.texture_size[1] if root.detail else 0
        text_size: self.width, None
        opacity: 1 if root.detail else 0
    Widget:
        size_hint_y: 1


<BusyState>:
    orientation: "vertical"
    spacing: dp(6)
    padding: dp(8)
    Widget:
        size_hint_y: 1
    MDSpinner:
        size_hint: None, None
        size: dp(28), dp(28)
        pos_hint: {"center_x": .5}
        active: True
        color: theme.primary
    MDLabel:
        text: root.text
        halign: "center"
        font_size: sp(12)
        bold: True
        theme_text_color: "Custom"
        text_color: theme.text
        size_hint_y: None
        height: self.texture_size[1]
        text_size: self.width, None
    MDLabel:
        text: root.detail
        halign: "center"
        font_size: sp(10)
        theme_text_color: "Custom"
        text_color: theme.muted
        size_hint_y: None
        height: self.texture_size[1] if root.detail else 0
        text_size: self.width, None
        opacity: 1 if root.detail else 0
    Widget:
        size_hint_y: 1


<NoticeCard>:
    orientation: "vertical"
    size_hint_y: None
    height: self.minimum_height
    padding: dp(16)
    spacing: dp(8)
    MDBoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(12)
        IconBadge:
            icon: root.icon
            bg: root.tint
            fg: root.fg
            size: dp(40), dp(40)
            pos_hint: {"center_y": .5}
        MDLabel:
            text: root.title
            font_size: sp(14)
            bold: True
            valign: "center"
            size_hint_y: None
            height: dp(40)
            text_size: self.width, None
            theme_text_color: "Custom"
            text_color: theme.text
    MDLabel:
        text: root.detail
        font_size: sp(11)
        theme_text_color: "Custom"
        text_color: theme.muted
        size_hint_y: None
        height: self.texture_size[1]
        text_size: self.width, None


<InfoBanner>:
    orientation: "horizontal"
    size_hint_y: None
    height: self.minimum_height
    padding: dp(12), dp(9)
    spacing: dp(9)
    radius: [dp(13)]
    elevation: 0
    border_color: theme.transparent
    md_bg_color: theme.primary_soft
    MDIcon:
        icon: "lightbulb-on-outline"
        theme_text_color: "Custom"
        text_color: theme.primary_text
        font_size: sp(16)
        size_hint: None, None
        size: dp(18), dp(18)
        pos_hint: {"center_y": .5}
    MDLabel:
        text: root.text
        font_size: sp(11)
        adaptive_height: True
        text_size: self.width, None
        theme_text_color: "Custom"
        text_color: theme.text
    MDIconButton:
        icon: "close"
        theme_icon_color: "Custom"
        icon_color: theme.muted
        icon_size: sp(15)
        size_hint: None, None
        size: dp(26), dp(26)
        pos_hint: {"center_y": .5}
        on_release: root.close_callback() if root.close_callback else None


<UploadTile>:
    orientation: "vertical"
    size_hint_y: None
    height: dp(224)
    padding: dp(12)
    spacing: dp(8)
    radius: [dp(18)]
    ripple_behavior: True
    opacity: .55 if self.disabled else 1
    MDBoxLayout:
        size_hint_y: None
        height: dp(138)
        padding: dp(6)
        canvas.before:
            Color:
                rgba: parse_color(theme.primary_soft)
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [dp(14)]
        RelativeLayout:
            MDIcon:
                icon: root.icon_name
                theme_text_color: "Custom"
                text_color: theme.primary_text
                font_size: sp(34)
                size_hint: None, None
                size: dp(44), dp(44)
                pos_hint: {"center_x": .5, "center_y": .60}
                opacity: 0 if root.image_source else 1
            MDLabel:
                text: "Choose image"
                halign: "center"
                font_size: sp(10)
                theme_text_color: "Custom"
                text_color: theme.muted
                size_hint_y: None
                height: dp(16)
                pos_hint: {"center_x": .5, "center_y": .34}
                opacity: 0 if root.image_source else 1
            Image:
                source: root.image_source
                fit_mode: "contain"
                opacity: 1 if root.image_source else 0
                on_texture: root.loaded = bool(self.texture)
            MDSpinner:
                active: bool(root.image_source) and not root.loaded and not root.failed
                opacity: 1 if root.image_source and not root.loaded and not root.failed else 0
                size_hint: None, None
                size: dp(24), dp(24)
                pos_hint: {"center_x": .5, "center_y": .5}
                color: theme.primary
            MDIcon:
                icon: "alert-circle-outline"
                theme_text_color: "Custom"
                text_color: theme.error
                font_size: sp(28)
                size_hint: None, None
                size: dp(32), dp(32)
                pos_hint: {"center_x": .5, "center_y": .5}
                opacity: 1 if root.failed else 0
    MDLabel:
        text: root.title
        font_size: sp(13)
        bold: True
        size_hint_y: None
        height: dp(20)
        theme_text_color: "Custom"
        text_color: theme.text
    MDLabel:
        text: root.file_name if root.file_name else root.subtitle
        font_size: sp(10)
        shorten: True
        shorten_from: "right"
        size_hint_y: None
        height: dp(16)
        text_size: self.width, None
        theme_text_color: "Custom"
        text_color: theme.muted


<ResultPane>:
    orientation: "vertical"
    padding: dp(10)
    spacing: dp(6)
    radius: [dp(16)]
    md_bg_color: "#FBFCFE"
    MDLabel:
        text: root.title
        font_size: sp(9)
        bold: True
        size_hint_y: None
        height: dp(16)
        text_size: self.width, None
        theme_text_color: "Custom"
        text_color: theme.muted
    MDBoxLayout:
        id: content


<SettingsRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(56)
    tint: theme.primary_soft
    fg: theme.primary_text
    spacing: dp(12)
    padding: dp(8), 0, dp(4), 0
    opacity: .55 if self.disabled else 1
    canvas.before:
        Color:
            rgba: root.hover_bg
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]
    on_enter: root.hover_bg = parse_color(theme.hover) if not root.disabled else parse_color(theme.transparent)
    on_leave: root.hover_bg = parse_color(theme.transparent)
    IconBadge:
        icon: root.icon
        bg: root.tint
        fg: root.fg
        size: dp(36), dp(36)
        pos_hint: {"center_y": .5}
    MDBoxLayout:
        orientation: "vertical"
        size_hint_y: None
        height: dp(36)
        spacing: dp(1)
        pos_hint: {"center_y": .5}
        MDLabel:
            text: root.title
            font_size: sp(13)
            bold: True
            adaptive_height: True
            theme_text_color: "Custom"
            text_color: theme.text
        MDLabel:
            text: root.subtitle
            font_size: sp(10)
            adaptive_height: True
            shorten: True
            shorten_from: "right"
            text_size: self.width, None
            theme_text_color: "Custom"
            text_color: theme.muted
    Widget:
    MDIcon:
        icon: "chevron-right"
        theme_text_color: "Custom"
        text_color: theme.muted
        font_size: sp(18)
        size_hint: None, None
        size: dp(20), dp(20)
        pos_hint: {"center_y": .5}
        opacity: 1 if root.chevron else 0


<RecentTile>:
    radius: [dp(14)]
    padding: 0
    ripple_behavior: True
    size_hint_y: None
    height: dp(104)
    on_enter: self.border_color = parse_color(theme.primary)
    on_leave: self.border_color = parse_color(theme.line)
    on_release: app.open_file(root.image_source)

    Image:
        source: root.image_source
        fit_mode: "cover"
''')
