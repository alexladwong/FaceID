"""Persistent navigation rail used on wide screens and inside the mobile drawer."""

from kivy.lang import Builder
from kivy.properties import ObjectProperty

from kivymd.uix.boxlayout import MDBoxLayout


Builder.load_string('''
#:import tokens screens.tokens

<NavItem@MDNavigationDrawerItem>
    radius: [dp(12)]
    focus_color: 0.31, 0.27, 0.9, 0.10
    ripple_color: 0.31, 0.27, 0.9, 0.06
    text_color: tokens.TEXT
    icon_color: tokens.MUTED
    selected_color: tokens.PRIMARY


<NavigationMenu>:
    orientation: "vertical"
    padding: dp(10), dp(12), dp(10), dp(10)
    spacing: dp(2)

    MDLabel:
        text: "WORKSPACE"
        font_size: sp(9)
        bold: True
        size_hint_y: None
        height: dp(30)
        theme_text_color: "Custom"
        text_color: tokens.MUTED

    NavItem:
        icon: "view-dashboard-outline"
        text: "Home"
        on_press: app.goto_screen("initScreen")

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
            icon: "circle"
            font_size: sp(8)
            theme_text_color: "Custom"
            text_color: tokens.SUCCESS if app.services_running else tokens.MUTED
            size_hint: None, None
            size: dp(12), dp(12)
            pos_hint: {"center_y": .5}
        MDLabel:
            text: "Engine running" if app.services_running else "Engine stopped"
            font_size: sp(10)
            theme_text_color: "Custom"
            text_color: tokens.MUTED

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
            text_color: tokens.SUCCESS
            size_hint: None, None
            size: dp(14), dp(14)
            pos_hint: {"center_y": .5}
        MDLabel:
            text: "Nothing leaves this device"
            font_size: sp(9)
            theme_text_color: "Custom"
            text_color: tokens.MUTED

    MDLabel:
        text: "Face AI  -  v" + app.app_version
        font_size: sp(9)
        size_hint_y: None
        height: dp(26)
        theme_text_color: "Custom"
        text_color: tokens.MUTED
''')


class NavigationMenu(MDBoxLayout):
    """Shared menu body for the desktop rail and the mobile drawer."""

    screen_manager = ObjectProperty(None)
