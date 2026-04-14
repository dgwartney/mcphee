"""Tests for profiles.py — ProfileManager."""

from __future__ import annotations

from pathlib import Path

import pytest
import click

from mcphee.profiles import ProfileManager


@pytest.fixture
def pm(tmp_path):
    """ProfileManager pointed at a temp file."""
    return ProfileManager(path=tmp_path / "profiles.toml")


# ------------------------------------------------------------------
# load_profiles
# ------------------------------------------------------------------

def test_load_profiles_empty(pm):
    profiles = pm.load_profiles()
    assert profiles == {}


def test_load_profiles_nonexistent_file(tmp_path):
    pm = ProfileManager(path=tmp_path / "nofile.toml")
    assert pm.load_profiles() == {}


def test_load_profiles_after_save(pm):
    pm.save_profile("test", "http", "http://localhost/mcp")
    profiles = pm.load_profiles()
    assert "test" in profiles


def test_load_multiple_profiles(pm):
    pm.save_profile("a", "http", "http://a.com/mcp")
    pm.save_profile("b", "sse", "http://b.com/sse")
    pm.save_profile("c", "stdio", "npx server")
    profiles = pm.load_profiles()
    assert set(profiles.keys()) == {"a", "b", "c"}


# ------------------------------------------------------------------
# get_profile
# ------------------------------------------------------------------

def test_get_profile_found(pm):
    pm.save_profile("myprofile", "http", "http://example.com/mcp")
    cfg = pm.get_profile("myprofile")
    assert cfg["mode"] == "http"
    assert cfg["url"] == "http://example.com/mcp"


def test_get_profile_not_found(pm):
    with pytest.raises(click.ClickException, match="not found"):
        pm.get_profile("doesnotexist")


def test_get_profile_not_found_shows_available(pm):
    pm.save_profile("existing", "http", "http://host/mcp")
    with pytest.raises(click.ClickException) as exc_info:
        pm.get_profile("missing")
    assert "existing" in str(exc_info.value.format_message())


# ------------------------------------------------------------------
# save_profile
# ------------------------------------------------------------------

def test_save_profile_http(pm):
    pm.save_profile("p1", "http", "http://host/mcp", headers={"x-key": "secret"})
    cfg = pm.get_profile("p1")
    assert cfg["mode"] == "http"
    assert cfg["url"] == "http://host/mcp"
    assert cfg["headers"]["x-key"] == "secret"


def test_save_profile_sse(pm):
    pm.save_profile("p2", "sse", "http://host/sse")
    cfg = pm.get_profile("p2")
    assert cfg["mode"] == "sse"
    assert cfg["url"] == "http://host/sse"


def test_save_profile_stdio(pm):
    pm.save_profile("p3", "stdio", "npx -y @mcp/server /tmp")
    cfg = pm.get_profile("p3")
    assert cfg["mode"] == "stdio"
    assert cfg["command"] == "npx -y @mcp/server /tmp"


def test_save_profile_overwrites(pm):
    pm.save_profile("p", "http", "http://old/mcp")
    pm.save_profile("p", "sse", "http://new/sse")
    cfg = pm.get_profile("p")
    assert cfg["mode"] == "sse"
    assert cfg["url"] == "http://new/sse"


def test_save_profile_creates_parent_dirs(tmp_path):
    deep_path = tmp_path / "a" / "b" / "c" / "profiles.toml"
    pm = ProfileManager(path=deep_path)
    pm.save_profile("x", "http", "http://x.com/mcp")
    assert deep_path.exists()


def test_save_profile_no_headers(pm):
    pm.save_profile("noh", "http", "http://x.com/mcp", headers=None)
    cfg = pm.get_profile("noh")
    assert "headers" not in cfg or cfg.get("headers") == {}


# ------------------------------------------------------------------
# delete_profile
# ------------------------------------------------------------------

def test_delete_profile(pm):
    pm.save_profile("del_me", "http", "http://host/mcp")
    pm.delete_profile("del_me")
    assert "del_me" not in pm.load_profiles()


def test_delete_profile_not_found(pm):
    with pytest.raises(click.ClickException, match="not found"):
        pm.delete_profile("ghost")


def test_delete_one_of_many(pm):
    pm.save_profile("keep", "http", "http://keep/mcp")
    pm.save_profile("remove", "http", "http://remove/mcp")
    pm.delete_profile("remove")
    profiles = pm.load_profiles()
    assert "keep" in profiles
    assert "remove" not in profiles


# ------------------------------------------------------------------
# list_profiles
# ------------------------------------------------------------------

def test_list_profiles_empty(pm):
    assert pm.list_profiles() == {}


def test_list_profiles_returns_all(pm):
    pm.save_profile("x", "http", "http://x/mcp")
    pm.save_profile("y", "stdio", "cmd")
    result = pm.list_profiles()
    assert "x" in result
    assert "y" in result


# ------------------------------------------------------------------
# XDG env var override
# ------------------------------------------------------------------

def test_xdg_config_home_override(monkeypatch, tmp_path):
    custom = tmp_path / "custom_config"
    custom.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(custom))
    from mcphee.profiles import _profiles_path
    path = _profiles_path()
    assert str(custom) in str(path)


# ------------------------------------------------------------------
# path property
# ------------------------------------------------------------------

def test_path_property(tmp_path):
    p = tmp_path / "my.toml"
    pm = ProfileManager(path=p)
    assert pm.path == p
