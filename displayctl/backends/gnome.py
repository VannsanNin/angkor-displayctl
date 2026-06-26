from __future__ import annotations
import logging
from typing import Optional

try:
    from gi.repository import Gio, GLib
except ImportError:
    Gio = None  # type: ignore
    GLib = None  # type: ignore

from displayctl.backends.base import DisplayBackend
from displayctl.display import Display

log = logging.getLogger("displayctl")


METHOD_VERIFY = 0
METHOD_TEMPORARY = 1
METHOD_PERSISTENT = 2

APPLY_METHOD = METHOD_TEMPORARY

ROTATION_MAP = {
    "normal": 0,
    "left": 1,
    "right": 2,
    "inverted": 3,
}

ROTATION_REVERSE = {v: k for k, v in ROTATION_MAP.items()}


class GnomeBackend(DisplayBackend):
    def __init__(self):
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self._proxy = Gio.DBusProxy.new_sync(
            bus,
            Gio.DBusProxyFlags.NONE,
            None,
            "org.gnome.Mutter.DisplayConfig",
            "/org/gnome/Mutter/DisplayConfig",
            "org.gnome.Mutter.DisplayConfig",
            None,
        )

    def _call(self, method: str, params: Optional[GLib.Variant] = None):
        return self._proxy.call_sync(
            method, params, Gio.DBusCallFlags.NONE, -1, None
        ).unpack()

    def _get_state(self):
        serial, monitors, logical_monitors, properties = self._call("GetCurrentState")
        return serial, monitors, logical_monitors, properties

    def _apply_config(
        self,
        serial: int,
        method: int,
        logical_monitors: list,
        properties: dict,
        dry_run: bool = False,
    ):
        if dry_run:
            log.info(
                "[DRY-RUN] Would apply config: method=%d, logical_monitors=%s",
                method, logical_monitors,
            )
            return
        variant = GLib.Variant("(uua(iiduba(ssa{sv}))a{sv})", (
            serial,
            method,
            logical_monitors,
            properties,
        ))
        self._proxy.call_sync(
            "ApplyMonitorsConfig", variant, Gio.DBusCallFlags.NONE, -1, None
        )

    def _parse_displays(self):
        serial, monitors, logical_monitors, properties = self._get_state()

        active_logical = {}
        for lx, ly, scale, rotation, is_primary, monitor_specs, lprops in logical_monitors:
            for connector, vendor, product, serial_num in monitor_specs:
                active_logical[connector] = {
                    "x": lx, "y": ly,
                    "is_primary": is_primary,
                    "rotation": rotation,
                }

        displays = []
        for monitor_info, modes, mon_props in monitors:
            connector, vendor, product, serial_num = monitor_info
            is_builtin = mon_props.get("is-builtin", False)

            current_width = 0
            current_height = 0
            current_refresh = 0.0
            parsed_modes = []
            for mode_id, w, h, refresh, preferred_scale, scales, mode_props in modes:
                parsed_modes.append({
                    "mode_id": mode_id,
                    "width": w,
                    "height": h,
                    "refresh": refresh,
                })
                if mode_props.get("is-current"):
                    current_width = w
                    current_height = h
                    current_refresh = refresh
                if mode_props.get("is-preferred") and not current_width:
                    current_width = w
                    current_height = h
                    current_refresh = refresh

            info = active_logical.get(connector, {})
            d = Display(
                name=connector,
                edid_name=mon_props.get("display-name", connector),
                connected=True,
                active=connector in active_logical,
                primary=info.get("is_primary", False),
                width=current_width,
                height=current_height,
                refresh=current_refresh,
                offset_x=info.get("x", 0),
                offset_y=info.get("y", 0),
                rotation=ROTATION_REVERSE.get(info.get("rotation", 0), "normal"),
                modes=parsed_modes,
            )
            displays.append(d)

        return displays

    def get_displays(self) -> list[Display]:
        return self._parse_displays()

    def _active_displays(self) -> list[Display]:
        displays = [d for d in self.get_displays() if d.connected]
        builtin = [d for d in displays if "Built-in" in (d.edid_name or "")]
        others = [d for d in displays if d not in builtin]
        return builtin + others

    def _build_monitor_specs(self, displays: list[Display], width: int, height: int):
        specs = []
        for d in displays:
            mode_id = ""
            for m in d.modes:
                if m["width"] == width and m["height"] == height:
                    mode_id = m["mode_id"]
                    break
            if not mode_id and d.modes:
                mode_id = d.modes[0]["mode_id"]
            specs.append((d.name, mode_id, {}))
        return specs

    def mirror(self, dry_run: bool = False, verbose: bool = False) -> None:
        displays = self._active_displays()
        if not displays:
            return
        primary = next((d for d in displays if d.primary), displays[0])
        serial, monitors, *_ = self._get_state()
        specs = self._build_monitor_specs(displays, primary.width, primary.height)
        logical_monitors = [(0, 0, 1.0, 0, True, specs)]
        self._apply_config(serial, METHOD_TEMPORARY, logical_monitors, {}, dry_run=dry_run)

    def extend(
        self,
        dry_run: bool = False,
        verbose: bool = False,
        primary: Optional[str] = None,
        arrange: str = "left-right",
    ) -> None:
        displays = self._active_displays()
        if not displays:
            return
        serial, *_ = self._get_state()
        if primary:
            primary_disp = next((d for d in displays if d.name == primary), displays[0])
        else:
            primary_disp = next((d for d in displays if d.primary), displays[0])

        sorted_displays = displays
        if arrange == "right-left":
            sorted_displays = list(reversed(displays))

        offset_x = 0
        logical_monitors = []
        for d in sorted_displays:
            specs = self._build_monitor_specs([d], d.width, d.height)
            is_primary = d.name == primary_disp.name
            logical_monitors.append((offset_x, 0, 1.0, 0, is_primary, specs))
            offset_x += d.width

        self._apply_config(serial, METHOD_TEMPORARY, logical_monitors, {}, dry_run=dry_run)

    def second_only(self, dry_run: bool = False, verbose: bool = False) -> None:
        displays = self._active_displays()
        if len(displays) < 2:
            return
        serial, *_ = self._get_state()
        primary = next((d for d in displays if d.primary), displays[0])
        secondary = displays[1] if displays[0].name == primary.name else displays[0]
        specs = self._build_monitor_specs([secondary], secondary.width, secondary.height)
        logical_monitors = [(0, 0, 1.0, 0, True, specs)]
        self._apply_config(serial, METHOD_TEMPORARY, logical_monitors, {}, dry_run=dry_run)

    def pc_only(self, dry_run: bool = False, verbose: bool = False) -> None:
        displays = self._active_displays()
        if not displays:
            return
        serial, *_ = self._get_state()
        target = displays[0]
        specs = self._build_monitor_specs([target], target.width, target.height)
        logical_monitors = [(0, 0, 1.0, 0, True, specs)]
        self._apply_config(serial, METHOD_TEMPORARY, logical_monitors, {}, dry_run=dry_run)

    def set_mode(
        self,
        mode: str,
        primary: Optional[str] = None,
        arrange: str = "left-right",
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        mode_map = {
            "mirror": self.mirror,
            "duplicate": self.mirror,
            "extend": self.extend,
            "second": self.second_only,
            "pc": self.pc_only,
        }
        fn = mode_map.get(mode)
        if fn:
            fn(dry_run=dry_run, verbose=verbose, primary=primary, arrange=arrange)

    def set_brightness(
        self,
        value: int,
        display: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        pass

    def set_resolution(
        self,
        resolution: str,
        display: str,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        displays = self._active_displays()
        target = next((d for d in displays if d.name == display), None)
        if not target:
            return
        serial, *_ = self._get_state()
        w, h = resolution.split("x") if "x" in resolution else (0, 0)
        specs = self._build_monitor_specs([target], int(w), int(h))
        logical_monitors = [(0, 0, 1.0, 0, target.primary, specs)]
        self._apply_config(serial, METHOD_TEMPORARY, logical_monitors, {}, dry_run=dry_run)

    def set_refresh(
        self,
        refresh: int,
        display: str,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        displays = self._active_displays()
        target = next((d for d in displays if d.name == display), None)
        if not target:
            return
        serial, *_ = self._get_state()
        mode_id = ""
        for m in target.modes:
            if abs(m["refresh"] - refresh) < 0.5:
                mode_id = m["mode_id"]
                break
        specs = [(target.name, mode_id, {})]
        logical_monitors = [(0, 0, 1.0, 0, target.primary, specs)]
        self._apply_config(serial, METHOD_TEMPORARY, logical_monitors, {}, dry_run=dry_run)

    def set_rotation(
        self,
        rotation: str,
        display: str,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        displays = self._active_displays()
        target = next((d for d in displays if d.name == display), None)
        if not target:
            return
        serial, *_ = self._get_state()
        r = ROTATION_MAP.get(rotation, 0)
        specs = self._build_monitor_specs([target], target.width, target.height)
        logical_monitors = [(0, 0, 1.0, r, target.primary, specs)]
        self._apply_config(serial, METHOD_TEMPORARY, logical_monitors, {}, dry_run=dry_run)

    def get_active_mode(self) -> str:
        displays = self._active_displays()
        if len(displays) == 0:
            return "none"
        if len(displays) == 1:
            return "pc"
        primaries = [d for d in displays if d.primary]
        if not primaries:
            return "extend"
        primary = primaries[0]
        others = [d for d in displays if d.name != primary.name]
        on_port = [d for d in others if d.active]
        if not on_port:
            return "pc"
        all_same = all(
            d.width == primary.width
            and d.height == primary.height
            and d.offset_x == 0
            and d.offset_y == 0
            for d in on_port
        )
        if all_same and on_port:
            return "mirror"
        secondary_active = any(d.active and not d.primary for d in displays)
        if secondary_active and not primary.active:
            return "second"
        return "extend"
