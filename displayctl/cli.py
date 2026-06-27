from __future__ import annotations
import sys
import logging
from typing import Optional

import click
import rich_click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from displayctl import __version__, __app_name__
from displayctl.display import Display
from displayctl.backends import get_backend
from displayctl.backends.base import DisplayBackend
from displayctl.profile import save_profile, load_profile, list_profiles, delete_profile, apply_profile_displays
from displayctl.hotplug import run_watch
from displayctl.tui import run_tui as curses_tui
from displayctl.utils import setup_logging

console = Console(stderr=True)
log = logging.getLogger("displayctl")

rich_click.RichHelpConfiguration.arguments_panel_title = "Arguments"
rich_click.RichHelpConfiguration.options_panel_title = "Options"
rich_click.RichHelpConfiguration.commands_panel_title = "Commands"
rich_click.RichHelpConfiguration.show_arguments = True
rich_click.RichHelpConfiguration.use_rich_markup = True
rich_click.RichHelpConfiguration.header_text = "[bold cyan]displayctl[/] - Multi-monitor display mode controller"
rich_click.RichHelpConfiguration.footer_text = "[dim]Report issues at https://github.com/VannsanNin/angkor-displayctl[/]"


def _get_backend(verbose: bool = False) -> DisplayBackend:
    setup_logging(verbose=verbose)
    return get_backend()


def _print_displays_table(displays: list[Display]) -> None:
    table = Table(box=box.ROUNDED, title="Monitors", title_style="bold")
    table.add_column("Display Name", style="cyan")
    table.add_column("Resolution", style="green")
    table.add_column("Refresh", style="yellow")
    table.add_column("Position", style="magenta")
    table.add_column("Primary", style="blue")
    table.add_column("Active", style="white")
    for d in displays:
        table.add_row(
            d.name,
            d.resolution or ("[dim]disconnected[/]" if not d.connected else "[dim]unknown[/]"),
            f"{d.refresh:.2f} Hz" if d.refresh else "",
            d.position or "",
            "[bold]Yes[/]" if d.primary else "",
            "[green]Yes[/]" if d.active else "[red]No[/]",
        )
    console.print(table)


def _print_displays_list(displays: list[Display]) -> None:
    for d in displays:
        if d.connected:
            console.print(f"[cyan]{d.name}[/]  {d.resolution}  {d.refresh:.2f}Hz  pos={d.position}  "
                          f"{'[bold]primary[/]' if d.primary else ''}  "
                          f"edid=[dim]{d.edid_name}[/]")
        else:
            console.print(f"[cyan]{d.name}[/]  [dim]disconnected[/]")


@click.group(invoke_without_command=False, cls=rich_click.RichGroup)
@click.version_option(version=__version__, prog_name=__app_name__)
@click.option("-v", "--verbose", is_flag=True, help="Show raw backend commands")
@click.option("--dry-run", is_flag=True, help="Print commands without executing")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, dry_run: bool) -> None:
    """Multi-monitor display mode controller.

    Control display modes, resolutions, brightness, and save/load display profiles.
    Works on X11 (xrandr) and Wayland (wlr-randr / GNOME).
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["dry_run"] = dry_run
    ctx.obj["backend"] = _get_backend(verbose=verbose)


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show current display layout and active mode."""
    backend: DisplayBackend = ctx.obj["backend"]
    displays = backend.get_displays()
    mode = backend.get_active_mode()
    panel = Panel(f"[bold]Current mode:[/] [green]{mode}[/]", expand=False)
    console.print(panel)
    console.print()
    _print_displays_table(displays)


