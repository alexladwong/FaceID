"""Persistent navigation rail used on wide screens and inside the mobile drawer."""

from kivy.lang import Builder
from kivy.properties import ObjectProperty

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.navigationdrawer import MDNavigationDrawerItem


class _DrawerMenuStub:
    """KivyMD items call reset_active_color on release; the rail is not a
    MDNavigationDrawerMenu, so provide a no-op implementation."""

    def reset_active_color(self, item):
        pass


class NavItem(MDNavigationDrawerItem):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self._drawer_menu is None:
            self._drawer_menu = _DrawerMenuStub()


Builder.load_string('''
#:import theme screens.palette.theme
#:import parse_color kivy.parser.parse_color

<NavItem>:
    size_hint_y: None
    height: dp(44)
    radius: [dp(10)]
    focus_color: theme.hover
    ripple_color: theme.primary_soft
    text_color: theme.text
    icon_color: theme.muted
    selected_color: theme.primary_text
    canvas.before:
        Color:
            rgba: parse_color(theme.primary_soft) if root.selected else parse_color(theme.transparent)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]
        Color:
            rgba: parse_color(theme.primary) if root.selected else parse_color(theme.transparent)
        RoundedRectangle:
            pos: self.x, self.center_y - dp(9)
            size: dp(3), dp(18)
            radius: [dp(1.5)]


<NavigationMenu>:
    orientation: "vertical"
    on_pos: self.do_layout()
    padding: dp(12), dp(14), dp(12), dp(10)
    spacing: 0

    # --- brand ---------------------------------------------------------
    MDBoxLayout:
        orientation: "horizontal"
        size_hint_y: None
        height: dp(54)
        spacing: dp(10)
        padding: dp(2), 0

        MDCard:
            size_hint: None, None
            size: dp(36), dp(36)
            radius: [dp(11)]
            elevation: 0
            md_bg_color: theme.primary
            border_color: theme.transparent
            pos_hint: {"center_y": .5}
            MDIcon:
                icon: "face-recognition"
                theme_text_color: "Custom"
                text_color: theme.text_on_primary
                font_size: sp(20)
                pos_hint: {"center_x": .5, "center_y": .5}

        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: dp(38)
            spacing: 0
            pos_hint: {"center_y": .5}
            MDLabel:
                text: "Face AI"
                font_size: sp(16)
                bold: True
                theme_text_color: "Custom"
                text_color: theme.text
            MDLabel:
                text: "Local-first"
                font_size: sp(9)
                theme_text_color: "Custom"
                text_color: theme.muted

        MDIconButton:
            icon: "chevron-left"
            theme_icon_color: "Custom"
            icon_color: theme.muted
            size_hint_x: None
            width: dp(30) if app.is_wide else 0
            opacity: 1 if app.is_wide else 0
            disabled: not app.is_wide
            pos_hint: {"center_y": .5}
            on_release: app.toggle_nav_collapse()

        MDIconButton:
            icon: "close"
            theme_icon_color: "Custom"
            icon_color: theme.muted
            size_hint_x: None
            width: dp(36) if not app.is_wide else 0
            opacity: 1 if not app.is_wide else 0
            disabled: app.is_wide
            pos_hint: {"center_y": .5}
            on_release: app.close_drawer()

    MDCard:
        size_hint_y: None
        height: dp(1)
        radius: [0]
        elevation: 0
        md_bg_color: theme.line
        border_color: theme.transparent
        opacity: .7

    # --- grouped navigation -------------------------------------------
    MDScrollView:
        do_scroll_x: False
        bar_width: 0

        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: self.minimum_height
            spacing: dp(2)

            MDLabel:
                text: "WORKSPACE"
                font_size: sp(9)
                bold: True
                size_hint_y: None
                height: dp(30)
                theme_text_color: "Custom"
                text_color: theme.muted
                valign: "bottom"

            NavItem:
                icon: "view-dashboard-outline"
                text: "Home"
                on_press: app.goto_screen("initScreen")

            MDLabel:
                text: "FACE TOOLS"
                font_size: sp(9)
                bold: True
                size_hint_y: None
                height: dp(30)
                theme_text_color: "Custom"
                text_color: theme.muted
                valign: "bottom"

            NavItem:
                icon: "account-search-outline"
                text: "Face Finder"
                on_press: app.goto_screen("faceFindScr")

            NavItem:
                icon: "shield-lock-outline"
                text: "Secure Vault"
                on_press: app.goto_screen("securityScr")

            MDLabel:
                text: "DOOR ACCESS"
                font_size: sp(9)
                bold: True
                size_hint_y: None
                height: dp(30)
                theme_text_color: "Custom"
                text_color: theme.muted
                valign: "bottom"

            NavItem:
                icon: "door-open"
                text: "Access"
                on_press: app.goto_screen("accessScr")

            NavItem:
                icon: "account-group-outline"
                text: "People"
                on_press: app.goto_screen("peopleScr")

            MDLabel:
                text: "SYSTEM"
                font_size: sp(9)
                bold: True
                size_hint_y: None
                height: dp(30)
                theme_text_color: "Custom"
                text_color: theme.muted
                valign: "bottom"

            NavItem:
                icon: "tune-variant"
                text: "Settings"
                on_press: app.goto_screen("settingsScr")

    # --- footer --------------------------------------------------------
    MDCard:
        size_hint_y: None
        height: dp(1)
        radius: [0]
        elevation: 0
        md_bg_color: theme.line
        border_color: theme.transparent
        opacity: .7

    MDBoxLayout:
        orientation: "horizontal"
        size_hint_y: None
        height: dp(30)
        spacing: dp(8)

        MDIcon:
            icon: "shield-check-outline"
            font_size: sp(12)
            theme_text_color: "Custom"
            text_color: theme.success
            size_hint: None, None
            size: dp(14), dp(14)
            pos_hint: {"center_y": .5}
        MDLabel:
            text: "Nothing leaves this device"
            font_size: sp(9)
            theme_text_color: "Custom"
            text_color: theme.muted

    MDLabel:
        text: "Face AI  -  v" + app.app_version
        font_size: sp(9)
        size_hint_y: None
        height: dp(24)
        theme_text_color: "Custom"
        text_color: theme.muted
''')


