from __future__ import annotations
import json
import re
from typing import Optional
from displayctl.backends.base import DisplayBackend
from displayctl.display import Display
from displayctl.utils import run_cmd, which


class WaylandBackend(DisplayBackend):
    def __init__(self):
        self._use_sway = which("swaymsg") is not None
        self._use_wlr = which("wlr-randr") is not None

    def _parse_wlr_randr(self) -> list[Display]:
        if not self._use_wlr:
            return []
        result = run_cmd(["wlr-randr"], verbose=False, check=False)
        if result.returncode != 0:
            return []
        displays: list[Display] = []
        current: Optional[Display] = None

        for line in result.stdout.splitlines():
            m = re.match(r"^(\S+)\s+\"(.*?)\"", line)
            if m:
                if current:
                    displays.append(current)
                current = Display(name=m.group(1), edid_name=m.group(2), connected=True, active=True)
                continue
            if current:
                mm = re.match(r"^\s+(\d+)x(\d+)\s+@\s+(\d+\.\d+|\d+)\s+Hz\s+.*?position\s+(\d+),(\d+)", line)
                if mm:
                    current.width = int(mm.group(1))
                    current.height = int(mm.group(2))
                    current.refresh = float(mm.group(3))
                    current.offset_x = int(mm.group(4))
                    current.offset_y = int(mm.group(5))
                rm = re.match(r"^\s+transform:\s+(normal|left|right|inverted)", line)
                if rm:
                    current.rotation = rm.group(1)
                pm = re.match(r"^\s+Scale:", line)
                if pm:
                    current.primary = True
        if current:
            displays.append(current)
        return displays

    def get_displays(self) -> list[Display]:
        return self._parse_wlr_randr()

    def _active_displays(self) -> list[Display]:
        return [d for d in self.get_displays() if d.connected]

    def _wlr_cmd(self, cmd: list[str], dry_run: bool = False, verbose: bool = False):
        run_cmd(["wlr-randr"] + cmd, dry_run=dry_run, verbose=verbose)

    def mirror(self, dry_run: bool = False, verbose: bool = False) -> None:
        displays = self._active_displays()
        if not displays:
            return
        primary = next((d for d in displays if d.primary), displays[0])
        if self._use_wlr:
            for d in displays:
                if d.name == primary.name:
                    self._wlr_cmd(["--output", d.name, "--mode", f"{primary.width}x{primary.height}@{primary.refresh}Hz"], dry_run, verbose)
                else:
                    self._wlr_cmd(["--output", d.name, "--mode", f"{primary.width}x{primary.height}@{primary.refresh}Hz", "--pos", "0,0"], dry_run, verbose)
        elif self._use_sway:
            cfg = f'output "*" disable; output {primary.name} enable'
            for d in displays:
                if d.name != primary.name:
                    cfg += f"; output {d.name} enable mode {primary.width}x{primary.height} position 0 0"
            run_cmd(["swaymsg", cfg], dry_run=dry_run, verbose=verbose)

    def extend(self, dry_run: bool = False, verbose: bool = False,
               primary: Optional[str] = None, arrange: str = "left-right") -> None:
        displays = self._active_displays()
        if not displays:
            return
        if primary:
            primary_disp = next((d for d in displays if d.name == primary), displays[0])
        else:
            primary_disp = next((d for d in displays if d.primary), displays[0])
        sorted_disp = displays if arrange == "left-right" else list(reversed(displays))
        offset_x = 0
        if self._use_wlr:
            for d in sorted_disp:
                self._wlr_cmd(["--output", d.name, "--mode", f"{d.width}x{d.height}@{d.refresh}Hz", "--pos", f"{offset_x},0"], dry_run, verbose)
                offset_x += d.width
        elif self._use_sway:
            cfg = ""
            for d in sorted_disp:
                cfg += f"output {d.name} enable mode {d.width}x{d.height} position {offset_x} 0; "
                offset_x += d.width
            run_cmd(["swaymsg", cfg], dry_run=dry_run, verbose=verbose)

    def second_only(self, dry_run: bool = False, verbose: bool = False) -> None:
        displays = self._active_displays()
        if len(displays) < 2:
            return
        primary = next((d for d in displays if d.primary), displays[0])
        secondary = displays[1] if displays[0].name == primary.name else displays[0]
        if self._use_wlr:
            self._wlr_cmd(["--output", primary.name, "--off"], dry_run, verbose)
            self._wlr_cmd(["--output", secondary.name, "--mode", f"{secondary.width}x{secondary.height}@{secondary.refresh}Hz", "--pos", "0,0"], dry_run, verbose)
        elif self._use_sway:
            run_cmd(["swaymsg", f'output {primary.name} disable; output {secondary.name} enable'], dry_run=dry_run, verbose=verbose)

    def pc_only(self, dry_run: bool = False, verbose: bool = False) -> None:
        displays = self._active_displays()
        primary = next((d for d in displays if d.primary), displays[0] if displays else None)
        if not primary:
            return
        if self._use_wlr:
            self._wlr_cmd(["--output", primary.name, "--mode", f"{primary.width}x{primary.height}@{primary.refresh}Hz", "--pos", "0,0"], dry_run, verbose)
            for d in displays:
                if d.name != primary.name:
                    self._wlr_cmd(["--output", d.name, "--off"], dry_run, verbose)
        elif self._use_sway:
            cfg = f'output {primary.name} enable'
            for d in displays:
                if d.name != primary.name:
                    cfg += f"; output {d.name} disable"
            run_cmd(["swaymsg", cfg], dry_run=dry_run, verbose=verbose)

    def set_mode(self, mode: str, primary: Optional[str] = None,
                 arrange: str = "left-right",
                 dry_run: bool = False, verbose: bool = False) -> None:
        if mode in ("mirror", "duplicate"):
            self.mirror(dry_run=dry_run, verbose=verbose)
        elif mode == "extend":
            self.extend(
                dry_run=dry_run,
                verbose=verbose,
                primary=primary,
                arrange=arrange,
            )
        elif mode == "second":
            self.second_only(dry_run=dry_run, verbose=verbose)
        elif mode == "pc":
            self.pc_only(dry_run=dry_run, verbose=verbose)

    def set_brightness(self, value: int, display: Optional[str] = None,
                       dry_run: bool = False, verbose: bool = False) -> None:
        import logging
        log = logging.getLogger("displayctl")
        log.warning("Brightness control not fully supported on Wayland. Use wlroots-gamma or ddcutil.")

    def set_resolution(self, resolution: str, display: str,
                       dry_run: bool = False, verbose: bool = False) -> None:
        if self._use_wlr:
            self._wlr_cmd(["--output", display, "--mode", resolution], dry_run, verbose)
        elif self._use_sway:
            run_cmd(["swaymsg", f'output {display} mode {resolution}'], dry_run=dry_run, verbose=verbose)

    def set_refresh(self, refresh: int, display: str,
                    dry_run: bool = False, verbose: bool = False) -> None:
        if self._use_wlr:
            self._wlr_cmd(["--output", display, "--mode", f"@{refresh}Hz"], dry_run, verbose)
        elif self._use_sway:
            run_cmd(["swaymsg", f'output {display} max_render_time 1'], dry_run=dry_run, verbose=verbose)
            log = logging.getLogger("displayctl")
            log.warning("Refresh rate control on sway requires manual wlr-randr usage.")

    def set_rotation(self, rotation: str, display: str,
                     dry_run: bool = False, verbose: bool = False) -> None:
        if self._use_wlr:
            self._wlr_cmd(["--output", display, "--transform", rotation], dry_run, verbose)
        elif self._use_sway:
            run_cmd(["swaymsg", f'output {display} transform {rotation}'], dry_run=dry_run, verbose=verbose)

    def get_active_mode(self) -> str:
        displays = self._active_displays()
        if len(displays) == 0:
            return "none"
        if len(displays) == 1:
            return "pc"
        primaries = [d for d in displays if d.primary]
        primary = primaries[0] if primaries else displays[0]
        others = [d for d in displays if d.name != primary.name]
        on_port = [d for d in others if d.active]
        if not on_port:
            return "pc"
        all_same = all(d.width == primary.width and d.height == primary.height for d in on_port)
        if all_same and on_port:
            return "mirror"
        secondary_active = any(d.active and d.name != primary.name for d in displays)
        if secondary_active and not primary.active:
            return "second"
        return "extend"
