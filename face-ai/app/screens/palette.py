"""Central, observable design tokens.

Screens bind to these properties instead of hardcoded colours, so switching
between the light and dark palettes updates every screen at runtime.
"""

from kivy.event import EventDispatcher
from kivy.properties import StringProperty

LIGHT = {
    "primary": "#4F46E5",
    "primary_text": "#4F46E5",
    "primary_dark": "#4338CA",
    "primary_soft": "#EEF2FF",
    "accent": "#0EA5E9",
    "surface": "#F5F6FA",
    "card": "#FFFFFF",
    "line": "#E4E7F0",
    "text": "#151A24",
    "muted": "#667085",
    "hover": "#F2F4F9",
    "success": "#12805C",
    "success_soft": "#E7F7F0",
    "warning": "#B45309",
    "warning_soft": "#FFF4E5",
    "error": "#B42318",
    "error_soft": "#FEECEB",
    "text_on_primary": "#FFFFFF",
    "text_on_primary_soft": "#E4E7FF",
    "white_12": "#FFFFFF1F",
    "white_18": "#FFFFFF2E",
    "transparent": "#00000000",
}

DARK = {
    "primary": "#4F46E5",
    "primary_text": "#B0B4FF",
    "primary_dark": "#6366F1",
    "primary_soft": "#232544",
    "accent": "#38BDF8",
    "surface": "#0E1117",
    "card": "#171B24",
    "line": "#2A3040",
    "text": "#F2F4F8",
    "muted": "#9AA4B2",
    "hover": "#1E2430",
    "success": "#4ADE80",
    "success_soft": "#12301F",
    "warning": "#FBBF24",
    "warning_soft": "#33260B",
    "error": "#F87171",
    "error_soft": "#3A1414",
    "text_on_primary": "#FFFFFF",
    "text_on_primary_soft": "#D7D9FF",
    "white_12": "#FFFFFF1F",
    "white_18": "#FFFFFF2E",
    "transparent": "#00000000",
}


class Theme(EventDispatcher):
    primary = StringProperty(LIGHT["primary"])
    primary_text = StringProperty(LIGHT["primary_text"])
    primary_dark = StringProperty(LIGHT["primary_dark"])
    primary_soft = StringProperty(LIGHT["primary_soft"])
    accent = StringProperty(LIGHT["accent"])
    surface = StringProperty(LIGHT["surface"])
    card = StringProperty(LIGHT["card"])
    line = StringProperty(LIGHT["line"])
    text = StringProperty(LIGHT["text"])
    muted = StringProperty(LIGHT["muted"])
    hover = StringProperty(LIGHT["hover"])
    success = StringProperty(LIGHT["success"])
    success_soft = StringProperty(LIGHT["success_soft"])
    warning = StringProperty(LIGHT["warning"])
    warning_soft = StringProperty(LIGHT["warning_soft"])
    error = StringProperty(LIGHT["error"])
    error_soft = StringProperty(LIGHT["error_soft"])
    text_on_primary = StringProperty(LIGHT["text_on_primary"])
    text_on_primary_soft = StringProperty(LIGHT["text_on_primary_soft"])
    white_12 = StringProperty(LIGHT["white_12"])
    white_18 = StringProperty(LIGHT["white_18"])
    transparent = StringProperty(LIGHT["transparent"])

    def apply(self, mode):
        data = DARK if mode == "dark" else LIGHT
        for key, value in data.items():
            setattr(self, key, value)


theme = Theme()
