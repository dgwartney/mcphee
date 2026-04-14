"""Tests for shell.py — MCPShell command dispatch and meta-commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from mcphee.shell import MCPShell, parse_kv_args, MCPCompleter


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def mock_conn():
    """A mock MCPConnection with pre-configured return values."""
    conn = MagicMock()
    conn.timeout = 30.0
    conn.is_connected = True

    tool = MagicMock()
    tool.name = "echo"
    tool.description = "Echo tool"
    tool.inputSchema = {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}

    resource = MagicMock()
    resource.uri = "test://data"
    resource.description = "Test resource"
    resource.mimeType = "text/plain"

    prompt = MagicMock()
    prompt.name = "greet"
    prompt.description = "Greet"
    arg = MagicMock()
    arg.name = "name"
    arg.required = True
    prompt.arguments = [arg]

    conn.list_tools.return_value = [tool]
    conn.list_resources.return_value = [resource]
    conn.list_resource_templates.return_value = []
    conn.list_prompts.return_value = [prompt]

    # Tool call result
    tool_result = MagicMock()
    tool_result.data = "hello"
    conn.call_tool.return_value = tool_result

    # Resource read result
    res_item = MagicMock()
    res_item.text = "resource content"
    res_item.mimeType = "text/plain"
    conn.read_resource.return_value = [res_item]

    # Prompt result
    msg = MagicMock()
    msg.role = "user"
    content = MagicMock()
    content.text = "Hello World!"
    msg.content = content
    prompt_result = MagicMock()
    prompt_result.messages = [msg]
    conn.get_prompt.return_value = prompt_result

    return conn


@pytest.fixture
def shell(mock_conn):
    return MCPShell(conn=mock_conn, mode="http", target="http://localhost/mcp", vi_mode=False)


# ------------------------------------------------------------------
# parse_kv_args
# ------------------------------------------------------------------

def test_parse_kv_string():
    assert parse_kv_args(["key=value"]) == {"key": "value"}


def test_parse_kv_int():
    assert parse_kv_args(["n=42"]) == {"n": 42}


def test_parse_kv_bool_true():
    assert parse_kv_args(["flag=true"]) == {"flag": True}


def test_parse_kv_bool_false():
    assert parse_kv_args(["flag=false"]) == {"flag": False}


def test_parse_kv_json_array():
    assert parse_kv_args(["arr=[1,2,3]"]) == {"arr": [1, 2, 3]}


def test_parse_kv_quoted_string():
    assert parse_kv_args(['msg="hello world"']) == {"msg": "hello world"}


def test_parse_kv_multiple():
    result = parse_kv_args(["a=1", "b=two"])
    assert result == {"a": 1, "b": "two"}


def test_parse_kv_empty():
    assert parse_kv_args([]) == {}


def test_parse_kv_no_equals_raises():
    with pytest.raises(ValueError, match="key=value"):
        parse_kv_args(["noequals"])


def test_parse_kv_float():
    result = parse_kv_args(["x=3.14"])
    assert result == {"x": 3.14}


# ------------------------------------------------------------------
# _load_caches
# ------------------------------------------------------------------

def test_load_caches_populates_data(shell, mock_conn):
    shell._load_caches()
    assert "echo" in shell.tool_names
    assert "test://data" in shell.resource_uris
    assert "greet" in shell.prompt_names
    assert "name" in shell.prompt_args["greet"]


def test_load_caches_handles_exception(shell, mock_conn):
    mock_conn.list_tools.side_effect = Exception("server error")
    shell._load_caches()  # should not raise
    assert shell.tool_names == []


# ------------------------------------------------------------------
# _dispatch — MCP commands
# ------------------------------------------------------------------

def test_dispatch_list_tools(shell, mock_conn, capsys):
    shell._dispatch("list tools")
    mock_conn.list_tools.assert_called()


def test_dispatch_list_resources(shell, mock_conn, capsys):
    shell._dispatch("list resources")
    mock_conn.list_resources.assert_called()


def test_dispatch_list_prompts(shell, mock_conn, capsys):
    shell._dispatch("list prompts")
    mock_conn.list_prompts.assert_called()


def test_dispatch_list_unknown(shell, capsys):
    shell._dispatch("list foobar")
    # Should print an error, not raise


def test_dispatch_list_no_subcommand(shell, capsys):
    shell._dispatch("list")
    # Should print usage error


def test_dispatch_call_tool(shell, mock_conn):
    shell._dispatch("call echo message=hello")
    mock_conn.call_tool.assert_called_once_with("echo", {"message": "hello"})


def test_dispatch_call_no_args(shell, mock_conn):
    shell._dispatch("call echo")
    mock_conn.call_tool.assert_called_once_with("echo", {})


def test_dispatch_call_missing_name(shell, capsys):
    shell._dispatch("call")
    # Should print usage error


def test_dispatch_call_bad_kv(shell, capsys):
    shell._dispatch("call echo badarg")
    # Should print error about key=value format


def test_dispatch_call_tool_error(shell, mock_conn, capsys):
    mock_conn.call_tool.side_effect = Exception("tool error")
    shell._dispatch("call echo message=hi")
    # Should show error panel, not raise


def test_dispatch_read(shell, mock_conn):
    shell._dispatch("read test://data")
    mock_conn.read_resource.assert_called_once_with("test://data")


def test_dispatch_read_no_uri(shell, capsys):
    shell._dispatch("read")
    # Should print usage error


def test_dispatch_read_error(shell, mock_conn, capsys):
    mock_conn.read_resource.side_effect = Exception("not found")
    shell._dispatch("read test://missing")
    # Should show error, not raise


def test_dispatch_prompt(shell, mock_conn):
    shell._dispatch("prompt greet name=Alice")
    mock_conn.get_prompt.assert_called_once_with("greet", {"name": "Alice"})


def test_dispatch_prompt_no_name(shell, capsys):
    shell._dispatch("prompt")
    # Should print usage error


def test_dispatch_prompt_error(shell, mock_conn, capsys):
    mock_conn.get_prompt.side_effect = Exception("prompt error")
    shell._dispatch("prompt greet name=x")
    # Should show error, not raise


def test_dispatch_help(shell, capsys):
    shell._dispatch("help")
    # Should not raise


def test_dispatch_exit_returns_true(shell):
    result = shell._dispatch("exit")
    assert result is True


def test_dispatch_quit_returns_true(shell):
    result = shell._dispatch("quit")
    assert result is True


def test_dispatch_unknown_command(shell, capsys):
    result = shell._dispatch("foobar")
    assert result is False


def test_dispatch_empty_line(shell):
    result = shell._dispatch("")
    assert result is False


def test_dispatch_parse_error(shell, capsys):
    # Unclosed quote causes shlex.split to raise ValueError
    result = shell._dispatch('call echo message="unclosed')
    assert result is False


# ------------------------------------------------------------------
# JSON mode
# ------------------------------------------------------------------

def test_list_tools_json_mode(shell, mock_conn, capsys):
    shell._json_mode = True
    shell._dispatch("list tools")
    out = capsys.readouterr().out
    data = json.loads(out)
    assert any(t["name"] == "echo" for t in data)


def test_list_resources_json_mode(shell, mock_conn, capsys):
    shell._json_mode = True
    shell._dispatch("list resources")
    out = capsys.readouterr().out
    json.loads(out)  # should be valid JSON


def test_list_prompts_json_mode(shell, mock_conn, capsys):
    shell._json_mode = True
    shell._dispatch("list prompts")
    out = capsys.readouterr().out
    json.loads(out)  # should be valid JSON


# ------------------------------------------------------------------
# Debug mode
# ------------------------------------------------------------------

def test_debug_mode_call(shell, mock_conn, capsys):
    shell._debug = True
    shell._dispatch("call echo message=hi")
    mock_conn.call_tool.assert_called()


def test_debug_mode_read(shell, mock_conn, capsys):
    shell._debug = True
    shell._dispatch("read test://data")
    mock_conn.read_resource.assert_called()


def test_debug_mode_prompt(shell, mock_conn, capsys):
    shell._debug = True
    shell._dispatch("prompt greet name=x")
    mock_conn.get_prompt.assert_called()


# ------------------------------------------------------------------
# Meta-commands
# ------------------------------------------------------------------

def test_meta_clear(shell, capsys):
    shell._handle_meta("#clear")


def test_meta_refresh(shell, mock_conn):
    shell._handle_meta("#refresh")
    mock_conn.list_tools.assert_called()


def test_meta_json_toggle(shell, capsys):
    assert shell._json_mode is False
    shell._handle_meta("#json")
    assert shell._json_mode is True
    shell._handle_meta("#json")
    assert shell._json_mode is False


def test_meta_debug_toggle(shell):
    assert shell._debug is False
    shell._handle_meta("#debug")
    assert shell._debug is True
    shell._handle_meta("#debug")
    assert shell._debug is False


def test_meta_history_no_session(shell, capsys):
    shell._session = None
    shell._handle_meta("#history")
    # Should print warning, not raise


def test_meta_history_with_n(shell, capsys):
    session = MagicMock()
    session.history.load_history_strings.return_value = ["cmd1", "cmd2", "cmd3"]
    shell._session = session
    shell._handle_meta("#history 2")


def test_meta_history_invalid_n(shell, capsys):
    shell._handle_meta("#history abc")
    # Should print error


def test_meta_export_no_result(shell, capsys):
    shell._last_result = None
    shell._handle_meta("#export")


def test_meta_export_with_result(shell, tmp_path, capsys):
    shell._last_result = {"answer": 42}
    out_file = str(tmp_path / "out.json")
    shell._handle_meta(f"#export {out_file}")
    data = json.loads(Path(out_file).read_text())
    assert data["answer"] == 42


def test_meta_timeout_show_current(shell, capsys):
    shell._handle_meta("#timeout")


def test_meta_timeout_set(shell, mock_conn, capsys):
    shell._handle_meta("#timeout 60")
    assert mock_conn.timeout == 60.0


def test_meta_timeout_invalid(shell, capsys):
    shell._handle_meta("#timeout abc")


def test_meta_timeout_zero_invalid(shell, capsys):
    shell._handle_meta("#timeout 0")


def test_meta_help(shell, capsys):
    shell._handle_meta("#help")


def test_meta_unknown(shell, capsys):
    shell._handle_meta("#bogus")


# ------------------------------------------------------------------
# MCPCompleter
# ------------------------------------------------------------------

def test_completer_top_level():
    shell = MagicMock()
    shell.tool_names = ["echo", "add"]
    shell.resource_uris = ["test://data"]
    shell.prompt_names = ["greet"]
    shell.tool_schemas = {}
    shell.prompt_args = {}

    completer = MCPCompleter(shell)
    from prompt_toolkit.document import Document
    doc = Document("", 0)
    completions = list(completer.get_completions(doc, None))
    names = [c.text for c in completions]
    assert "list" in names
    assert "call" in names
    assert "exit" in names


def test_completer_call_names():
    shell = MagicMock()
    shell.tool_names = ["echo", "add"]
    shell.tool_schemas = {"echo": {"properties": {"message": {}}}, "add": {"properties": {"a": {}, "b": {}}}}
    shell.resource_uris = []
    shell.prompt_names = []
    shell.prompt_args = {}

    completer = MCPCompleter(shell)
    from prompt_toolkit.document import Document
    doc = Document("call ", 5)
    completions = list(completer.get_completions(doc, None))
    names = [c.text for c in completions]
    assert "echo" in names
    assert "add" in names


def test_completer_call_params():
    shell = MagicMock()
    shell.tool_names = ["echo"]
    shell.tool_schemas = {"echo": {"properties": {"message": {"type": "string"}}}}
    shell.resource_uris = []
    shell.prompt_names = []
    shell.prompt_args = {}

    completer = MCPCompleter(shell)
    from prompt_toolkit.document import Document
    doc = Document("call echo ", 10)
    completions = list(completer.get_completions(doc, None))
    names = [c.text for c in completions]
    assert "message=" in names


def test_completer_list_subcommands():
    shell = MagicMock()
    shell.tool_names = []
    shell.tool_schemas = {}
    shell.resource_uris = []
    shell.prompt_names = []
    shell.prompt_args = {}

    completer = MCPCompleter(shell)
    from prompt_toolkit.document import Document
    doc = Document("list ", 5)
    completions = list(completer.get_completions(doc, None))
    names = [c.text for c in completions]
    assert "tools" in names
    assert "resources" in names
    assert "prompts" in names


def test_completer_read_uris():
    shell = MagicMock()
    shell.tool_names = []
    shell.tool_schemas = {}
    shell.resource_uris = ["test://data", "test://json"]
    shell.prompt_names = []
    shell.prompt_args = {}

    completer = MCPCompleter(shell)
    from prompt_toolkit.document import Document
    doc = Document("read ", 5)
    completions = list(completer.get_completions(doc, None))
    names = [c.text for c in completions]
    assert "test://data" in names


def test_completer_prompt_names():
    shell = MagicMock()
    shell.tool_names = []
    shell.tool_schemas = {}
    shell.resource_uris = []
    shell.prompt_names = ["greet", "summarize"]
    shell.prompt_args = {"greet": ["name"], "summarize": ["text"]}

    completer = MCPCompleter(shell)
    from prompt_toolkit.document import Document
    doc = Document("prompt ", 7)
    completions = list(completer.get_completions(doc, None))
    names = [c.text for c in completions]
    assert "greet" in names


def test_completer_prompt_args():
    shell = MagicMock()
    shell.tool_names = []
    shell.tool_schemas = {}
    shell.resource_uris = []
    shell.prompt_names = ["greet"]
    shell.prompt_args = {"greet": ["name", "lang"]}

    completer = MCPCompleter(shell)
    from prompt_toolkit.document import Document
    doc = Document("prompt greet ", 13)
    completions = list(completer.get_completions(doc, None))
    names = [c.text for c in completions]
    assert "name=" in names
    assert "lang=" in names


def test_completer_handles_bad_shlex():
    shell = MagicMock()
    shell.tool_names = []
    shell.tool_schemas = {}
    shell.resource_uris = []
    shell.prompt_names = []
    shell.prompt_args = {}

    completer = MCPCompleter(shell)
    from prompt_toolkit.document import Document
    # Unclosed quote — shlex.split raises ValueError, should be caught
    doc = Document('call echo "unclosed', 19)
    completions = list(completer.get_completions(doc, None))
    # Should return empty list without raising


# ------------------------------------------------------------------
# _history_path
# ------------------------------------------------------------------

def test_history_path_uses_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    from mcphee.shell import _history_path
    path = _history_path()
    assert "mcphee" in str(path)
    assert path.parent.exists()
