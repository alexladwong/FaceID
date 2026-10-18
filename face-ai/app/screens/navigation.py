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

<NavItem>:
    radius: [dp(12)]
    focus_color: 0.31, 0.27, 0.9, 0.10
    ripple_color: 0.31, 0.27, 0.9, 0.06
    text_color: theme.text
    icon_color: theme.muted
    selected_color: theme.primary_text


<NavigationMenu>:
    orientation: "vertical"
    on_pos: self.do_layout()
    padding: dp(10), dp(12), dp(10), dp(10)
    spacing: dp(2)

    MDLabel:
        text: "WORKSPACE"
        font_size: sp(9)
        bold: True
        size_hint_y: None
        height: dp(30)
        theme_text_color: "Custom"
        text_color: theme.muted

    NavItem:
        icon: "view-dashboard-outline"
        text: "Home"
        on_press: app.goto_screen("initScreen")

    NavItem:
        icon: "door-open"
        text: "Access"
        on_press: app.goto_screen("accessScr")

    NavItem:
        icon: "account-group-outline"
        text: "People"
        on_press: app.goto_screen("peopleScr")

    NavItem:
        icon: "account-search-outline"
        text: "Face Finder"
        on_press: app.goto_screen("faceFindScr")

    NavItem:
        icon: "shield-lock-outline"
        text: "Secure Vault"
        on_press: app.goto_screen("securityScr")

    NavItem:
        icon: "tune-variant"
        text: "Settings"
        on_press: app.goto_screen("settingsScr")

    Widget:
        size_hint_y: 1

    MDBoxLayout:
        orientation: "horizontal"
        size_hint_y: None
        height: dp(30)
        padding: dp(10), 0
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
        height: dp(26)
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
    padding: dp(8), dp(10), dp(8), dp(8)
    spacing: dp(4)

    TooltipMDIconButton:
        tooltip_text: "Home"
        icon: "view-dashboard-outline"
        theme_icon_color: "Custom"
        icon_color: theme.primary_text if app.current_screen == "initScreen" else theme.muted
        md_bg_color: theme.primary_soft if app.current_screen == "initScreen" else theme.transparent
        pos_hint: {"center_x": .5}
        on_release: app.goto_screen("initScreen")

    TooltipMDIconButton:
        tooltip_text: "Access"
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
