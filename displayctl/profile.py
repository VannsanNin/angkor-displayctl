from __future__ import annotations
import json
import logging
from typing import Optional, TYPE_CHECKING
from displayctl.display import Display
from displayctl.utils import PROFILES_FILE

if TYPE_CHECKING:
    from displayctl.backends.base import DisplayBackend

log = logging.getLogger("displayctl")


def _ensure_config_dir():
    PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_profiles_raw() -> dict:
    _ensure_config_dir()
    if PROFILES_FILE.exists():
        try:
            return json.loads(PROFILES_FILE.read_text())
        except (json.JSONDecodeError, OSError) as e:
            log.error(f"Failed to load profiles: {e}")
            return {}
    return {}


def _save_profiles_raw(data: dict) -> None:
    _ensure_config_dir()
    PROFILES_FILE.write_text(json.dumps(data, indent=2))


def save_profile(name: str, displays: list[Display]) -> None:
    profiles = _load_profiles_raw()
    profile_data = {
        "displays": [d.to_dict() for d in displays],
        "fingerprints": {d.name: d.fingerprint() for d in displays if d.connected},
    }
    profiles[name] = profile_data
    _save_profiles_raw(profiles)
    log.info(f"Saved profile '{name}' with {len(displays)} display(s)")


def load_profile(name: str) -> Optional[list[Display]]:
    profiles = _load_profiles_raw()
    data = profiles.get(name)
    if not data:
        log.error(f"Profile '{name}' not found")
        return None
    displays = [Display.from_dict(d) for d in data.get("displays", [])]
    log.info(f"Loaded profile '{name}' with {len(displays)} display(s)")
    return displays


def list_profiles() -> list[str]:
    return sorted(_load_profiles_raw().keys())


def delete_profile(name: str) -> bool:
    profiles = _load_profiles_raw()
    if name not in profiles:
        log.error(f"Profile '{name}' not found")
        return False
    del profiles[name]
    _save_profiles_raw(profiles)
    log.info(f"Deleted profile '{name}'")
    return True


def apply_profile_displays(displays: list[Display], backend: "DisplayBackend",
                            dry_run: bool = False, verbose: bool = False) -> None:
    for d in displays:
        if d.connected and d.width and d.height:
            from displayctl.backends import get_backend
            actual_backend = backend
            actual_backend.set_resolution(f"{d.width}x{d.height}", d.name, dry_run=dry_run, verbose=verbose)
            if d.rotation and d.rotation != "normal":
                actual_backend.set_rotation(d.rotation, d.name, dry_run=dry_run, verbose=verbose)


def find_matching_profile(connected_fingerprints: set[str]) -> Optional[str]:
    profiles = _load_profiles_raw()
    for name, data in profiles.items():
        stored = set(data.get("fingerprints", {}).values())
        if stored and stored == connected_fingerprints:
            return name
    return None
