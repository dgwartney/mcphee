"""Tests for #payload display, the REPL loop, and connection guards."""

from __future__ import annotations

import logging
import runpy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from mcphee.connection import MCPConnection
from mcphee.display import Display
from mcphee.shell import MCPShell


@pytest.fixture
def shell():
    conn = MagicMock()
    conn.timeout = 30.0
    conn.list_tools.return_value = []
    conn.list_resources.return_value = []
    conn.list_resource_templates.return_value = []
    conn.list_prompts.return_value = []
    return MCPShell(conn=conn, mode="http", target="http://localhost/mcp", vi_mode=False)


# ------------------------------------------------------------------
# Display.payload_request / payload_response
# ------------------------------------------------------------------


def test_payload_request_shows_jsonrpc_envelope(capsys):
    Display.payload_request("tools/call", {"name": "echo", "arguments": {"message": "hi"}})
    out = capsys.readouterr().out
    assert "Request Payload" in out
    assert '"method": "tools/call"' in out
    assert '"jsonrpc": "2.0"' in out


def test_payload_response_content_blocks(capsys):
    blocks = [
        SimpleNamespace(type="text", text='{"answer": 42}'),
        SimpleNamespace(type="text", text="not json"),
        SimpleNamespace(type="blob", blob=b"\x00\x01\x02"),
    ]
    result = SimpleNamespace(data=None, content=blocks, isError=False)
    Display.payload_response(result)
    out = capsys.readouterr().out
    assert "Response Payload" in out
    assert '"answer": 42' in out
    assert '"not json"' in out
    assert "<binary 3 bytes>" in out
    assert '"isError": false' in out


def test_payload_response_data(capsys):
    Display.payload_response(SimpleNamespace(data={"k": "v"}))
    assert '"k": "v"' in capsys.readouterr().out


def test_payload_response_prompt_messages(capsys):
    msg = SimpleNamespace(role="user", content=SimpleNamespace(text="Hello Ada!"))
    Display.payload_response(SimpleNamespace(messages=[msg]))
    out = capsys.readouterr().out
    assert '"role": "user"' in out
    assert "Hello Ada!" in out


def test_payload_response_falls_back_to_raw(capsys):
    Display.payload_response(object())
    assert '"raw"' in capsys.readouterr().out


# ------------------------------------------------------------------
# #payload meta-command and its effect on commands
# ------------------------------------------------------------------


def test_meta_payload_on_off(shell):
    shell._handle_meta("#payload on")
    assert shell._payload_mode is True
    shell._handle_meta("#payload OFF")
    assert shell._payload_mode is False


def test_meta_payload_bad_arg_reports_usage(shell, capsys):
    shell._handle_meta("#payload maybe")
    assert shell._payload_mode is False
    assert "Usage: #payload on" in capsys.readouterr().out


@pytest.mark.parametrize(
    "line, method",
    [
        ("call echo message=hi", "tools/call"),
        ("read test://data", "resources/read"),
        ("prompt greet name=Ada", "prompts/get"),
    ],
)
def test_payload_mode_wraps_each_command(shell, line, method):
    shell._payload_mode = True
    with (
        patch.object(Display, "payload_request") as req,
        patch.object(Display, "payload_response") as resp,
        patch.object(Display, "tool_result"),
        patch.object(Display, "resource_content"),
        patch.object(Display, "prompt_result"),
    ):
        shell._dispatch(line)
    assert req.call_args.args[0] == method
    resp.assert_called_once()


def test_meta_loglevel_rejects_unknown_level(shell, capsys):
    before = logging.getLogger().level
    shell._handle_meta("#loglevel loud")
    assert logging.getLogger().level == before
    assert "Unknown level" in capsys.readouterr().out


# ------------------------------------------------------------------
# REPL loop
# ------------------------------------------------------------------


def test_run_loop_skips_blanks_survives_ctrl_c_and_exits(shell):
    session = MagicMock()
    session.prompt.side_effect = ["", KeyboardInterrupt(), "#json", "exit"]
    with patch("mcphee.shell.PromptSession", return_value=session):
        shell.run()
    assert shell._json_mode is True
    assert session.prompt.call_count == 4


def test_run_loop_exits_on_eof(shell):
    session = MagicMock()
    session.prompt.side_effect = EOFError()
    with patch("mcphee.shell.PromptSession", return_value=session):
        shell.run()
    session.prompt.assert_called_once()


# ------------------------------------------------------------------
# Connection guards and python -m mcphee
# ------------------------------------------------------------------


class _Unconnected(MCPConnection):
    def _make_client(self):  # pragma: no cover - never connected
        raise AssertionError

    @property
    def description(self) -> str:
        return "unconnected"


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.list_tools(),
        lambda c: c.list_resources(),
        lambda c: c.list_resource_templates(),
        lambda c: c.list_prompts(),
        lambda c: c.call_tool("echo", {}),
        lambda c: c.read_resource("test://data"),
        lambda c: c.get_prompt("greet", {}),
    ],
)
def test_operations_require_connect(call):
    with pytest.raises(RuntimeError, match="Not connected"):
        call(_Unconnected())


def test_python_dash_m_runs_cli():
    with patch("mcphee.cli.mcphee") as cli:
        runpy.run_module("mcphee", run_name="__main__")
    cli.assert_called_once_with()


# ------------------------------------------------------------------
# Ctrl+C during a request
# ------------------------------------------------------------------


def test_ctrl_c_during_command_returns_to_prompt(shell, capsys):
    session = MagicMock()
    session.prompt.side_effect = ["call slow", "#json", "exit"]
    with (
        patch("mcphee.shell.PromptSession", return_value=session),
        patch.object(shell, "_cmd_call", side_effect=KeyboardInterrupt),
    ):
        shell.run()
    assert shell._json_mode is True  # the REPL kept going after the interrupt
    assert "Interrupted" in capsys.readouterr().out


def test_ctrl_c_cancels_in_flight_request(mcp_connection):
    future = MagicMock()
    future.result.side_effect = KeyboardInterrupt
    coro = MagicMock()
    with patch("asyncio.run_coroutine_threadsafe", return_value=future):
        with pytest.raises(KeyboardInterrupt):
            mcp_connection._run(coro)
    future.cancel.assert_called_once_with()
