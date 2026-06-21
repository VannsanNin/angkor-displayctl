from __future__ import annotations
import sys
import logging
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box

from displayctl.backends.base import DisplayBackend
from displayctl.profile import save_profile, load_profile, list_profiles, apply_profile_displays

log = logging.getLogger("displayctl")
console = Console()

MENU_ITEMS = [
    ("1", "Mirror", "Duplicate primary to all monitors"),
    ("2", "Extend", "Extend desktop across monitors"),
    ("3", "Second only", "Second screen only"),
    ("4", "PC only", "PC screen only"),
    ("5", "Status", "Show displays + current mode"),
    ("6", "List", "List monitors with details"),
    ("7", "Brightness", "Set brightness (0-100)"),
    ("8", "Save profile", "Save current layout"),
    ("9", "Load profile", "Restore a saved layout"),
    ("p", "Profiles", "List saved profiles"),
    ("w", "Watch", "Start hotplug daemon"),
    ("q", "Quit", "Exit"),
]


def _show_status(backend: DisplayBackend) -> None:
    displays = backend.get_displays()
    mode = backend.get_active_mode()
    table = Table(box=box.ROUNDED)
    table.add_column("Display Name", style="cyan")
    table.add_column("Resolution", style="green")
    table.add_column("Refresh", style="yellow")
    table.add_column("Position", style="magenta")
    table.add_column("Primary", style="blue")
    table.add_column("Active", style="white")
    for d in displays:
        table.add_row(
            d.name,
            d.resolution or ("[dim]disconnected[/]" if not d.connected else ""),
            f"{d.refresh:.2f} Hz" if d.refresh else "",
            d.position or "",
            "[bold]Yes[/]" if d.primary else "",
            "[green]Yes[/]" if d.active else "[red]No[/]",
        )
    console.print(f"\n[bold]Mode:[/] [green]{mode}[/]")
    console.print(table)


def _show_list(backend: DisplayBackend) -> None:
    displays = backend.get_displays()
    for d in displays:
        if d.connected:
            console.print(f"  [cyan]{d.name}[/]  {d.resolution}  {d.refresh:.2f}Hz  "
                          f"pos={d.position}  {'[bold]primary[/]' if d.primary else ''}")
        else:
            console.print(f"  [cyan]{d.name}[/]  [dim]disconnected[/]")


def _show_profiles() -> None:
    names = list_profiles()
    if not names:
        console.print("  [yellow]No saved profiles.[/]")
        return
    for name in names:
        console.print(f"  [cyan]{name}[/]")


def run_tui(backend: DisplayBackend, dry_run: bool = False, verbose: bool = False) -> None:
    if not sys.stdin.isatty():
        console.print("[red]displayctl tui requires an interactive terminal.[/]")
        return

    while True:
        displays = backend.get_displays()
        connected = [d for d in displays if d.connected]
        mode = backend.get_active_mode()

        info = (
            f"[bold cyan]Connected:[/] {len(connected)}  "
            f"[bold cyan]Mode:[/] [green]{mode}[/]"
        )
        if dry_run:
            info += "  [yellow]DRY-RUN[/]"

        lines = []
        for key, label, desc in MENU_ITEMS:
            lines.append(f"  [bold]{key}[/]  {label}  [dim]─ {desc}[/]")

        console.print(Panel(
            f"{info}\n\n" + "\n".join(lines),
            title="[bold]displayctl[/]",
            border_style="cyan",
        ))

        choice = Prompt.ask("[bold]Select[/]", default="q").strip().lower()

        if choice == "q":
            console.print("[dim]Goodbye.[/]")
            break
        elif choice == "1":
            backend.mirror(dry_run=dry_run, verbose=verbose)
        elif choice == "2":
            backend.extend(dry_run=dry_run, verbose=verbose)
        elif choice == "3":
            backend.second_only(dry_run=dry_run, verbose=verbose)
        elif choice == "4":
            try:
                backend.pc_only(dry_run=dry_run, verbose=verbose)
            except Exception as e:
                console.print(f"[red]Error:[/] {e}")
        elif choice == "5":
            _show_status(backend)
        elif choice == "6":
            _show_list(backend)
        elif choice == "7":
            val = Prompt.ask("[yellow]Brightness 0-100[/]", default="80")
            if val.isdigit():
                backend.set_brightness(int(val), dry_run=dry_run, verbose=verbose)
        elif choice == "8":
            name = Prompt.ask("[yellow]Profile name[/]").strip()
            if name:
                save_profile(name, backend.get_displays())
                console.print(f"[green]Profile '{name}' saved.[/]")
        elif choice == "9":
            names = list_profiles()
            if not names:
                console.print("[yellow]No saved profiles.[/]")
            else:
                name = Prompt.ask("[yellow]Profile[/]", choices=names)
                displays = load_profile(name)
                if displays:
                    apply_profile_displays(displays, backend, dry_run=dry_run, verbose=verbose)
                    console.print(f"[green]Profile '{name}' applied.[/]")
        elif choice == "p":
            _show_profiles()
        elif choice == "w":
            from displayctl.hotplug import run_watch
            console.print("[yellow]Starting watch mode... (Ctrl+C to stop)[/]")
            run_watch(backend, trigger=False)
        else:
            console.print("[red]Invalid choice.[/]")

        if choice not in ("q", "w"):
            Prompt.ask("[dim]Press Enter to continue[/]", default="")
