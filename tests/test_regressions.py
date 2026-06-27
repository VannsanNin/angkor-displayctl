from __future__ import annotations

from unittest.mock import Mock, patch

from displayctl.backends.gnome import GnomeBackend
from displayctl.backends.wayland import WaylandBackend
from displayctl.backends.xrandr import XrandrBackend
from displayctl.display import Display
from displayctl.hotplug import _on_hotplug
from displayctl.utils import run_cmd


def test_run_cmd_dry_run_returns_text_output():
    result = run_cmd(["displayctl", "status"], dry_run=True)

    assert result.stdout == ""
    assert result.stderr == ""


def test_gui_module_imports_without_gtk_runtime():
    import displayctl.gui as gui

    assert hasattr(gui, "run_gui")


def test_xrandr_set_mode_dispatches_without_extra_kwargs():
    backend = XrandrBackend()

    with patch.object(backend, "mirror") as mirror:
        backend.set_mode("mirror", primary="eDP-1", arrange="right-left")

    mirror.assert_called_once_with(dry_run=False, verbose=False)


def test_wayland_set_mode_dispatches_without_extra_kwargs():
    backend = WaylandBackend()

    with patch.object(backend, "second_only") as second_only:
        backend.set_mode("second", primary="eDP-1", arrange="right-left")

    second_only.assert_called_once_with(dry_run=False, verbose=False)


def test_gnome_set_mode_dispatches_without_extra_kwargs():
    backend = GnomeBackend.__new__(GnomeBackend)

    with patch.object(backend, "pc_only") as pc_only:
        backend.set_mode("pc", primary="eDP-1", arrange="right-left")

    pc_only.assert_called_once_with(dry_run=False, verbose=False)


def test_hotplug_applies_matching_profile():
    backend = Mock()
    backend.get_displays.return_value = [
        Display(name="eDP-1", connected=True, width=1920, height=1080),
    ]
    profile_displays = [
        Display(name="eDP-1", connected=True, width=1920, height=1080),
    ]

    with (
        patch("displayctl.hotplug.find_matching_profile", return_value="desk"),
        patch("displayctl.hotplug.load_profile", return_value=profile_displays),
        patch("displayctl.hotplug.apply_profile_displays") as apply_profile,
    ):
        _on_hotplug(backend, notify=False)

    apply_profile.assert_called_once_with(profile_displays, backend)