class NavigationMenu(MDBoxLayout):
    """Shared menu body for the desktop rail and the mobile drawer."""

    screen_manager = ObjectProperty(None)


Builder.load_string('''
#:import theme screens.palette.theme
#:import TooltipMDIconButton screens.ui.TooltipMDIconButton


<CompactNav>:
    orientation: "vertical"
    on_pos: self.do_layout()
    padding: dp(12), dp(14), dp(12), dp(10)
    spacing: dp(4)

    MDCard:
        size_hint: None, None
        size: dp(38), dp(38)
        radius: [dp(12)]
        elevation: 0
        md_bg_color: theme.primary
        border_color: theme.transparent
        pos_hint: {"center_x": .5}
        MDIcon:
            icon: "face-recognition"
            theme_text_color: "Custom"
            text_color: theme.text_on_primary
            font_size: sp(20)
            pos_hint: {"center_x": .5, "center_y": .5}

    MDCard:
        size_hint_y: None
        height: dp(1)
        radius: [0]
        elevation: 0
        md_bg_color: theme.line
        border_color: theme.transparent
        opacity: .7

    TooltipMDIconButton:
        tooltip_text: "Expand navigation"
        icon: "chevron-right"
        theme_icon_color: "Custom"
        icon_color: theme.muted
        size_hint_y: None
        height: dp(36)
        pos_hint: {"center_x": .5}
        on_release: app.toggle_nav_collapse()

    TooltipMDIconButton:
        tooltip_text: "Home"
        icon: "view-dashboard-outline"
        theme_icon_color: "Custom"
        icon_color: theme.primary_text if app.current_screen == "initScreen" else theme.muted
        md_bg_color: theme.primary_soft if app.current_screen == "initScreen" else theme.transparent
        pos_hint: {"center_x": .5}
        on_release: app.goto_screen("initScreen")

    TooltipMDIconButton:
        tooltip_text: "Face Finder"
        icon: "account-search-outline"
        theme_icon_color: "Custom"
        icon_color: theme.primary_text if app.current_screen == "faceFindScr" else theme.muted
        md_bg_color: theme.primary_soft if app.current_screen == "faceFindScr" else theme.transparent
        pos_hint: {"center_x": .5}
        on_release: app.goto_screen("faceFindScr")

    TooltipMDIconButton:
        tooltip_text: "Secure Vault"
        icon: "shield-lock-outline"
        theme_icon_color: "Custom"
        icon_color: theme.primary_text if app.current_screen == "securityScr" else theme.muted
        md_bg_color: theme.primary_soft if app.current_screen == "securityScr" else theme.transparent
        pos_hint: {"center_x": .5}
        on_release: app.goto_screen("securityScr")

    TooltipMDIconButton:
        tooltip_text: "Door Access"
        icon: "door-open"
        theme_icon_color: "Custom"
        icon_color: theme.primary_text if app.current_screen == "accessScr" else theme.muted
        md_bg_color: theme.primary_soft if app.current_screen == "accessScr" else theme.transparent
        pos_hint: {"center_x": .5}
        on_release: app.goto_screen("accessScr")

    TooltipMDIconButton:
        tooltip_text: "People"
        icon: "account-group-outline"
        theme_icon_color: "Custom"
        icon_color: theme.primary_text if app.current_screen == "peopleScr" else theme.muted
        md_bg_color: theme.primary_soft if app.current_screen == "peopleScr" else theme.transparent
        pos_hint: {"center_x": .5}
        on_release: app.goto_screen("peopleScr")

    TooltipMDIconButton:
        tooltip_text: "Settings"
        icon: "tune-variant"
        theme_icon_color: "Custom"
        icon_color: theme.primary_text if app.current_screen == "settingsScr" else theme.muted
        md_bg_color: theme.primary_soft if app.current_screen == "settingsScr" else theme.transparent
        pos_hint: {"center_x": .5}
        on_release: app.goto_screen("settingsScr")

    Widget:

    MDIcon:
        icon: "shield-check-outline"
        theme_text_color: "Custom"
        text_color: theme.success
        font_size: sp(16)
        size_hint: None, None
        size: dp(20), dp(20)
        pos_hint: {"center_x": .5}
''')


class CompactNav(MDBoxLayout):
    pass