@cli.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List all displays and their properties."""
    backend: DisplayBackend = ctx.obj["backend"]
    displays = backend.get_displays()
    console.print("[bold]Connected displays:[/]")
    _print_displays_list(displays)


@cli.command()
@click.pass_context
@click.option("--primary", default=None, help="Set primary display")
@click.option("--arrange", type=click.Choice(["left-right", "right-left"]), default="left-right", help="Arrangement")
def mirror(ctx: click.Context, primary: Optional[str], arrange: str) -> None:
    """Mirror all displays (same content on every screen)."""
    backend: DisplayBackend = ctx.obj["backend"]
    backend.mirror(dry_run=ctx.obj["dry_run"], verbose=ctx.obj["verbose"])
    if not ctx.obj["dry_run"]:
        console.print("[green]Displays mirrored[/]")


@cli.command()
@click.pass_context
@click.option("--primary", default=None, help="Set primary display")
@click.option("--arrange", type=click.Choice(["left-right", "right-left"]), default="left-right")
def extend(ctx: click.Context, primary: Optional[str], arrange: str) -> None:
    """Extend desktop across all displays."""
    backend: DisplayBackend = ctx.obj["backend"]
    backend.extend(dry_run=ctx.obj["dry_run"], verbose=ctx.obj["verbose"],
                   primary=primary, arrange=arrange)
    if not ctx.obj["dry_run"]:
        console.print("[green]Desktop extended across displays[/]")


@cli.command()
@click.pass_context
def second(ctx: click.Context) -> None:
    """Show content only on the secondary display."""
    backend: DisplayBackend = ctx.obj["backend"]
    backend.second_only(dry_run=ctx.obj["dry_run"], verbose=ctx.obj["verbose"])
    if not ctx.obj["dry_run"]:
        console.print("[green]Switched to second display only[/]")


@cli.command()
@click.pass_context
def pc(ctx: click.Context) -> None:
    """Show content only on the primary (built-in) display."""
    backend: DisplayBackend = ctx.obj["backend"]
    backend.pc_only(dry_run=ctx.obj["dry_run"], verbose=ctx.obj["verbose"])
    if not ctx.obj["dry_run"]:
        console.print("[green]Switched to primary display only[/]")


@cli.command()
@click.pass_context
@click.option("--mode", required=True, type=click.Choice(["mirror", "duplicate", "extend", "second", "pc"]), help="Display mode")
@click.option("--primary", default=None, help="Primary display name")
@click.option("--arrange", type=click.Choice(["left-right", "right-left"]), default="left-right")
def set(ctx: click.Context, mode: str, primary: Optional[str], arrange: str) -> None:
    """Set display mode (alias for mirror/extend/second/pc)."""
    backend: DisplayBackend = ctx.obj["backend"]
    backend.set_mode(mode, primary=primary, arrange=arrange,
                     dry_run=ctx.obj["dry_run"], verbose=ctx.obj["verbose"])
    if not ctx.obj["dry_run"]:
        console.print(f"[green]Mode set to:[/] [cyan]{mode}[/]")


@cli.command()
@click.pass_context
@click.argument("value", type=int)
@click.option("--display", default=None, help="Display name (default: all)")
def brightness(ctx: click.Context, value: int, display: Optional[str]) -> None:
    """Set display brightness (0-100)."""
    backend: DisplayBackend = ctx.obj["backend"]
    backend.set_brightness(value, display=display,
                           dry_run=ctx.obj["dry_run"], verbose=ctx.obj["verbose"])
    if not ctx.obj["dry_run"]:
        target = f" [dim]{display}[/]" if display else ""
        console.print(f"[green]Brightness set to[/] [cyan]{value}%{target}[/]")


@cli.command()
@click.pass_context
@click.argument("resolution", type=str)
@click.option("--display", required=True, help="Display name")
def resolution(ctx: click.Context, resolution: str, display: str) -> None:
    """Set display resolution (e.g. 1920x1080)."""
    backend: DisplayBackend = ctx.obj["backend"]
    backend.set_resolution(resolution, display,
                           dry_run=ctx.obj["dry_run"], verbose=ctx.obj["verbose"])
    if not ctx.obj["dry_run"]:
        console.print(f"[green]{display}[/] resolution set to [cyan]{resolution}[/]")


@cli.command()
@click.pass_context
@click.argument("refresh", type=int)
@click.option("--display", required=True, help="Display name")
def refresh(ctx: click.Context, refresh: int, display: str) -> None:
    """Set display refresh rate in Hz."""
    backend: DisplayBackend = ctx.obj["backend"]
    backend.set_refresh(refresh, display,
                        dry_run=ctx.obj["dry_run"], verbose=ctx.obj["verbose"])
    if not ctx.obj["dry_run"]:
        console.print(f"[green]{display}[/] refresh set to [cyan]{refresh}Hz[/]")


@cli.command()
@click.pass_context
@click.argument("rotation", type=click.Choice(["normal", "left", "right", "inverted"]))
@click.option("--display", required=True, help="Display name")
def rotate(ctx: click.Context, rotation: str, display: str) -> None:
    """Rotate a display (normal, left, right, inverted)."""
    backend: DisplayBackend = ctx.obj["backend"]
    backend.set_rotation(rotation, display,
                         dry_run=ctx.obj["dry_run"], verbose=ctx.obj["verbose"])
    if not ctx.obj["dry_run"]:
        console.print(f"[green]{display}[/] rotated to [cyan]{rotation}[/]")


@cli.command()
@click.pass_context
@click.option("--profile", required=True, help="Profile name")
def save(ctx: click.Context, profile: str) -> None:
    """Save current display layout as a profile."""
    backend: DisplayBackend = ctx.obj["backend"]
    displays = backend.get_displays()
    save_profile(profile, displays)
    console.print(f"[green]Profile[/] [cyan]{profile}[/] [green]saved.[/]")


@cli.command()
@click.pass_context
@click.option("--profile", required=True, help="Profile name")
def load(ctx: click.Context, profile: str) -> None:
    """Apply a saved display profile."""
    backend: DisplayBackend = ctx.obj["backend"]
    displays = load_profile(profile)
    if displays is None:
        console.print(f"[red]Profile[/] [cyan]{profile}[/] [red]not found.[/]")
        sys.exit(1)
    apply_profile_displays(displays, backend,
                            dry_run=ctx.obj["dry_run"], verbose=ctx.obj["verbose"])
    console.print(f"[green]Profile[/] [cyan]{profile}[/] [green]applied.[/]")


@cli.command()
@click.pass_context
def profiles(ctx: click.Context) -> None:
    """List all saved display profiles."""
    names = list_profiles()
    if not names:
        console.print("[yellow]No saved profiles.[/]")
        return
    console.print("[bold]Saved profiles:[/]")
    for name in names:
        console.print(f"  [cyan]{name}[/]")


@cli.command()
@click.pass_context
@click.option("--profile", required=True, help="Profile name to delete")
def delete(ctx: click.Context, profile: str) -> None:
    """Delete a saved display profile."""
    if delete_profile(profile):
        console.print(f"[green]Profile[/] [cyan]{profile}[/] [green]deleted.[/]")
    else:
        console.print(f"[red]Profile[/] [cyan]{profile}[/] [red]not found.[/]")
        sys.exit(1)


@cli.command()
@click.pass_context
@click.option("--trigger", is_flag=True, help="Trigger hotplug action once (used by udev)")
def watch(ctx: click.Context, trigger: bool) -> None:
    """Watch for display hotplug events and auto-apply profiles."""
    backend: DisplayBackend = ctx.obj["backend"]
    run_watch(backend, trigger=trigger)


@cli.command()
@click.pass_context
def tui(ctx: click.Context) -> None:
    """Launch the terminal-based TUI."""
    backend: DisplayBackend = ctx.obj["backend"]
    dry_run = ctx.obj["dry_run"]
    verbose = ctx.obj["verbose"]
    curses_tui(backend, dry_run=dry_run, verbose=verbose)


@cli.command()
def gui() -> None:
    """Launch the modern GTK4 GUI application."""
    from displayctl.gui import run_gui
    run_gui()


def main() -> None:
    cli(auto_envvar_prefix="DISPLAYCTL")


if __name__ == "__main__":
    main()
