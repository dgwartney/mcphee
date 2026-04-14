"""Shared fixtures for mcphee tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# ------------------------------------------------------------------
# XDG temp dirs — prevent tests from touching real user config/data
# ------------------------------------------------------------------

@pytest.fixture(autouse=True)
def xdg_tmp(tmp_path, monkeypatch):
    """Redirect XDG paths to a temporary directory for all tests."""
    config_home = tmp_path / "config"
    data_home = tmp_path / "data"
    config_home.mkdir()
    data_home.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
    return {"config": config_home, "data": data_home}


# ------------------------------------------------------------------
# In-memory FastMCP test server + connection
# ------------------------------------------------------------------

@pytest.fixture
def mcp_server():
    """A simple in-memory FastMCP server for testing."""
    import fastmcp

    server = fastmcp.FastMCP("test-server")

    @server.tool()
    def echo(message: str) -> str:
        """Echo the input message."""
        return message

    @server.tool()
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @server.resource("test://data")
    def get_data() -> str:
        """A simple test resource."""
        return "test resource content"

    @server.resource("test://json-data")
    def get_json_data() -> dict:
        """A JSON test resource."""
        return {"key": "value", "num": 42}

    @server.prompt()
    def greet(name: str) -> str:
        """Greet someone by name."""
        return f"Hello {name}!"

    return server


@pytest.fixture
def mcp_connection(mcp_server):
    """A connected MCPConnection backed by the in-memory test server."""
    from fastmcp.client.transports import FastMCPTransport
    from fastmcp import Client
    from mcphee.connection import MCPConnection

    class InMemoryConnection(MCPConnection):
        def _make_client(self) -> Client:
            return Client(FastMCPTransport(mcp_server))

        @property
        def description(self) -> str:
            return "in-memory"

    conn = InMemoryConnection()
    conn.connect()
    yield conn
    conn.disconnect()
