"""Tests for cli.py — Click CLI via CliRunner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from mcphee.cli import mcphee, profile_list, profile_add, profile_remove
from mcphee.profiles import ProfileManager


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def pm(tmp_path):
    return ProfileManager(path=tmp_path / "profiles.toml")


# ------------------------------------------------------------------
# Root group
# ------------------------------------------------------------------

def test_help(runner):
    result = runner.invoke(mcphee, ["--help"])
    assert result.exit_code == 0
    assert "connect" in result.output
    assert "profile" in result.output


def test_version(runner):
    result = runner.invoke(mcphee, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


# ------------------------------------------------------------------
# connect — option validation
# ------------------------------------------------------------------

def test_connect_requires_one_source(runner):
    result = runner.invoke(mcphee, ["connect"])
    assert result.exit_code != 0
    assert "required" in result.output.lower() or "Usage" in result.output


def test_connect_mutual_exclusion(runner):
    result = runner.invoke(mcphee, ["connect", "--stdio", "cmd", "--http", "http://x/mcp"])
    assert result.exit_code != 0


def test_connect_bad_header(runner):
    result = runner.invoke(mcphee, ["connect", "--http", "http://x/mcp", "--header", "badheader"])
    assert result.exit_code != 0


def test_connect_unknown_profile(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    result = runner.invoke(mcphee, ["connect", "--profile", "nosuchprofile"])
    assert result.exit_code != 0


def test_connect_help(runner):
    result = runner.invoke(mcphee, ["connect", "--help"])
    assert result.exit_code == 0
    assert "--stdio" in result.output
    assert "--sse" in result.output
    assert "--http" in result.output
    assert "--profile" in result.output
    assert "--header" in result.output
    assert "--json" in result.output
    assert "--emacs" in result.output


# ------------------------------------------------------------------
# connect — successful connection (mock the shell)
# ------------------------------------------------------------------

def _make_mock_shell():
    shell = MagicMock()
    shell.run.return_value = None
    return shell


def test_connect_stdio(runner):
    with patch("mcphee.cli.ConnectionFactory.create") as mock_factory, \
         patch("mcphee.cli.MCPShell") as mock_shell_cls:

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_factory.return_value = mock_conn

        mock_shell = _make_mock_shell()
        mock_shell_cls.return_value = mock_shell

        result = runner.invoke(mcphee, ["connect", "--stdio", "echo hello"])
        mock_factory.assert_called_once_with("stdio", "echo hello", headers=None, timeout=30.0)
        mock_shell.run.assert_called_once()


def test_connect_sse(runner):
    with patch("mcphee.cli.ConnectionFactory.create") as mock_factory, \
         patch("mcphee.cli.MCPShell") as mock_shell_cls:

        mock_conn = MagicMock()
        mock_factory.return_value = mock_conn

        mock_shell = _make_mock_shell()
        mock_shell_cls.return_value = mock_shell

        result = runner.invoke(mcphee, ["connect", "--sse", "http://localhost/sse",
                                         "--header", "x-key=secret"])
        mock_factory.assert_called_once_with("sse", "http://localhost/sse",
                                              headers={"x-key": "secret"}, timeout=30.0)


def test_connect_http(runner):
    with patch("mcphee.cli.ConnectionFactory.create") as mock_factory, \
         patch("mcphee.cli.MCPShell") as mock_shell_cls:

        mock_conn = MagicMock()
        mock_factory.return_value = mock_conn
        mock_shell_cls.return_value = _make_mock_shell()

        runner.invoke(mcphee, ["connect", "--http", "http://localhost/mcp"])
        mock_factory.assert_called_once_with("http", "http://localhost/mcp",
                                              headers=None, timeout=30.0)


def test_connect_json_flag(runner):
    with patch("mcphee.cli.ConnectionFactory.create") as mock_factory, \
         patch("mcphee.cli.MCPShell") as mock_shell_cls:

        mock_conn = MagicMock()
        mock_factory.return_value = mock_conn
        mock_shell = _make_mock_shell()
        mock_shell_cls.return_value = mock_shell

        runner.invoke(mcphee, ["connect", "--http", "http://localhost/mcp", "--json"])
        _, kwargs = mock_shell_cls.call_args
        assert kwargs.get("json_mode") is True


def test_connect_emacs_flag(runner):
    with patch("mcphee.cli.ConnectionFactory.create") as mock_factory, \
         patch("mcphee.cli.MCPShell") as mock_shell_cls:

        mock_conn = MagicMock()
        mock_factory.return_value = mock_conn
        mock_shell = _make_mock_shell()
        mock_shell_cls.return_value = mock_shell

        runner.invoke(mcphee, ["connect", "--http", "http://localhost/mcp", "--emacs"])
        _, kwargs = mock_shell_cls.call_args
        assert kwargs.get("vi_mode") is False


def test_connect_timeout_flag(runner):
    with patch("mcphee.cli.ConnectionFactory.create") as mock_factory, \
         patch("mcphee.cli.MCPShell") as mock_shell_cls:

        mock_conn = MagicMock()
        mock_factory.return_value = mock_conn
        mock_shell_cls.return_value = _make_mock_shell()

        runner.invoke(mcphee, ["connect", "--http", "http://localhost/mcp", "--timeout", "60"])
        mock_factory.assert_called_once_with("http", "http://localhost/mcp",
                                              headers=None, timeout=60.0)


def test_connect_connection_failure(runner):
    with patch("mcphee.cli.ConnectionFactory.create") as mock_factory:
        mock_conn = MagicMock()
        mock_conn.connect.side_effect = Exception("refused")
        mock_factory.return_value = mock_conn

        result = runner.invoke(mcphee, ["connect", "--http", "http://localhost/mcp"])
        assert result.exit_code == 1


def test_connect_profile(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    pm = ProfileManager(path=tmp_path / "cfg" / "mcphee" / "profiles.toml")
    pm.save_profile("myserver", "http", "http://my.server/mcp")

    with patch("mcphee.cli.ConnectionFactory.create") as mock_factory, \
         patch("mcphee.cli.MCPShell") as mock_shell_cls, \
         patch("mcphee.cli.ProfileManager") as mock_pm_cls:

        mock_pm_cls.return_value = pm
        mock_conn = MagicMock()
        mock_factory.return_value = mock_conn
        mock_shell_cls.return_value = _make_mock_shell()

        result = runner.invoke(mcphee, ["connect", "--profile", "myserver"])
        mock_factory.assert_called()


# ------------------------------------------------------------------
# profile group
# ------------------------------------------------------------------

def test_profile_help(runner):
    result = runner.invoke(mcphee, ["profile", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "add" in result.output
    assert "remove" in result.output


def test_profile_list_empty(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    result = runner.invoke(mcphee, ["profile", "list"])
    assert result.exit_code == 0
    assert "No profiles" in result.output


def test_profile_list_with_profiles(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    pm = ProfileManager(path=tmp_path / "cfg" / "mcphee" / "profiles.toml")
    pm.save_profile("srv1", "http", "http://srv1/mcp")

    with patch("mcphee.cli.ProfileManager") as mock_pm_cls:
        mock_pm_cls.return_value = pm
        result = runner.invoke(mcphee, ["profile", "list"])
        assert result.exit_code == 0


def test_profile_add_http(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    pm = ProfileManager(path=tmp_path / "cfg" / "mcphee" / "profiles.toml")

    with patch("mcphee.cli.ProfileManager") as mock_pm_cls:
        mock_pm_cls.return_value = pm
        # Simulate: mode=http, url=http://test/mcp, no headers
        result = runner.invoke(
            mcphee, ["profile", "add", "testprof"],
            input="http\nhttp://test/mcp\nn\n",
        )
        assert result.exit_code == 0
        cfg = pm.get_profile("testprof")
        assert cfg["mode"] == "http"


def test_profile_add_stdio(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    pm = ProfileManager(path=tmp_path / "cfg" / "mcphee" / "profiles.toml")

    with patch("mcphee.cli.ProfileManager") as mock_pm_cls:
        mock_pm_cls.return_value = pm
        result = runner.invoke(
            mcphee, ["profile", "add", "localprof"],
            input="stdio\nnpx -y @mcp/server /tmp\nn\n",
        )
        assert result.exit_code == 0
        cfg = pm.get_profile("localprof")
        assert cfg["mode"] == "stdio"


def test_profile_remove(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    pm = ProfileManager(path=tmp_path / "cfg" / "mcphee" / "profiles.toml")
    pm.save_profile("todel", "http", "http://del/mcp")

    with patch("mcphee.cli.ProfileManager") as mock_pm_cls:
        mock_pm_cls.return_value = pm
        result = runner.invoke(mcphee, ["profile", "remove", "todel"])
        assert result.exit_code == 0
        assert "todel" not in pm.load_profiles()


def test_profile_remove_not_found(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    pm = ProfileManager(path=tmp_path / "cfg" / "mcphee" / "profiles.toml")

    with patch("mcphee.cli.ProfileManager") as mock_pm_cls:
        mock_pm_cls.return_value = pm
        result = runner.invoke(mcphee, ["profile", "remove", "ghost"])
        assert result.exit_code != 0
