from __future__ import annotations
import sys
import os
import threading
import logging
from typing import Optional

try:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Gtk, Adw, GLib, Gio, Gdk
except (ImportError, ValueError):
    Gtk = None  # type: ignore
    Adw = None  # type: ignore
    GLib = None  # type: ignore
    Gio = None  # type: ignore
    Gdk = None  # type: ignore

from displayctl import __version__, __app_name__
from displayctl.display import Display
from displayctl.backends import get_backend
from displayctl.backends.base import DisplayBackend
from displayctl.profile import save_profile, load_profile, list_profiles, delete_profile, apply_profile_displays
from displayctl.utils import setup_logging

log = logging.getLogger(__name__)

ROTATION_OPTIONS = ["normal", "left", "right", "inverted"]


class MonitorWidget(Gtk.Frame):
    def __init__(self, display: Display, backend: DisplayBackend, app: DisplayCtlApp):
        super().__init__()
        self._display = display
        self._backend = backend
        self._app = app
        self.set_css_classes(["card"])

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        self.set_child(box)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        indicator = Gtk.Image.new_from_icon_name("display-symbolic")
        header_box.append(indicator)

        self._name_label = Gtk.Label()
        self._name_label.set_markup(f"<b>{display.name}</b>")
        self._name_label.set_halign(Gtk.Align.START)
        header_box.append(self._name_label)

        if display.primary:
            primary_badge = Gtk.Label(label="Primary")
            primary_badge.set_css_classes(["badge", "primary-badge"])
            header_box.append(primary_badge)

        header_box.append(Gtk.Label.new(""))

        self._status_label = Gtk.Label()
        self._status_label.set_halign(Gtk.Align.END)
        self._status_label.set_hexpand(True)
        header_box.append(self._status_label)
        box.append(header_box)

        self._info_label = Gtk.Label()
        self._info_label.set_halign(Gtk.Align.START)
        box.append(self._info_label)

        controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        controls_box.set_margin_top(6)

        brightness_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        brightness_label = Gtk.Label(label="Brightness")
        brightness_label.set_size_request(80, -1)
        brightness_label.set_xalign(0)
        brightness_box.append(brightness_label)
        self._brightness_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 5
        )
        self._brightness_scale.set_size_request(200, -1)
        self._brightness_scale.set_value(100)
        self._brightness_scale.connect("value-changed", self._on_brightness_changed)
        brightness_box.append(self._brightness_scale)
        self._brightness_value_label = Gtk.Label(label="100%")
        self._brightness_value_label.set_size_request(40, -1)
        brightness_box.append(self._brightness_value_label)
        controls_box.append(brightness_box)

        res_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        res_label = Gtk.Label(label="Resolution")
        res_label.set_size_request(80, -1)
        res_label.set_xalign(0)
        res_box.append(res_label)
        self._res_dropdown = Gtk.DropDown()
        self._res_dropdown.set_size_request(200, -1)
        res_box.append(self._res_dropdown)
        controls_box.append(res_box)

        rot_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        rot_label = Gtk.Label(label="Rotation")
        rot_label.set_size_request(80, -1)
        rot_label.set_xalign(0)
        rot_box.append(rot_label)
        self._rot_dropdown = Gtk.DropDown.new_from_strings(ROTATION_OPTIONS)
        self._rot_dropdown.set_size_request(200, -1)
        rot_box.append(self._rot_dropdown)
        controls_box.append(rot_box)

        box.append(controls_box)

        self._update_display(display)

    def _on_brightness_changed(self, scale: Gtk.Scale):
        val = int(scale.get_value())
        self._brightness_value_label.set_text(f"{val}%")
        self._app.schedule_backend_op(
            self._backend.set_brightness, val, display=self._display.name
        )

    def _populate_resolutions(self, display: Display):
        modes = display.modes
        if not modes:
            self._res_dropdown.set_sensitive(False)
            return
        seen = set()
        items = []
        current_idx = 0
        for i, m in enumerate(modes):
            key = (m["width"], m["height"])
            if key not in seen:
                seen.add(key)
                label = f"{m['width']}x{m['height']}"
                items.append(label)
                if m["width"] == display.width and m["height"] == display.height:
                    current_idx = len(items) - 1
        model = Gtk.StringList.new(items)
        self._res_dropdown.set_model(model)
        self._res_dropdown.set_selected(current_idx)
        self._res_dropdown.connect("notify::selected", self._on_resolution_changed)
        self._res_dropdown.set_sensitive(True)

    def _on_resolution_changed(self, dropdown: Gtk.DropDown, *args):
        pos = dropdown.get_selected()
        if pos == Gtk.INVALID_LIST_POSITION:
            return
        item = dropdown.get_model().get_string(pos)
        if item:
            self._app.schedule_backend_op(
                self._backend.set_resolution, item, display=self._display.name
            )

    def _on_rotation_changed(self, dropdown: Gtk.DropDown, *args):
        pos = dropdown.get_selected()
        if pos == Gtk.INVALID_LIST_POSITION:
            return
        rotation = ROTATION_OPTIONS[pos]
        if rotation != self._display.rotation:
            self._app.schedule_backend_op(
                self._backend.set_rotation, rotation, display=self._display.name
            )

    def _update_display(self, display: Display):
        self._display = display
        if not display.connected:
            self._name_label.set_markup(f"<b>{display.name}</b>  [dim]disconnected[/]")
            self._status_label.set_text("Disconnected")
            self._info_label.set_text("")
            self.set_sensitive(False)
            return
        self.set_sensitive(True)
        self._name_label.set_markup(f"<b>{display.name}</b>")
        self._status_label.set_text("Connected")
        res = display.resolution or "unknown"
        refresh = f"{display.refresh:.2f} Hz" if display.refresh else ""
        info = f"{res}"
        if refresh:
            info += f"  |  {refresh}"
        if display.edid_name and display.edid_name != display.name:
            info += f"  |  {display.edid_name}"
        self._info_label.set_text(info)
        self._populate_resolutions(display)
        rot_idx = ROTATION_OPTIONS.index(display.rotation) if display.rotation in ROTATION_OPTIONS else 0
        self._rot_dropdown.set_selected(rot_idx)
        try:
            self._rot_dropdown.disconnect_by_func(self._on_rotation_changed)
        except TypeError:
            pass
        self._rot_dropdown.connect("notify::selected", self._on_rotation_changed)

    def refresh(self, display: Display):
        self._update_display(display)

    @property
    def display_name(self) -> str:
        return self._display.name


class DisplayCtlApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="dev.displayctl.gui",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self._backend: Optional[DisplayBackend] = None
        self._monitor_widgets: dict[str, MonitorWidget] = {}
        self._profile_list: list[str] = []
        self._backend_ops: list[tuple] = []

    def do_startup(self):
        Adw.Application.do_startup(self)
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        icon_path = os.path.join(os.path.dirname(__file__), "..", "icons", "hicolor")
        icon_theme.add_search_path(os.path.abspath(icon_path))

    def do_activate(self):
        try:
            setup_logging()
            self._backend = get_backend()
        except Exception as e:
            self._show_error(f"Failed to initialize backend: {e}")
            return
        win = Adw.ApplicationWindow(application=self)
        win.set_title(f"{__app_name__} - Display Controller")
        win.set_default_size(900, 700)
        win.set_icon_name("displayctl")

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        header = Adw.HeaderBar()
        main_box.append(header)

        self._status_page = Adw.StatusPage()
        self._status_page.set_title("displayctl")
        self._status_page.set_description("Multi-monitor display controller")
        main_box.append(self._status_page)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        clamp = Adw.Clamp()
        clamp.set_child(content)
        self._status_page.set_child(clamp)

        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        status_bar.set_css_classes(["status-bar"])
        status_bar.set_margin_bottom(6)
        self._connected_label = Gtk.Label()
        self._connected_label.set_markup("<b>Connected:</b> --")
        status_bar.append(self._connected_label)
        self._mode_label = Gtk.Label()
        self._mode_label.set_markup("<b>Mode:</b> --")
        status_bar.append(self._mode_label)
        status_bar.append(Gtk.Label.new(""))
        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.connect("clicked", lambda b: self._refresh_all())
        status_bar.append(refresh_btn)
        cli_btn = Gtk.MenuButton()
        cli_btn.set_label("CLI Help")
        cli_btn.set_icon_name("utilities-terminal-symbolic")
        cli_menu = Gtk.PopoverMenu()
        cli_section = Gtk.StringList.new([
            "displayctl mirror",
            "displayctl extend",
            "displayctl second",
            "displayctl pc",
            "displayctl status",
            "displayctl brightness 80",
            "displayctl save --profile work",
            "displayctl load --profile work",
        ])
        cli_list = Gtk.ListBox()
        cli_list.bind_model(cli_section, self._create_cli_row)
        cli_menu.set_child(cli_list)
        cli_btn.set_popover(cli_menu)
        status_bar.append(cli_btn)
        content.append(status_bar)

        mode_header = Gtk.Label.new()
        mode_header.set_markup("<b>Display Modes</b>")
        mode_header.set_halign(Gtk.Align.START)
        content.append(mode_header)

        mode_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        mode_buttons.set_homogeneous(True)
        modes = [
            ("mirror", "Mirror"),
            ("extend", "Extend"),
            ("second", "Second Only"),
            ("pc", "PC Only"),
        ]
        for key, label in modes:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", self._on_mode_clicked, key)
            mode_buttons.append(btn)
        content.append(mode_buttons)

        monitors_header = Gtk.Label.new()
        monitors_header.set_markup("<b>Monitors</b>")
        monitors_header.set_halign(Gtk.Align.START)
        monitors_header.set_margin_top(12)
        content.append(monitors_header)

        self._monitors_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.append(self._monitors_box)

        profiles_header = Gtk.Label.new()
        profiles_header.set_markup("<b>Profiles</b>")
        profiles_header.set_halign(Gtk.Align.START)
        profiles_header.set_margin_top(12)
        content.append(profiles_header)

        profiles_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        save_btn = Gtk.Button(label="Save Current")
        save_btn.connect("clicked", self._on_save_profile)
        profiles_box.append(save_btn)
        load_btn = Gtk.Button(label="Load Profile")
        load_btn.connect("clicked", self._on_load_profile)
        profiles_box.append(load_btn)
        delete_btn = Gtk.Button(label="Delete Profile")
        delete_btn.connect("clicked", self._on_delete_profile)
        profiles_box.append(delete_btn)
        self._profiles_dropdown = Gtk.DropDown()
        profiles_box.append(self._profiles_dropdown)
        content.append(profiles_box)

        win.set_content(main_box)
        win.present()

        self._refresh_all()

    def _create_cli_row(self, item):
        row = Adw.ActionRow()
        row.set_title(item.get_string())
        row.set_activatable_widget(row)
        row.connect("activated", self._on_cli_row_activated, item.get_string())
        return row

    def _on_cli_row_activated(self, row, cmd: str):
        try:
            import subprocess
            subprocess.Popen(["x-terminal-emulator", "-e", f"bash -c 'echo \"$ {cmd}\" && {cmd}; read -p \"Press Enter...\"'"])
        except FileNotFoundError:
            pass

    def _show_error(self, message: str):
        dialog = Adw.MessageDialog(
            heading="Error",
            body=message,
        )
        dialog.add_response("ok", "OK")
        dialog.present()

    def _show_info(self, title: str, message: str):
        dialog = Adw.MessageDialog(
            heading=title,
            body=message,
        )
        dialog.add_response("ok", "OK")
        dialog.present()

    def _prompt_input(self, title: str, body: str, callback, default: str = ""):
        dialog = Adw.MessageDialog(
            heading=title,
            body=body,
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("ok", "OK")
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("ok")
        entry = Gtk.Entry()
        entry.set_text(default)
        dialog.set_extra_child(entry)
        dialog.connect("response", lambda d, r: callback(entry.get_text()) if r == "ok" else None)
        dialog.present()

    def _on_mode_clicked(self, button: Gtk.Button, mode: str):
        self.schedule_backend_op(self._backend.set_mode, mode)

    def _on_save_profile(self, button: Gtk.Button):
        self._prompt_input("Save Profile", "Enter profile name:", self._do_save_profile)

    def _do_save_profile(self, name: str):
        if not name:
            return
        name = name.strip()
        if not name:
            return
        try:
            displays = self._backend.get_displays()
            save_profile(name, displays)
            self._refresh_profiles()
            self._show_info("Profile Saved", f"Profile '{name}' saved.")
        except Exception as e:
            self._show_error(f"Failed to save profile: {e}")

    def _on_load_profile(self, button: Gtk.Button):
        if not self._profile_list:
            self._show_info("No Profiles", "No saved profiles found.")
            return
        names = "\n".join(f"  • {n}" for n in self._profile_list)
        self._prompt_input("Load Profile", f"Available profiles:\n{names}\n\nEnter profile name:", self._do_load_profile)

    def _do_load_profile(self, name: str):
        if not name or not name.strip():
            return
        name = name.strip()
        try:
            displays = load_profile(name)
            if displays:
                apply_profile_displays(displays, self._backend)
                self._show_info("Profile Loaded", f"Profile '{name}' applied.")
                self._refresh_all()
        except Exception as e:
            self._show_error(f"Failed to load profile: {e}")

    def _on_delete_profile(self, button: Gtk.Button):
        if not self._profile_list:
            self._show_info("No Profiles", "No saved profiles to delete.")
            return
        names = "\n".join(f"  • {n}" for n in self._profile_list)
        self._prompt_input("Delete Profile", f"Available profiles:\n{names}\n\nEnter profile name to delete:", self._do_delete_profile)

    def _do_delete_profile(self, name: str):
        if not name or not name.strip():
            return
        name = name.strip()
        try:
            if delete_profile(name):
                self._refresh_profiles()
                self._show_info("Profile Deleted", f"Profile '{name}' deleted.")
        except Exception as e:
            self._show_error(f"Failed to delete profile: {e}")

    def schedule_backend_op(self, func, *args, **kwargs):
        def run_op():
            try:
                func(*args, **kwargs)
                GLib.idle_add(self._refresh_all)
            except Exception as e:
                log.error(f"Backend operation failed: {e}")
                GLib.idle_add(self._show_error, f"Operation failed: {e}")
        t = threading.Thread(target=run_op, daemon=True)
        t.start()

    def _refresh_all(self):
        if not self._backend:
            return
        try:
            displays = self._backend.get_displays()
            mode = self._backend.get_active_mode()
        except Exception as e:
            log.error(f"Refresh failed: {e}")
            return
        connected = [d for d in displays if d.connected]
        self._connected_label.set_markup(f"<b>Connected:</b> {len(connected)}")
        self._mode_label.set_markup(f"<b>Mode:</b> {mode}")

        existing = set(self._monitor_widgets.keys())
        current = set(d.name for d in connected)

        for name in existing - current:
            widget = self._monitor_widgets.pop(name)
            self._monitors_box.remove(widget)

        for d in connected:
            if d.name in self._monitor_widgets:
                self._monitor_widgets[d.name].refresh(d)
            else:
                widget = MonitorWidget(d, self._backend, self)
                self._monitor_widgets[d.name] = widget
                self._monitors_box.append(widget)

        self._refresh_profiles()

    def _refresh_profiles(self):
        self._profile_list = list_profiles()
        items = self._profile_list if self._profile_list else ["(no profiles)"]
        model = Gtk.StringList.new(items)
        self._profiles_dropdown.set_model(model)
        self._profiles_dropdown.set_sensitive(bool(self._profile_list))


def run_gui():
    if Gtk is None:
        print("Error: PyGObject (gi) with GTK 4.0 is required for the GUI. "
              "Install python3-gi and gir1.2-gtk-4.0, or use the snap package.", file=sys.stderr)
        sys.exit(1)
    app = DisplayCtlApp()
    exit_code = app.run(sys.argv)
    sys.exit(exit_code)


if __name__ == "__main__":
    run_gui()
