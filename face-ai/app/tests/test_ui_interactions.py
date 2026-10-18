"""Real-pointer desktop UI regression tests.

These tests dispatch mouse down/up events through Kivy's Window rather than
calling handlers directly. That distinction matters: the old invisible drawer
scrim received every pointer event before the visible content did.

Run explicitly on a desktop session:

    FACEAI_UI_TESTS=1 ./.venv/bin/python -m unittest tests.test_ui_interactions -v
"""

import os
import tempfile
import unittest

from kivy.clock import Clock
from kivy.core.window import Window
from kivymd.uix.navigationdrawer import MDNavigationDrawerItem


def _enabled():
    return os.environ.get("FACEAI_UI_TESTS") == "1"


@unittest.skipUnless(
    _enabled(),
    "UI interaction tests need a desktop session; set FACEAI_UI_TESTS=1",
)
class UIInteractionTests(unittest.TestCase):
    def test_pointer_reaches_navigation_and_controls(self):
        from main import FaceAiApp

        app = FaceAiApp()
        app.initial_window_size = (1200, 820)
        failures = []

        def check(condition, message):
            print(("PASS " if condition else "FAIL ") + message, flush=True)
            if not condition:
                failures.append(message)

        def widgets():
            found = []

            def walk(widget):
                found.append(widget)
                for child in widget.children:
                    walk(child)

            for child in Window.children:
                walk(child)
            return found

        def visible(widget):
            return (
                widget.width > 0
                and widget.height > 0
                and widget.opacity > 0.05
                and not widget.disabled
            )

        def find_text(text):
            for widget in widgets():
                for attr in ("text", "hint_text"):
                    if getattr(widget, attr, None) == text and visible(widget):
                        return widget
            return None

        def find_title(title):
            for widget in widgets():
                if getattr(widget, "title", None) == title and visible(widget):
                    return widget
            return None

        def find_tooltip(text):
            for widget in widgets():
                if getattr(widget, "tooltip_text", None) == text and visible(widget):
                    return widget
            return None

        def find_nav(text):
            for widget in app.root.ids.nav_menu.walk():
                if isinstance(widget, MDNavigationDrawerItem) and widget.text == text:
                    return widget
            return None

        def find_icon(icon):
            for widget in widgets():
                if getattr(widget, "icon", None) == icon and visible(widget):
                    return widget
            return None

        def find_class(name):
            return [w for w in widgets() if type(w).__name__ == name and visible(w)]

        def click(widget, label):
            if widget is None:
                check(False, "missing control: " + label)
                return
            wx, wy = widget.to_window(*widget.center)
            top = Window.height - wy
            Window.dispatch("on_mouse_down", wx, top, "left", [])
            Clock.schedule_once(
                lambda dt: Window.dispatch("on_mouse_up", wx, top, "left", []), 0.06
            )

        def after(seconds, fn):
            Clock.schedule_once(fn, seconds)

        def go(name, next_fn):
            app.goto_screen(name)
            after(0.35, next_fn)

        steps = []

        def step(fn):
            steps.append(fn)
            return fn

        @step
        def start(dt):
            scrim = app.root.ids.drawer_scrim
            check(
                scrim.width == 0 and scrim.height == 0,
                "closed drawer scrim has no hit area",
            )
            check(
                not scrim.collide_point(Window.width / 2, Window.height / 2),
                "closed drawer scrim cannot cover content",
            )
            check(
                app.root.ids.compact_nav.disabled,
                "hidden compact navigation is disabled",
            )
            click(find_nav("People"), "navigation People")
            after(0.5, navigate_home)

        def navigate_home(dt):
            check(app.current_screen == "peopleScr", "pointer navigation opens People")
            click(find_nav("Home"), "navigation Home")
            after(0.45, quick_action)

        def quick_action(dt):
            check(app.current_screen == "initScreen", "pointer navigation returns Home")
            click(find_title("Door Access"), "quick action Door Access")
            after(0.45, theme)

        def theme(dt):
            check(app.current_screen == "accessScr", "quick action opens Access")
            click(find_nav("Home"), "navigation Home")
            after(0.35, toggle_theme)

        def toggle_theme(dt):
            before = app.theme_dark
            click(find_tooltip("Switch theme"), "theme toggle")
            after(0.35, lambda d: restore_theme(before))

        def restore_theme(before):
            check(app.theme_dark != before, "theme control changes the theme")
            click(find_tooltip("Switch theme"), "theme toggle restore")
            after(0.35, open_help)

        def open_help(dt):
            click(find_tooltip("Help and shortcuts"), "help")
            after(0.4, close_help)

        def close_help(dt):
            check(
                app.txt_dialog is not None and app.txt_dialog._window is not None,
                "help dialog opens",
            )
            click(find_text("Got it"), "help close")
            after(0.45, start_engine)

        def start_engine(dt):
            check(
                app.txt_dialog is None or app.txt_dialog._window is None,
                "help dialog closes and releases the pointer",
            )
            click(find_text("Start face engine"), "start engine")
            after(2.2, stop_engine)

        def stop_engine(dt):
            check(app.services_running, "engine service actually starts")
            stop = find_tooltip("Stop face engine")
            check(stop is not None, "stop engine control is available")
            click(stop, "stop engine")
            after(1.0, access_dialog)

        def access_dialog(dt):
            check(not app.services_running, "engine service actually stops")
            click(find_nav("Access"), "navigation Access")
            after(0.35, open_alternative)

        def open_alternative(dt):
            click(find_text("Alternative"), "alternative access")
            after(0.35, open_pin)

        def open_pin(dt):
            check(
                app.txt_dialog is not None and app.txt_dialog._window is not None,
                "alternative dialog opens",
            )
            click(find_text("PIN"), "alternative PIN")
            after(0.5, close_pin)

        def close_pin(dt):
            check(find_text("Staff / resident ID") is not None, "PIN form opens")
            click(find_text("Cancel"), "PIN cancel")
            after(0.45, settings_dialog)

        def settings_dialog(dt):
            click(find_nav("Settings"), "navigation Settings")
            after(0.4, delete_dialog)

        def delete_dialog(dt):
            click(find_title("Delete generated images"), "delete images")
            after(0.4, cancel_delete)

        def cancel_delete(dt):
            check(
                app.txt_dialog is not None and app.txt_dialog._window is not None,
                "delete confirmation opens",
            )
            click(find_text("CANCEL"), "delete cancel")
            after(0.45, compact_mode)

        def compact_mode(dt):
            check(
                app.txt_dialog is None or app.txt_dialog._window is None,
                "delete confirmation closes",
            )
            Window.size = (800, 700)
            after(0.8, compact_click)

        def compact_click(dt):
            check(app.show_rail and app.rail_compact, "800 px keeps a compact rail")
            click(find_tooltip("People"), "compact navigation People")
            after(0.45, drawer_mode)

        def drawer_mode(dt):
            check(app.current_screen == "peopleScr", "compact rail navigation works")
            Window.size = (756, 700)
            after(0.8, open_drawer)

        def open_drawer(dt):
            check(not app.show_rail, "756 px uses the drawer")
            menu = None
            for widget in widgets():
                if getattr(widget, "icon", None) == "menu" and visible(widget):
                    menu = widget
                    break
            click(menu, "open drawer")
            after(0.5, drawer_destination)

        def drawer_destination(dt):
            scrim = app.root.ids.drawer_scrim
            check(app.drawer_open and scrim.width > 0, "open drawer installs its scrim")
            click(find_nav("People"), "drawer People")
            after(0.5, finish)

        def finish(dt):
            check(not app.drawer_open, "drawer closes after choosing a destination")
            check(app.root.ids.drawer_scrim.width == 0, "closed scrim hit area is removed")
            Window.size = (1200, 820)
            after(0.7, wide_rail)

        def wide_rail(dt):
            click(find_icon("chevron-left"), "collapse rail")
            after(0.6, collapsed_rail)

        def collapsed_rail(dt):
            check(app.nav_collapsed and app.rail_compact, "rail collapse works")
            click(find_icon("chevron-right"), "expand rail")
            after(0.6, keyboard)

        def keyboard(dt):
            check(not app.nav_collapsed, "rail expansion works")
            Window.dispatch("on_key_down", 50, 0, "2", ["meta"])
            after(0.4, people_filter)

        def people_filter(dt):
            check(app.current_screen == "accessScr", "keyboard shortcut navigates")
            app.goto_screen("peopleScr")
            after(0.4, filter_click)

        def filter_click(dt):
            click(find_text("Suspended"), "People filter")
            after(0.35, filter_restore)

        def filter_restore(dt):
            check(app.people_filter == "suspended", "People filter applies")
            click(find_text("All"), "People filter restore")
            after(0.35, vault_files)

        def vault_files(dt):
            import main as main_module

            before_dir = app.sec_file_dir
            root = tempfile.mkdtemp(prefix="faceai_ui_vault_")
            vault_dir = os.path.join(root, "vault")
            os.makedirs(vault_dir)
            source = os.path.join(root, "ui_vault_note.txt")
            with open(source, "w") as handle:
                handle.write("Face AI UI vault regression payload.\n")
            target = os.path.join(vault_dir, "ui_vault_note.txt")
            app.sec_file_dir = vault_dir
            app.goto_screen("securityScr")
            after(0.5, lambda d: start_vault(d, main_module, source, target, vault_dir, before_dir))

        def start_vault(dt, main_module, source, target, vault_dir, before_dir):
            app.sec_login_ok()
            after(0.4, lambda d: upload_vault(d, main_module, source, target, vault_dir, before_dir))

        def upload_vault(dt, main_module, source, target, vault_dir, before_dir):
            def fake_open_file(on_selection=None, **kwargs):
                if on_selection:
                    Clock.schedule_once(lambda d: on_selection([source]), 0.1)

            main_module.filechooser.open_file = fake_open_file
            click(find_text("Upload"), "vault upload")
            after(1.8, lambda d: vault_uploaded(d, download_show, target, vault_dir, before_dir))

        def download_show(*args, **kwargs):
            download_show.called = True

        def vault_uploaded(dt, show, target, vault_dir, before_dir):
            check(os.path.exists(target), "vault upload encrypts the selected file")
            click(find_text("Refresh"), "vault refresh")
            after(0.35, lambda d: vault_row(d, target, vault_dir, before_dir))

        def vault_row(dt, target, vault_dir, before_dir):
            rows = find_class("SecSingleFile")
            check(bool(rows), "vault file row is visible")
            app.op_file_manager.show = download_show
            click(rows[0] if rows else None, "vault download")
            after(0.35, lambda d: vault_delete(d, target, vault_dir, before_dir))

        def vault_delete(dt, target, vault_dir, before_dir):
            check(bool(getattr(download_show, "called", False)), "vault download opens destination")
            click(find_icon("delete-outline"), "vault delete")
            after(0.4, lambda d: vault_cancel(d, target, vault_dir, before_dir))

        def vault_cancel(dt, target, vault_dir, before_dir):
            check(
                app.txt_dialog is not None and app.txt_dialog._window is not None,
                "vault delete confirmation opens",
            )
            click(find_text("Cancel"), "vault delete cancel")
            after(0.4, lambda d: vault_confirm(d, target, vault_dir, before_dir))

        def vault_confirm(dt, target, vault_dir, before_dir):
            check(os.path.exists(target), "vault delete cancel preserves file")
            click(find_icon("delete-outline"), "vault delete again")
            after(0.4, lambda d: vault_confirm_delete(d, target, vault_dir, before_dir))

        def vault_confirm_delete(dt, target, vault_dir, before_dir):
            click(find_text("DELETE"), "vault delete confirm")
            after(0.7, lambda d: vault_done(d, target, vault_dir, before_dir))

        def vault_done(dt, target, vault_dir, before_dir):
            check(not os.path.exists(target), "vault delete removes the file")
            app.sec_file_dir = before_dir
            after(0.3, face_finder)

        def face_finder(dt):
            app.goto_screen("faceFindScr")
            after(0.4, reset_finder)

        def reset_finder(dt):
            click(find_text("Reset"), "Face Finder reset")
            after(0.3, upload_faces)

        def upload_faces(dt):
            import main as main_module

            fixture_dir = os.path.dirname(__file__)
            source = os.path.join(fixture_dir, "fixtures", "face_source.jpg")
            target = os.path.join(fixture_dir, "..", "..", "docs", "images", "gitThumb.jpg")

            def fake_open_file(on_selection=None, **kwargs):
                path = fake_open_file.path
                if on_selection:
                    Clock.schedule_once(lambda d: on_selection([path]), 0.1)

            main_module.filechooser.open_file = fake_open_file
            fake_open_file.path = source
            click(find_title("Source face"), "Face Finder source")
            after(0.9, lambda d: upload_target(d, main_module, fake_open_file, target))

        def upload_target(dt, main_module, fake_open_file, target):
            check(app.src_image_path is not None, "Face Finder source image loads")
            fake_open_file.path = target
            click(find_title("Target photo"), "Face Finder target")
            after(0.9, start_match_engine)

        def start_match_engine(dt):
            check(app.trgt_image_path is not None, "Face Finder target image loads")
            if not app.services_running:
                app.start_face_services()
            after(2.2, run_match)

        def run_match(dt):
            check(app.services_running, "engine runs for Face Finder")
            click(find_text("Find matches"), "Face Finder match")
            after(5.0, match_result)

        def match_result(dt):
            check(app.match_has_results, "Face Finder produces a real match result")
            click(find_text("Reset"), "Face Finder reset after match")
            after(0.4, access_registration)

        def access_registration(dt):
            click(find_nav("Access"), "navigation Access for registration")
            after(0.8, open_registration)

        def open_registration(dt):
            click(find_tooltip("Register a person"), "registration")
            after(2.0, close_registration)

        def close_registration(dt):
            check(find_text("Full name *") is not None, "registration modal opens")
            click(find_text("Cancel"), "registration cancel")
            after(0.5, final_stop)

        def final_stop(dt):
            check(
                app.txt_dialog is None or app.txt_dialog._window is None,
                "registration closes and the app is interactive again",
            )
            if app.services_running:
                app.stop_face_services()
            app.stop()

        Clock.schedule_once(start, 3.0)
        # Safety stop if an operation blocks longer than expected.
        Clock.schedule_once(lambda dt: app.stop(), 90.0)
        app.run()
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
