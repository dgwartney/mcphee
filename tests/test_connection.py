"""Tests for connection.py — connection class hierarchy."""

from __future__ import annotations

import pytest
from fastmcp.client.transports import FastMCPTransport
from fastmcp import Client

from mcphee.connection import (
    ConnectionFactory,
    HTTPMCPConnection,
    MCPConnection,
    SSEMCPConnection,
    StdioMCPConnection,
)


# ------------------------------------------------------------------
# Helper: InMemoryConnection for testing MCPConnection base
# ------------------------------------------------------------------

def make_in_memory_conn(server, timeout=30.0):
    """Return a concrete MCPConnection backed by an in-memory FastMCP server."""

    class _Conn(MCPConnection):
        def _make_client(self) -> Client:
            return Client(FastMCPTransport(server))

        @property
        def description(self) -> str:
            return "in-memory"

    return _Conn(timeout=timeout)


# ------------------------------------------------------------------
# connect / disconnect
# ------------------------------------------------------------------

def test_connect_sets_connected(mcp_server):
    conn = make_in_memory_conn(mcp_server)
    assert not conn.is_connected
    conn.connect()
    assert conn.is_connected
    conn.disconnect()
    assert not conn.is_connected


def test_context_manager(mcp_server):
    conn = make_in_memory_conn(mcp_server)
    with conn:
        assert conn.is_connected
    assert not conn.is_connected


def test_disconnect_idempotent(mcp_server):
    conn = make_in_memory_conn(mcp_server)
    conn.connect()
    conn.disconnect()
    conn.disconnect()  # should not raise


# ------------------------------------------------------------------
# list_tools
# ------------------------------------------------------------------

def test_list_tools_returns_tools(mcp_connection):
    tools = mcp_connection.list_tools()
    assert isinstance(tools, list)
    names = [t.name for t in tools]
    assert "echo" in names
    assert "add" in names


def test_list_tools_have_schemas(mcp_connection):
    tools = mcp_connection.list_tools()
    echo = next(t for t in tools if t.name == "echo")
    schema = getattr(echo, "inputSchema", None) or getattr(echo, "input_schema", None)
    assert schema is not None
    assert "message" in schema.get("properties", {})


# ------------------------------------------------------------------
# list_resources
# ------------------------------------------------------------------

def test_list_resources_returns_resources(mcp_connection):
    resources = mcp_connection.list_resources()
    assert isinstance(resources, list)
    uris = [str(r.uri) for r in resources]
    assert any("test://data" in u for u in uris)


# ------------------------------------------------------------------
# list_resource_templates
# ------------------------------------------------------------------

def test_list_resource_templates_returns_list(mcp_connection):
    templates = mcp_connection.list_resource_templates()
    assert isinstance(templates, list)


# ------------------------------------------------------------------
# list_prompts
# ------------------------------------------------------------------

def test_list_prompts_returns_prompts(mcp_connection):
    prompts = mcp_connection.list_prompts()
    assert isinstance(prompts, list)
    names = [p.name for p in prompts]
    assert "greet" in names


# ------------------------------------------------------------------
# call_tool
# ------------------------------------------------------------------

def test_call_tool_echo(mcp_connection):
    result = mcp_connection.call_tool("echo", {"message": "hello"})
    # Result may be wrapped in content blocks or have .data
    from mcphee.display import Display
    extracted = Display._extract_result(result)
    assert "hello" in str(extracted)


def test_call_tool_add(mcp_connection):
    result = mcp_connection.call_tool("add", {"a": 3, "b": 4})
    from mcphee.display import Display
    extracted = Display._extract_result(result)
    assert "7" in str(extracted)


def test_call_tool_unknown_raises(mcp_connection):
    with pytest.raises(Exception):
        mcp_connection.call_tool("nonexistent_tool_xyz", {})


# ------------------------------------------------------------------
# read_resource
# ------------------------------------------------------------------

def test_read_resource(mcp_connection):
    content = mcp_connection.read_resource("test://data")
    assert content is not None
    # Should contain "test resource content"
    items = content if isinstance(content, list) else [content]
    texts = [getattr(item, "text", str(item)) for item in items]
    assert any("test resource content" in t for t in texts)


def test_read_resource_unknown_raises(mcp_connection):
    with pytest.raises(Exception):
        mcp_connection.read_resource("nonexistent://xyz/abc")


# ------------------------------------------------------------------
# get_prompt
# ------------------------------------------------------------------

def test_get_prompt(mcp_connection):
    result = mcp_connection.get_prompt("greet", {"name": "World"})
    messages = getattr(result, "messages", None) or result
    assert messages
    text = getattr(messages[0].content, "text", str(messages[0].content))
    assert "World" in text


def test_get_prompt_unknown_raises(mcp_connection):
    with pytest.raises(Exception):
        mcp_connection.get_prompt("nonexistent_prompt_xyz", {})


# ------------------------------------------------------------------
# _run without connect raises
# ------------------------------------------------------------------

def test_run_without_connect_raises(mcp_server):
    conn = make_in_memory_conn(mcp_server)

    async def noop():
        pass

    with pytest.raises(RuntimeError, match="Not connected"):
        conn._run(noop())


# ------------------------------------------------------------------
# ConnectionFactory
# ------------------------------------------------------------------

def test_factory_stdio():
    conn = ConnectionFactory.create("stdio", "echo hello")
    assert isinstance(conn, StdioMCPConnection)
    assert conn.command == "echo hello"


def test_factory_sse():
    conn = ConnectionFactory.create("sse", "http://localhost/sse", headers={"x-key": "v"})
    assert isinstance(conn, SSEMCPConnection)
    assert conn.url == "http://localhost/sse"
    assert conn.headers == {"x-key": "v"}


def test_factory_http():
    conn = ConnectionFactory.create("http", "http://localhost/mcp")
    assert isinstance(conn, HTTPMCPConnection)
    assert conn.url == "http://localhost/mcp"


def test_factory_invalid_mode():
    with pytest.raises(ValueError, match="Unknown mode"):
        ConnectionFactory.create("ftp", "ftp://example.com")


# ------------------------------------------------------------------
# StdioMCPConnection description
# ------------------------------------------------------------------

def test_stdio_description():
    conn = StdioMCPConnection("npx -y @mcp/server /tmp")
    assert "stdio" in conn.description
    assert "npx" in conn.description


def test_sse_description():
    conn = SSEMCPConnection("http://host/sse")
    assert "sse" in conn.description
    assert "host" in conn.description


def test_http_description():
    conn = HTTPMCPConnection("http://host/mcp")
    assert "http" in conn.description
    assert "host" in conn.description


# ------------------------------------------------------------------
# Timeout attribute
# ------------------------------------------------------------------

def test_timeout_default(mcp_server):
    conn = make_in_memory_conn(mcp_server)
    assert conn.timeout == 30.0


def test_timeout_custom(mcp_server):
    conn = make_in_memory_conn(mcp_server, timeout=60.0)
    assert conn.timeout == 60.0
