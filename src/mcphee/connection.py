"""MCP connection class hierarchy."""

from __future__ import annotations

import asyncio
import shlex
import threading
from abc import ABC, abstractmethod
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import SSETransport, StreamableHttpTransport


class MCPConnection(ABC):
    """Abstract base for MCP server connections.

    Each connection manages a daemon thread running a dedicated asyncio event loop.
    Async fastmcp calls are submitted to that loop via run_coroutine_threadsafe and
    awaited synchronously from the caller's thread. Subclasses implement _make_client()
    to return a transport-specific fastmcp Client.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self._client: Client | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._connected = False

    # ------------------------------------------------------------------
    # Abstract hooks — subclasses return a configured fastmcp Client
    # ------------------------------------------------------------------

    @abstractmethod
    def _make_client(self) -> Client:
        """Return a fastmcp Client configured for this transport."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of this connection."""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Start the background asyncio event loop and enter the fastmcp client context.

        Spawns a daemon thread that runs the event loop for the lifetime of this connection.
        Raises an exception from the underlying transport if the server cannot be reached.
        """
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

        self._client = self._make_client()
        self._run(self._client.__aenter__())
        self._connected = True

    def disconnect(self) -> None:
        """Exit the fastmcp client context and stop the background event loop.

        Waits up to 5 seconds for the event loop thread to terminate. Any error during
        client teardown is suppressed to ensure the thread is always cleaned up.
        """
        if self._client and self._connected:
            try:
                self._run(self._client.__aexit__(None, None, None))
            except Exception:
                pass
        self._connected = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5)

    # ------------------------------------------------------------------
    # Sync wrapper around async fastmcp calls
    # ------------------------------------------------------------------

    def _run(self, coro: Any) -> Any:
        """Submit a coroutine to the background loop and block until it completes.

        Args:
            coro: An awaitable to execute on the background event loop.

        Returns:
            The coroutine's return value.

        Raises:
            RuntimeError: If not connected.
            concurrent.futures.TimeoutError: If the call exceeds self.timeout seconds.
        """
        if self._loop is None:
            raise RuntimeError("Not connected — call connect() first")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=self.timeout)

    # ------------------------------------------------------------------
    # MCP operations
    # ------------------------------------------------------------------

    def list_tools(self) -> list:
        """Return the list of Tool objects exposed by the server."""
        if self._client is None:
            raise RuntimeError("Not connected — call connect() first")
        return self._run(self._client.list_tools())

    def list_resources(self) -> list:
        """Return the list of Resource objects exposed by the server."""
        if self._client is None:
            raise RuntimeError("Not connected — call connect() first")
        return self._run(self._client.list_resources())

    def list_resource_templates(self) -> list:
        """Return the list of ResourceTemplate objects exposed by the server."""
        if self._client is None:
            raise RuntimeError("Not connected — call connect() first")
        return self._run(self._client.list_resource_templates())

    def list_prompts(self) -> list:
        """Return the list of Prompt objects exposed by the server."""
        if self._client is None:
            raise RuntimeError("Not connected — call connect() first")
        return self._run(self._client.list_prompts())

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Invoke a server tool by name and return its result."""
        if self._client is None:
            raise RuntimeError("Not connected — call connect() first")
        return self._run(self._client.call_tool(name, arguments))

    def read_resource(self, uri: str) -> Any:
        """Read a server resource by URI and return its content."""
        if self._client is None:
            raise RuntimeError("Not connected — call connect() first")
        return self._run(self._client.read_resource(uri))

    def get_prompt(self, name: str, arguments: dict[str, Any]) -> Any:
        """Fetch a server prompt by name and return the rendered messages."""
        if self._client is None:
            raise RuntimeError("Not connected — call connect() first")
        return self._run(self._client.get_prompt(name, arguments))

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "MCPConnection":
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._connected


class StdioMCPConnection(MCPConnection):
    """Connect to an MCP server via stdio (subprocess)."""

    def __init__(self, command: str, timeout: float = 30.0) -> None:
        super().__init__(timeout)
        self.command = command
        # Split into argv; shlex handles quoted args correctly
        self._argv = shlex.split(command)

    def _make_client(self) -> Client:
        from fastmcp.client.transports import (
            NodeStdioTransport,
            PythonStdioTransport,
            StdioTransport,
        )

        cmd, *args = self._argv

        if cmd in ("node", "npx", "npx.cmd", "bunx"):
            # NodeStdioTransport(command, args=[...])
            return Client(NodeStdioTransport(cmd, args=args))

        elif cmd in ("python", "python3") and args:
            # PythonStdioTransport(script_path, args=[extra_args], python_cmd=interpreter)
            # argv pattern: python /path/to/server.py [extra...]
            script_path, *script_args = args
            return Client(PythonStdioTransport(script_path, args=script_args, python_cmd=cmd))

        else:
            # Generic: StdioTransport(command, args=[...]) handles uv, uvx, arbitrary executables
            return Client(StdioTransport(cmd, args=args))

    @property
    def description(self) -> str:
        return f"stdio: {self.command}"


class SSEMCPConnection(MCPConnection):
    """Connect to a remote MCP server via HTTP + Server-Sent Events."""

    def __init__(
        self, url: str, headers: dict[str, str] | None = None, timeout: float = 30.0
    ) -> None:
        super().__init__(timeout)
        self.url = url
        self.headers = headers or {}

    def _make_client(self) -> Client:
        transport = SSETransport(url=self.url, headers=self.headers)
        return Client(transport)

    @property
    def description(self) -> str:
        return f"sse: {self.url}"


class HTTPMCPConnection(MCPConnection):
    """Connect to a remote MCP server via Streamable HTTP."""

    def __init__(
        self, url: str, headers: dict[str, str] | None = None, timeout: float = 30.0
    ) -> None:
        super().__init__(timeout)
        self.url = url
        self.headers = headers or {}

    def _make_client(self) -> Client:
        transport = StreamableHttpTransport(url=self.url, headers=self.headers)
        return Client(transport)

    @property
    def description(self) -> str:
        return f"http: {self.url}"


class ConnectionFactory:
    """Create the right MCPConnection subclass based on mode."""

    @staticmethod
    def create(
        mode: str,
        target: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> MCPConnection:
        """
        Args:
            mode: "stdio", "sse", or "http"
            target: command string (stdio) or URL (sse/http)
            headers: HTTP headers for remote transports
            timeout: request timeout in seconds
        """
        if mode == "stdio":
            return StdioMCPConnection(command=target, timeout=timeout)
        elif mode == "sse":
            return SSEMCPConnection(url=target, headers=headers, timeout=timeout)
        elif mode == "http":
            return HTTPMCPConnection(url=target, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Unknown mode: {mode!r}. Choose from: stdio, sse, http")
