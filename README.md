# displayctl

Multi-monitor display mode controller for Linux. Supports X11 (xrandr) and Wayland (wlr-randr/swaymsg) with automatic backend detection.

## Features

- **Display modes**: Mirror, Extend, Second Screen Only, PC Screen Only
- **Dual backend**: X11 via xrandr, Wayland via wlr-randr/swaymsg (auto-detected)
- **Profile system**: Save/load layouts with EDID fingerprinting (port-independent)
- **Hotplug daemon**: Auto-apply profiles on monitor connect/disconnect via udev
- **Rich terminal UI**: Colored tables for status and list output
- **CLI polish**: Dry-run, verbose mode, per-command help with examples

## Installation

### From APT repository

```bash
# Add GPG key
curl -fsSL https://vannsannin.github.io/angkor-displayctl/gpg.key \
  | sudo gpg --dearmor -o /usr/share/keyrings/displayctl.gpg

# Add repository
echo "deb [signed-by=/usr/share/keyrings/displayctl.gpg] https://vannsannin.github.io/angkor-displayctl jammy main" \
  | sudo tee /etc/apt/sources.list.d/displayctl.list

# Install
sudo apt update && sudo apt install displayctl
```

### From source

```bash
git clone https://github.com/displayctl/displayctl.git
cd displayctl
make install
```

### Build .deb package

```bash
make deb
# or
./scripts/build-deb.sh
```

## Usage

### Display modes

```bash
displayctl mirror                   # Duplicate all screens
displayctl extend                   # Extend desktop across monitors
displayctl second                   # Second screen only
displayctl pc                       # PC screen only
displayctl set --mode extend --primary HDMI-1 --arrange left-right
```

### Information

```bash
displayctl status                   # Rich table of displays + current mode
displayctl list                     # List monitors with details
```

### Display control

```bash
displayctl brightness 80            # Set brightness 0-100 (all displays)
displayctl brightness 50 --display HDMI-1
displayctl resolution 1920x1080 --display HDMI-1
displayctl refresh 144 --display DP-1
displayctl rotate normal --display HDMI-1
displayctl rotate left --display HDMI-1
```

### Profiles

```bash
displayctl save --profile home      # Save current layout
displayctl load --profile home      # Restore saved layout
displayctl profiles                 # List saved profiles
displayctl delete --profile home    # Delete a profile
```

### Hotplug daemon

```bash
displayctl watch                    # Run as daemon (auto-apply profile on hotplug)

# Enable at login via systemd user service:
systemctl --user enable displayctl-watch
systemctl --user start displayctl-watch
```

### Global flags

```
-v, --verbose     Show raw backend commands
--dry-run         Print commands without executing
--version         Show version
--help            Show help
```

## Backends

| Session | Backend | Detection |
|---------|---------|-----------|
| X11     | xrandr  | `$XDG_SESSION_TYPE` or default |
| Wayland | wlr-randr / swaymsg | `$WAYLAND_DISPLAY` or `$XDG_SESSION_TYPE` |

## Configuration

- **User config**: `~/.config/displayctl/profiles.json`
- **System config**: `/etc/displayctl/config.json`
- **Logs**: `~/.local/share/displayctl/displayctl.log`

## Development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Project structure

```
displayctl/
├── displayctl/           # Python package
│   ├── cli.py            # Click CLI
│   ├── display.py        # Display model
│   ├── profile.py        # Profile save/load
│   ├── hotplug.py        # udev hotplug watcher
│   ├── utils.py          # Helpers
│   └── backends/         # X11 + Wayland backends
├── tests/                # pytest tests
├── debian/               # Debian packaging
├── scripts/              # Build and repo scripts
├── apt-repo/             # APT repository structure
├── setup.py / pyproject.toml
└── Makefile
```

## License

MIT
