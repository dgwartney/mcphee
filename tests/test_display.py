"""Tests for display.py — Display static methods."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from mcphee.display import Display, _to_json_str


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def make_tool(name="echo", description="Echo tool", properties=None, required=None):
    t = MagicMock()
    t.name = name
    t.description = description
    t.inputSchema = {
        "type": "object",
        "properties": properties or {"message": {"type": "string"}},
        "required": required or ["message"],
    }
    return t


def make_resource(uri="test://data", description="Test resource", mimeType="text/plain"):
    r = MagicMock()
    r.uri = uri
    r.description = description
    r.mimeType = mimeType
    return r


def make_prompt(name="greet", description="Greet", arguments=None):
    p = MagicMock()
    p.name = name
    p.description = description
    args = []
    for aname, required in (arguments or [("name", True)]):
        a = MagicMock()
        a.name = aname
        a.required = required
        args.append(a)
    p.arguments = args
    return p


def make_message(role="user", text="Hello"):
    msg = MagicMock()
    msg.role = role
    content = MagicMock()
    content.text = text
    msg.content = content
    return msg


# ------------------------------------------------------------------
# tools_table
# ------------------------------------------------------------------

def test_tools_table_no_error(capsys):
    tools = [make_tool("echo"), make_tool("add", properties={"a": {"type": "integer"}, "b": {"type": "integer"}})]
    Display.tools_table(tools)  # should not raise


def test_tools_table_empty(capsys):
    Display.tools_table([])  # should not raise


def test_tools_table_tool_without_schema(capsys):
    t = MagicMock()
    t.name = "bare"
    t.description = "no schema"
    t.inputSchema = None
    t.input_schema = None
    Display.tools_table([t])


# ------------------------------------------------------------------
# resources_table
# ------------------------------------------------------------------

def test_resources_table_no_error(capsys):
    resources = [make_resource()]
    Display.resources_table(resources)


def test_resources_table_empty(capsys):
    Display.resources_table([])


def test_resources_table_with_templates(capsys):
    tmpl = MagicMock()
    tmpl.uriTemplate = "file:///{path}"
    tmpl.description = "Template"
    tmpl.mimeType = "text/plain"
    Display.resources_table([], templates=[tmpl])


# ------------------------------------------------------------------
# prompts_table
# ------------------------------------------------------------------

def test_prompts_table_no_error(capsys):
    Display.prompts_table([make_prompt()])


def test_prompts_table_empty(capsys):
    Display.prompts_table([])


def test_prompts_table_no_arguments(capsys):
    p = make_prompt(arguments=[])
    Display.prompts_table([p])


# ------------------------------------------------------------------
# tool_result
# ------------------------------------------------------------------

def test_tool_result_json_string(capsys):
    result = MagicMock()
    result.data = '{"key": "value"}'
    Display.tool_result(result)


def test_tool_result_dict(capsys):
    result = MagicMock()
    result.data = {"answer": 42}
    Display.tool_result(result)


def test_tool_result_plain_string(capsys):
    result = MagicMock()
    result.data = "plain text response"
    Display.tool_result(result)


def test_tool_result_json_mode(capsys):
    result = MagicMock()
    result.data = {"key": "val"}
    Display.tool_result(result, json_mode=True)
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["key"] == "val"


def test_tool_result_content_blocks(capsys):
    block = MagicMock()
    block.text = '{"x": 1}'
    result = MagicMock()
    result.data = None
    result.content = [block]
    Display.tool_result(result)


# ------------------------------------------------------------------
# resource_content
# ------------------------------------------------------------------

def test_resource_content_text(capsys):
    item = MagicMock()
    item.text = "hello from resource"
    item.mimeType = "text/plain"
    Display.resource_content([item], uri="test://data")


def test_resource_content_json(capsys):
    item = MagicMock()
    item.text = '{"key": "value"}'
    item.mimeType = "application/json"
    Display.resource_content([item], uri="test://json")


def test_resource_content_binary(capsys):
    item = MagicMock()
    item.text = None
    item.blob = b"\x00\x01\x02"
    item.mimeType = "application/octet-stream"
    Display.resource_content([item], uri="test://bin")


def test_resource_content_json_mode(capsys):
    item = MagicMock()
    item.text = "some text"
    item.mimeType = "text/plain"
    Display.resource_content([item], uri="test://data", json_mode=True)
    out = capsys.readouterr().out
    assert "some text" in out


def test_resource_content_fallback(capsys):
    item = MagicMock()
    del item.text
    del item.blob
    Display.resource_content([item], uri="test://unknown")


def test_resource_content_json_mode_all_blocks_printed(capsys):
    """Both blocks must be printed in JSON mode (regression test for early-return bug)."""
    item1 = MagicMock()
    item1.text = "block one"
    item1.mimeType = "text/plain"
    item2 = MagicMock()
    item2.text = "block two"
    item2.mimeType = "text/plain"
    Display.resource_content([item1, item2], uri="test://multi", json_mode=True)
    out = capsys.readouterr().out
    assert "block one" in out
    assert "block two" in out


# ------------------------------------------------------------------
# prompt_result
# ------------------------------------------------------------------

def test_prompt_result_no_error(capsys):
    result = MagicMock()
    result.messages = [make_message("user", "Hello World")]
    Display.prompt_result(result, name="greet")


def test_prompt_result_json_mode(capsys):
    result = MagicMock()
    result.messages = [make_message("user", "Hi")]
    Display.prompt_result(result, name="test", json_mode=True)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data[0]["role"] == "user"
    assert data[0]["content"] == "Hi"


def test_prompt_result_empty(capsys):
    result = MagicMock()
    result.messages = []
    Display.prompt_result(result, name="empty")


# ------------------------------------------------------------------
# error / info / success / warning
# ------------------------------------------------------------------

def test_error_no_raise(capsys):
    Display.error("something went wrong")


def test_connected_banner(capsys):
    Display.connected_banner("http", "http://localhost/mcp")


def test_info(capsys):
    Display.info("some info")


def test_success(capsys):
    Display.success("great success")


def test_warning(capsys):
    Display.warning("watch out")


# ------------------------------------------------------------------
# help tables
# ------------------------------------------------------------------

def test_help_table(capsys):
    Display.help_table()


def test_meta_help_table(capsys):
    Display.meta_help_table()


# ------------------------------------------------------------------
# _extract_result
# ------------------------------------------------------------------

def test_extract_result_data():
    r = MagicMock()
    r.data = {"x": 1}
    assert Display._extract_result(r) == {"x": 1}


def test_extract_result_content_single_text():
    block = MagicMock()
    block.text = '{"y": 2}'
    r = MagicMock()
    r.data = None
    r.content = [block]
    result = Display._extract_result(r)
    assert result == {"y": 2}


def test_extract_result_content_plain_text():
    block = MagicMock()
    block.text = "plain"
    r = MagicMock()
    r.data = None
    r.content = [block]
    assert Display._extract_result(r) == "plain"


def test_extract_result_list():
    block = MagicMock()
    block.text = "item"
    assert Display._extract_result([block]) == "item"


def test_extract_result_fallback():
    r = "raw string"
    assert Display._extract_result(r) == "raw string"


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def test_looks_like_json_object():
    assert Display._looks_like_json('{"a": 1}')


def test_looks_like_json_array():
    assert Display._looks_like_json("[1, 2, 3]")


def test_looks_like_json_string():
    assert not Display._looks_like_json("hello")


def test_to_json_str_dict():
    out = _to_json_str({"a": 1})
    assert json.loads(out) == {"a": 1}


def test_to_json_str_json_string():
    out = _to_json_str('{"b": 2}')
    assert json.loads(out) == {"b": 2}


def test_to_json_str_plain_string():
    out = _to_json_str("hello")
    assert out == "hello"
