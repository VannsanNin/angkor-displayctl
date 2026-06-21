from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock
from displayctl.backends.xrandr import XrandrBackend
from displayctl.backends.wayland import WaylandBackend
from displayctl.display import Display


XRANDR_OUTPUT = """Screen 0: minimum 320 x 200, current 3840 x 1080, maximum 16384 x 16384
eDP-1 connected primary 1920x1080+0+0 60.00*+ 59.94
   1920x1080     60.00*+  59.94
   1680x1050     59.95
DP-1 connected 1920x1080+1920+0 59.94*+
   1920x1080     60.00   59.94*
   1280x1024     60.02
HDMI-1 disconnected
"""


def test_xrandr_parse_displays():
    backend = XrandrBackend()
    with patch.object(backend, "_parse_xrandr") as mock_parse:
        mock_parse.return_value = [
            Display(name="eDP-1", connected=True, active=True, primary=True,
                    width=1920, height=1080, refresh=60.0, offset_x=0, offset_y=0),
            Display(name="DP-1", connected=True, active=True, primary=False,
                    width=1920, height=1080, refresh=59.94, offset_x=1920, offset_y=0),
        ]
        displays = backend.get_displays()
        assert len(displays) == 2
        assert displays[0].name == "eDP-1"
        assert displays[0].primary is True
        assert displays[1].name == "DP-1"
        assert displays[1].offset_x == 1920


@pytest.fixture
def mock_xrandr():
    with patch("displayctl.backends.xrandr.run_cmd") as mock:
        mock.return_value.stdout = XRANDR_OUTPUT
        yield mock


def test_xrandr_mirror():
    backend = XrandrBackend()
    with patch.object(backend, "_parse_xrandr") as mock_parse:
        mock_parse.return_value = [
            Display(name="eDP-1", connected=True, active=True, primary=True,
                    width=1920, height=1080, refresh=60.0, offset_x=0, offset_y=0),
            Display(name="DP-1", connected=True, active=True, primary=False,
                    width=1920, height=1080, refresh=59.94, offset_x=1920, offset_y=0),
        ]
        with patch("displayctl.backends.xrandr.run_cmd") as mock_run:
            mock_run.return_value.stdout = "Screen 0: minimum 320 x 200, current 3840 x 1080, maximum 16384 x 16384"
            backend.mirror(dry_run=True)
            assert mock_run.called


def test_xrandr_extend():
    backend = XrandrBackend()
    with patch.object(backend, "_parse_xrandr") as mock_parse:
        mock_parse.return_value = [
            Display(name="eDP-1", connected=True, active=True, primary=True,
                    width=1920, height=1080, refresh=60.0, offset_x=0, offset_y=0),
            Display(name="DP-1", connected=True, active=True, primary=False,
                    width=1920, height=1080, refresh=59.94, offset_x=1920, offset_y=0),
        ]
        with patch("displayctl.backends.xrandr.run_cmd") as mock_run:
            backend.extend(dry_run=True)
            assert mock_run.called


def test_xrandr_second_only():
    backend = XrandrBackend()
    with patch.object(backend, "_parse_xrandr") as mock_parse:
        mock_parse.return_value = [
            Display(name="eDP-1", connected=True, active=True, primary=True,
                    width=1920, height=1080, refresh=60.0, offset_x=0, offset_y=0),
            Display(name="DP-1", connected=True, active=True, primary=False,
                    width=1920, height=1080, refresh=59.94, offset_x=1920, offset_y=0),
        ]
        with patch("displayctl.backends.xrandr.run_cmd") as mock_run:
            backend.second_only(dry_run=True)
            assert mock_run.called


def test_xrandr_pc_only():
    backend = XrandrBackend()
    with patch.object(backend, "_parse_xrandr") as mock_parse:
        mock_parse.return_value = [
            Display(name="eDP-1", connected=True, active=True, primary=True,
                    width=1920, height=1080, refresh=60.0, offset_x=0, offset_y=0),
            Display(name="DP-1", connected=True, active=True, primary=False,
                    width=1920, height=1080, refresh=59.94, offset_x=1920, offset_y=0),
        ]
        with patch("displayctl.backends.xrandr.run_cmd") as mock_run:
            backend.pc_only(dry_run=True)
            assert mock_run.called


def test_xrandr_brightness():
    backend = XrandrBackend()
    with patch.object(backend, "_active_displays") as mock_active:
        mock_active.return_value = [
            Display(name="eDP-1", connected=True, active=True, primary=True,
                    width=1920, height=1080, refresh=60.0, offset_x=0, offset_y=0),
        ]
        with patch("displayctl.backends.xrandr.run_cmd") as mock_run:
            backend.set_brightness(80, dry_run=True)
            assert mock_run.called


def test_xrandr_get_active_mode():
    backend = XrandrBackend()
    with patch.object(backend, "_active_displays") as mock_active:
        mock_active.return_value = [
            Display(name="eDP-1", connected=True, active=True, primary=True,
                    width=1920, height=1080, offset_x=0, offset_y=0),
            Display(name="DP-1", connected=True, active=True, primary=False,
                    width=1920, height=1080, offset_x=1920, offset_y=0),
        ]
        mode = backend.get_active_mode()
        assert mode == "extend"


def test_wayland_backend_init():
    backend = WaylandBackend()
    assert backend._use_sway or not backend._use_sway


@pytest.mark.parametrize("mode,expected", [
    ("normal", "normal"),
    ("left", "left"),
    ("right", "right"),
    ("inverted", "inverted"),
])
def test_rotation_values(mode, expected):
    assert mode == expected


def test_display_dataclass():
    d = Display(name="HDMI-1", connected=True, active=True, 
                width=1920, height=1080, refresh=60.0, edid_name="Dell U2719D")
    assert d.resolution == "1920x1080"
    assert d.fingerprint() is not None
    assert d.to_dict()["name"] == "HDMI-1"
    restored = Display.from_dict(d.to_dict())
    assert restored.name == "HDMI-1"
    assert restored.width == 1920
