from __future__ import annotations
import time
import logging
import subprocess
from pathlib import Path

from displayctl.profile import apply_profile_displays, find_matching_profile, load_profile
from displayctl.backends.base import DisplayBackend
from displayctl.utils import DRM_PATH

log = logging.getLogger("displayctl")

UDEV_RULES_DIR = Path("/etc/udev/rules.d")
UDEV_RULE_FILE = UDEV_RULES_DIR / "99-displayctl-hotplug.rules"


def _setup_udev_rule() -> None:
    try:
        if not UDEV_RULES_DIR.exists():
            UDEV_RULES_DIR.mkdir(parents=True, exist_ok=True)
        rule = (
            'ACTION=="change", SUBSYSTEM=="drm", KERNEL=="card*", '
            'RUN+="/usr/bin/displayctl watch --trigger"\n'
        )
        UDEV_RULE_FILE.write_text(rule)
        log.info(f"Wrote udev rule to {UDEV_RULE_FILE}")
    except PermissionError:
        log.warning("Cannot write udev rule (not root). Run with sudo or place manually:")
        log.warning(f"  sudo install -Dm644 /dev/stdin {UDEV_RULE_FILE} <<< '...'")


def _monitor_inotify(backend: DisplayBackend, callback) -> None:
    try:
        import pyinotify
    except ImportError:
        log.error("pyinotify not available; falling back to polling mode (install pyinotify for efficiency)")
        _poll_loop(backend, callback)
        return

    class EventHandler(pyinotify.ProcessEvent):
        def process_IN_ATTRIB(self, event):
            log.debug(f"inotify event on {event.pathname}")
            callback(backend)

        def process_IN_CREATE(self, event):
            log.debug(f"inotify event on {event.pathname}")
            callback(backend)

    wm = pyinotify.WatchManager()
    if DRM_PATH.exists():
        wm.add_watch(str(DRM_PATH), pyinotify.IN_ATTRIB | pyinotify.IN_CREATE, rec=True)
    handler = EventHandler()
    notifier = pyinotify.Notifier(wm, handler)
    log.info("Watching for display hotplug events (inotify)...")
    try:
        notifier.loop()
    except KeyboardInterrupt:
        notifier.stop()


def _poll_loop(backend: DisplayBackend, callback, interval: float = 2.0) -> None:
    log.info(f"Polling for display changes every {interval}s (pyinotify not available)...")
    try:
        while True:
            callback(backend)
            time.sleep(interval)
    except KeyboardInterrupt:
        pass


def _on_hotplug(backend: DisplayBackend, notify: bool = True) -> None:
    displays = backend.get_displays()
    connected = {d.fingerprint() for d in displays if d.connected}
    profile_name = find_matching_profile(connected)
    if profile_name:
        profile_displays = load_profile(profile_name)
        if profile_displays:
            log.info(f"Auto-applying profile '{profile_name}' after hotplug")
            apply_profile_displays(profile_displays, backend)
            if notify:
                try:
                    subprocess.run(
                        ["notify-send", "displayctl", f"Applied profile: {profile_name}"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                except FileNotFoundError:
                    log.debug("notify-send is not available")
    else:
        log.debug("No matching profile found for current display layout")


def run_watch(backend: DisplayBackend, trigger: bool = False) -> None:
    _setup_udev_rule()
    if trigger:
        _on_hotplug(backend, notify=True)
        return
    try:
        _monitor_inotify(backend, lambda b: _on_hotplug(b, notify=True))
    except Exception as e:
        log.error(f"Watch error: {e}")
        _poll_loop(backend, lambda b: _on_hotplug(b, notify=True))
