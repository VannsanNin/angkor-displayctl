from __future__ import annotations
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from displayctl.profile import save_profile, load_profile, list_profiles, delete_profile, find_matching_profile
from displayctl.display import Display


@pytest.fixture
def mock_profiles_file(tmp_path):
    profiles_path = tmp_path / "profiles.json"
    with patch("displayctl.profile.PROFILES_FILE", profiles_path):
        profiles_path.parent.mkdir(parents=True, exist_ok=True)
        yield profiles_path


def test_save_and_load_profile(mock_profiles_file):
    displays = [
        Display(name="eDP-1", connected=True, active=True, primary=True,
                width=1920, height=1080, refresh=60.0, offset_x=0, offset_y=0),
        Display(name="DP-1", connected=True, active=True, primary=False,
                width=1920, height=1080, refresh=59.94, offset_x=1920, offset_y=0),
    ]
    save_profile("test_profile", displays)
    loaded = load_profile("test_profile")
    assert loaded is not None
    assert len(loaded) == 2
    assert loaded[0].name == "eDP-1"
    assert loaded[0].width == 1920


def test_list_profiles(mock_profiles_file):
    displays = [Display(name="eDP-1", connected=True, active=True)]
    save_profile("profile_a", displays)
    save_profile("profile_b", displays)
    names = list_profiles()
    assert "profile_a" in names
    assert "profile_b" in names


def test_delete_profile(mock_profiles_file):
    displays = [Display(name="eDP-1", connected=True, active=True)]
    save_profile("to_delete", displays)
    assert delete_profile("to_delete") is True
    assert delete_profile("nonexistent") is False
    assert "to_delete" not in list_profiles()


def test_find_matching_profile(mock_profiles_file):
    displays = [Display(name="eDP-1", connected=True, active=True, edid_hash="abc123")]
    save_profile("home", displays)
    result = find_matching_profile({"abc123"})
    assert result == "home"
    result = find_matching_profile({"xyz789"})
    assert result is None


def test_save_with_fingerprints(mock_profiles_file):
    displays = [Display(name="eDP-1", connected=True, active=True, edid_hash="abc")]
    save_profile("fp_test", displays)
    data = json.loads(mock_profiles_file.read_text())
    assert "fingerprints" in data["fp_test"]
    assert data["fp_test"]["fingerprints"]["eDP-1"] == "abc"


def test_load_nonexistent_profile(mock_profiles_file):
    assert load_profile("nope") is None
