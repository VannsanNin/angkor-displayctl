from __future__ import annotations
import re
import os
from typing import Optional
from displayctl.backends.base import DisplayBackend
from displayctl.display import Display
from displayctl.utils import run_cmd, get_edid_name


class XrandrBackend(DisplayBackend):
    def _parse_xrandr(self) -> list[Display]:
        result = run_cmd(["xrandr"], verbose=False)
        displays: list[Display] = []
        current: Optional[Display] = None
        primary_name = ""

        for line in result.stdout.splitlines():
            m = re.match(r"^(\S+)\s+connected\s+(?:primary\s+)?(\d+)x(\d+)\+(\d+)\+(\d+)", line)
            if m:
                name = m.group(1)
                if "primary" in line:
                    primary_name = name
                w, h, ox, oy = int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
                rotation = "normal"
                rmatch = re.search(r"(normal|left|right|inverted)", line.split("connected")[1])
                if rmatch:
                    rotation = rmatch.group(1)
                edid_name = get_edid_name(name)
                current = Display(
                    name=name, edid_name=edid_name, connected=True,
                    active=True, width=w, height=h, refresh=0.0,
                    offset_x=ox, offset_y=oy, rotation=rotation,
                )
                displays.append(current)
            elif re.match(r"^\S+ disconnected", line):
                name = line.split()[0]
                edid_name = get_edid_name(name)
                displays.append(Display(name=name, edid_name=edid_name, connected=False, active=False))
            elif current and re.match(r"^\s+\d+x\d+", line):
                mm = re.match(r"^\s+(\d+)x(\d+)\s+(\d+\.\d+|\d+)", line)
                if mm:
                    w, h = int(mm.group(1)), int(mm.group(2))
                    refresh = float(mm.group(3))
                    current.modes.append({
                        "width": w,
                        "height": h,
                        "refresh": refresh,
                    })
                    if "*" in line:
                        current.width = w
                        current.height = h
                        current.refresh = refresh

        for d in displays:
            if d.name == primary_name:
                d.primary = True
        return displays

    def get_displays(self) -> list[Display]:
        return self._parse_xrandr()

    def _active_displays(self) -> list[Display]:
        return [d for d in self.get_displays() if d.connected]

    def _get_screen_size(self) -> tuple[int, int]:
        result = run_cmd(["xrandr"], verbose=False)
        m = re.search(r"current\s+(\d+)\s*x\s*(\d+)", result.stdout)
        if m:
            return int(m.group(1)), int(m.group(2))
        return 0, 0

    def mirror(self, dry_run: bool = False, verbose: bool = False) -> None:
        displays = self._active_displays()
        if not displays:
            run_cmd(["xrandr"], dry_run=dry_run, verbose=verbose)
            return
        primary = next((d for d in displays if d.primary), displays[0])
        sw, sh = self._get_screen_size()
        cmd = ["xrandr", "--fb", f"{sw}x{sh}"]
        for d in displays:
            cmd += ["--output", d.name, "--mode", f"{primary.width}x{primary.height}", "--pos", "0x0"]
            if d.name == primary.name:
                cmd += ["--primary"]
        run_cmd(cmd, dry_run=dry_run, verbose=verbose)

    def extend(self, dry_run: bool = False, verbose: bool = False,
               primary: Optional[str] = None, arrange: str = "left-right") -> None:
        displays = self._active_displays()
        if not displays:
            run_cmd(["xrandr"], dry_run=dry_run, verbose=verbose)
            return
        if primary:
            primary_disp = next((d for d in displays if d.name == primary), displays[0])
        else:
            primary_disp = next((d for d in displays if d.primary), displays[0])
        cmd = ["xrandr"]
        offset_x = 0
        sorted_displays = displays
        if arrange == "right-left":
            sorted_displays = list(reversed(displays))
        for d in sorted_displays:
            if d.name == primary_disp.name:
                cmd += ["--output", d.name, "--auto", "--primary", "--pos", f"{offset_x}x0"]
            else:
                cmd += ["--output", d.name, "--auto", "--pos", f"{offset_x}x0"]
            offset_x += d.width
        run_cmd(cmd, dry_run=dry_run, verbose=verbose)

    def second_only(self, dry_run: bool = False, verbose: bool = False) -> None:
        displays = self._active_displays()
        if len(displays) < 2:
            run_cmd(["xrandr"], dry_run=dry_run, verbose=verbose)
            return
        primary = next((d for d in displays if d.primary), displays[0])
        secondary = displays[1] if displays[0].name == primary.name else displays[0]
        cmd = ["xrandr", "--output", primary.name, "--off"]
        cmd += ["--output", secondary.name, "--mode", f"{secondary.width}x{secondary.height}", "--primary"]
        if secondary.refresh:
            cmd += ["--rate", str(int(secondary.refresh))]
        run_cmd(cmd, dry_run=dry_run, verbose=verbose)

    def pc_only(self, dry_run: bool = False, verbose: bool = False) -> None:
        displays = self._active_displays()
        primary = next((d for d in displays if d.primary), displays[0] if displays else None)
        if not primary:
            run_cmd(["xrandr"], dry_run=dry_run, verbose=verbose)
            return
        cmd = ["xrandr"]
        for d in displays:
            if d.name != primary.name:
                cmd += ["--output", d.name, "--off"]
        cmd += ["--output", primary.name, "--mode", f"{primary.width}x{primary.height}", "--primary"]
        if primary.refresh:
            cmd += ["--rate", str(int(primary.refresh))]
        run_cmd(cmd, dry_run=dry_run, verbose=verbose)

    def set_mode(self, mode: str, primary: Optional[str] = None,
                 arrange: str = "left-right",
                 dry_run: bool = False, verbose: bool = False) -> None:
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

    def set_brightness(self, value: int, display: Optional[str] = None,
                       dry_run: bool = False, verbose: bool = False) -> None:
        brightness = max(0, min(100, value)) / 100.0
        displays = self._active_displays()
        if display:
            targets = [d for d in displays if d.name == display]
        else:
            targets = displays
        for d in targets:
            run_cmd(["xrandr", "--output", d.name, "--brightness", f"{brightness}"],
                    dry_run=dry_run, verbose=verbose)

    def set_resolution(self, resolution: str, display: str,
                       dry_run: bool = False, verbose: bool = False) -> None:
        run_cmd(["xrandr", "--output", display, "--mode", resolution],
                dry_run=dry_run, verbose=verbose)

    def set_refresh(self, refresh: int, display: str,
                    dry_run: bool = False, verbose: bool = False) -> None:
        run_cmd(["xrandr", "--output", display, "--rate", str(refresh)],
                dry_run=dry_run, verbose=verbose)

    def set_rotation(self, rotation: str, display: str,
                     dry_run: bool = False, verbose: bool = False) -> None:
        run_cmd(["xrandr", "--output", display, "--rotate", rotation],
                dry_run=dry_run, verbose=verbose)

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
        all_same = all(d.width == primary.width and d.height == primary.height and
                      d.offset_x == 0 and d.offset_y == 0 for d in on_port)
        if all_same and on_port:
            return "mirror"
        secondary_active = any(d.active and not d.primary for d in displays)
        if secondary_active and not primary.active:
            return "second"
        return "extend"
