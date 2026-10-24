"""Tests for the bundled hello-world example server."""

from __future__ import annotations

import socket
import subprocess
import sys
import time

import pytest

from mcphee.connection import HTTPMCPConnection, StdioMCPConnection
from mcphee.examples import hello_world

EXPECTED_TOOLS = {
    "greet", "add", "multiply", "shout", "calculate_circle", "hash_text",
    "get_server_info", "repeat", "word_stats", "celsius_to_fahrenheit",
}


async def test_in_memory_server_exposes_primitives_and_tools_work():
    from fastmcp import Client

    async with Client(hello_world.mcp) as c:
        assert {t.name for t in await c.list_tools()} == EXPECTED_TOOLS
        assert (await c.call_tool("greet", {"name": "Ada"})).data == "Hello, Ada!"
        assert (await c.call_tool("add", {"a": 2, "b": 3})).data == 5
        assert (await c.call_tool("multiply", {"x": 1.5, "y": 2})).data == 3.0
        assert (await c.call_tool("shout", {"text": "hi"})).data == "HI!!!"
        assert (await c.call_tool("repeat", {"text": "a", "times": 2})).data == ["a", "a"]
        for name, args in [
            ("calculate_circle", {"radius": 1}),
            ("hash_text", {"text": "x"}),
            ("get_server_info", {}),
            ("word_stats", {"text": "a b", "include_chars": True}),
            ("celsius_to_fahrenheit", {"celsius": 100}),
        ]:
            assert (await c.call_tool(name, args)).data
        assert await c.list_resources()
        assert await c.list_resource_templates()
        assert await c.list_prompts()


def test_stdio_argv_overrides_command_splitting():
    conn = StdioMCPConnection(command="label", argv=["C:\\Program Files\\py.exe", "-m", "x"])
    assert conn._argv == ["C:\\Program Files\\py.exe", "-m", "x"]


def test_main_stdio_runs_quiet(monkeypatch):
    calls = []
    monkeypatch.setattr(hello_world.mcp, "run", lambda **kw: calls.append(kw))
    hello_world.main([])
    assert calls == [{"transport": "stdio", "show_banner": False, "log_level": "CRITICAL"}]


def test_main_http_announces_and_passes_host_port(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(hello_world.mcp, "run", lambda **kw: calls.append(kw))
    hello_world.main(["--http", "--host", "127.0.0.1", "--port", "9123"])
    assert calls == [{"transport": "http", "host": "127.0.0.1", "port": 9123}]
    err = capsys.readouterr().err
    assert "Starting hello-world-mcp HTTP server on http://127.0.0.1:9123/mcp" in err


def test_bundled_server_over_stdio_lists_tools():
    conn = StdioMCPConnection(
        command="demo", argv=[sys.executable, "-m", "mcphee.examples.hello_world"]
    )
    with conn:
        assert {t.name for t in conn.list_tools()} == EXPECTED_TOOLS


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_bundled_server_over_http_lists_tools():
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "mcphee.examples.hello_world", "--http", "--port", str(port)],
        stderr=subprocess.DEVNULL,
    )
    try:
        conn = HTTPMCPConnection(f"http://127.0.0.1:{port}/mcp", timeout=5)
        for _ in range(40):
            try:
                conn.connect()
                break
            except Exception:
                conn.disconnect()
                time.sleep(0.25)
        else:
            pytest.fail("HTTP server did not start")
        try:
            assert {t.name for t in conn.list_tools()} == EXPECTED_TOOLS
        finally:
            conn.disconnect()
    finally:
        proc.terminate()
        proc.wait(timeout=10)
