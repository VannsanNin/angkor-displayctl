from __future__ import annotations
import os
import sys
import subprocess
import logging
import hashlib
from pathlib import Path
from typing import Optional

DATA_DIR = Path.home() / ".local" / "share" / "displayctl"
CONFIG_DIR = Path.home() / ".config" / "displayctl"
SYSTEM_CONFIG = Path("/etc/displayctl/config.json")
PROFILES_FILE = CONFIG_DIR / "profiles.json"
LOG_FILE = DATA_DIR / "displayctl.log"

DRM_PATH = Path("/sys/class/drm")


def setup_logging(verbose: bool = False) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(str(LOG_FILE)),
            logging.StreamHandler(sys.stderr) if verbose else logging.StreamHandler(sys.stderr),
        ],
    )


def detect_session_type() -> str:
    xdg = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if xdg in ("wayland", "x11"):
        return xdg
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    return "x11"


def run_cmd(
    cmd: list[str],
    dry_run: bool = False,
    verbose: bool = False,
    check: bool = True,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    log = logging.getLogger("displayctl")
    cmd_str = " ".join(cmd)
    if verbose:
        log.debug(f"Running: {cmd_str}")
    if dry_run:
        log.info(f"[DRY-RUN] Would run: {cmd_str}")
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            check=False,
            text=True,
        )
        if result.returncode != 0 and check:
            log.error(f"Command failed: {cmd_str}\n{result.stderr.strip()}")
            sys.exit(result.returncode)
        return result
    except FileNotFoundError:
        log.error(f"Command not found: {cmd[0]}")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        log.error(f"Command timed out: {cmd_str}")
        sys.exit(1)


def which(cmd: str) -> Optional[str]:
    return subprocess.run(["which", cmd], capture_output=True, text=True).stdout.strip() or None


def read_edid(connector: str) -> bytes:
    edid_path = DRM_PATH / connector / "edid"
    if edid_path.exists():
        return edid_path.read_bytes()
    drm_dirs = sorted(DRM_PATH.glob(f"*-{connector}"))
    for d in drm_dirs:
        ep = d / "edid"
        if ep.exists():
            return ep.read_bytes()
    return b""


def get_edid_name(connector: str) -> str:
    edid = read_edid(connector)
    if not edid:
        return connector
    try:
        result = subprocess.run(
            ["edid-decode"], input=edid, capture_output=True, timeout=5, check=False
        )
        for line in result.stdout.decode(errors="replace").splitlines():
            if "Monitor Name" in line or "Product Name" in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    return parts[1].strip()
        return connector
    except FileNotFoundError:
        pass
    if len(edid) >= 127:
        name_bytes = edid[119:127]
        name = name_bytes.decode("ascii", errors="replace").strip()
        if name:
            return name
    return connector
