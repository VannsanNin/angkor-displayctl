import logging
import subprocess
from displayctl.utils import detect_session_type, which
from displayctl.backends.base import DisplayBackend
from displayctl.backends.xrandr import XrandrBackend
from displayctl.backends.wayland import WaylandBackend
from displayctl.backends.gnome import GnomeBackend

log = logging.getLogger("displayctl")


def _is_gnome() -> bool:
    try:
        result = subprocess.run(
            ["gdbus", "call", "--session",
             "--dest", "org.gnome.Mutter.DisplayConfig",
             "--object-path", "/org/gnome/Mutter/DisplayConfig",
             "--method", "org.freedesktop.DBus.Introspectable.Introspect"],
            capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_backend() -> DisplayBackend:
    session = detect_session_type()
    if session == "wayland":
        if _is_gnome():
            log.debug("Using GNOME Wayland backend (Mutter D-Bus API)")
            return GnomeBackend()
        if which("wlr-randr") or which("swaymsg"):
            log.debug("Using Wayland backend (wlr-randr/swaymsg detected)")
            return WaylandBackend()
        log.debug("Wayland session detected but no GNOME/wlr-randr/swaymsg found; falling back to xrandr")
    log.debug("Using X11 (xrandr) backend")
    return XrandrBackend()
