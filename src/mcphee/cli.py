"""Click CLI entry point for mcphee."""

from __future__ import annotations

import logging
import sys

import click
from rich.logging import RichHandler
from rich.table import Table

from mcphee.connection import ConnectionFactory
from mcphee.display import Display, console
from mcphee.profiles import ProfileManager
from mcphee.shell import MCPShell

# Configure the root logger once at import time.  Default to WARNING so the
# REPL is quiet; users can raise the level via the #loglevel / #debug meta-commands.
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    handlers=[RichHandler(console=console, show_path=False, rich_tracebacks=True)],
)

# ------------------------------------------------------------------
# Root group
# ------------------------------------------------------------------

@click.group()
@click.version_option(package_name="mcphee")
def mcphee() -> None:
    """mcphee — Interactive MCP client CLI.

    Connect to any MCP server via stdio, SSE, or Streamable HTTP and
    explore its tools, resources, and prompts in an interactive REPL.
    """


# ------------------------------------------------------------------
# connect command
# ------------------------------------------------------------------

@mcphee.command()
@click.option("--stdio", "stdio_cmd", metavar="CMD", default=None,
              help="Full shell command for a stdio MCP server (e.g. 'npx -y @mcp/server /tmp').")
@click.option("--sse", "sse_url", metavar="URL", default=None,
              help="HTTP + Server-Sent Events endpoint URL.")
@click.option("--http", "http_url", metavar="URL", default=None,
              help="Streamable HTTP endpoint URL.")
@click.option("--profile", "-p", metavar="NAME", default=None,
              help="Load connection settings from a named profile (XDG config: profiles.toml).")
@click.option("--header", "-H", metavar="KEY=VALUE", multiple=True,
              help="HTTP request header (repeatable). Only applies to --sse and --http.")
@click.option("--json", "json_mode", is_flag=True, default=False,
              help="Start in JSON output mode instead of Rich pretty output.")
@click.option("--emacs", "emacs_mode", is_flag=True, default=False,
              help="Use Emacs key bindings instead of the default Vi mode.")
@click.option("--timeout", "timeout", metavar="SECONDS", default=30.0, show_default=True,
              help="Request timeout in seconds.")
def connect(
    stdio_cmd: str | None,
    sse_url: str | None,
    http_url: str | None,
    profile: str | None,
    header: tuple[str, ...],
    json_mode: bool,
    emacs_mode: bool,
    timeout: float,
) -> None:
    """Connect to an MCP server and start the interactive REPL.

    Exactly one of --stdio, --sse, --http, or --profile must be provided.

    \b
    Examples:
      mcphee connect --stdio 'npx -y @modelcontextprotocol/server-filesystem /tmp'
      mcphee connect --sse http://localhost:8080/sse --header x-api-key=secret
      mcphee connect --http http://localhost:8080/mcp
      mcphee connect --profile myserver
    """
    if timeout <= 0:
        raise click.BadParameter("Timeout must be positive.", param_hint="--timeout")

    # Validate mutually exclusive options
    sources = [stdio_cmd, sse_url, http_url, profile]
    provided = [s for s in sources if s is not None]
    if len(provided) == 0:
        raise click.UsageError("One of --stdio, --sse, --http, or --profile is required.")
    if len(provided) > 1:
        raise click.UsageError("Only one of --stdio, --sse, --http, or --profile may be used.")

    # Parse headers
    headers: dict[str, str] = {}
    for h in header:
        if "=" not in h:
            raise click.BadParameter(f"Header must be KEY=VALUE, got: {h!r}", param_hint="--header")
        k, _, v = h.partition("=")
        headers[k.strip()] = v.strip()

    # Resolve profile
    if profile is not None:
        pm = ProfileManager()
        cfg = pm.get_profile(profile)
        mode = cfg["mode"]
        target = cfg.get("command") or cfg.get("url", "")
        headers = {**cfg.get("headers", {}), **headers}
    elif stdio_cmd is not None:
        mode, target = "stdio", stdio_cmd
    elif sse_url is not None:
        mode, target = "sse", sse_url
    else:
        assert http_url is not None
        mode, target = "http", http_url

    conn = ConnectionFactory.create(mode, target, headers=headers or None, timeout=timeout)

    try:
        conn.connect()
    except Exception as exc:
        Display.error(f"Connection failed: {exc}")
        sys.exit(1)

    try:
        shell = MCPShell(
            conn=conn,
            mode=mode,
            target=target,
            json_mode=json_mode,
            vi_mode=not emacs_mode,
        )
        shell.run()
    finally:
        conn.disconnect()


# ------------------------------------------------------------------
# profile group
# ------------------------------------------------------------------

@mcphee.group()
def profile() -> None:
    """Manage named MCP connection profiles."""


@profile.command("list")
def profile_list() -> None:
    """List all saved connection profiles."""
    pm = ProfileManager()
    profiles = pm.load_profiles()
    if not profiles:
        click.echo("No profiles saved. Use 'mcphee profile add <name>' to create one.")
        return

    table = Table(title="Saved Profiles", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="green", no_wrap=True)
    table.add_column("Mode")
    table.add_column("Target")
    table.add_column("Headers", style="dim")

    for name, cfg in profiles.items():
        mode = cfg.get("mode", "?")
        target = cfg.get("command") or cfg.get("url", "")
        hdrs = ", ".join(f"{k}=..." for k in cfg.get("headers", {}).keys())
        table.add_row(name, mode, target, hdrs)

    console.print(table)


@profile.command("add")
@click.argument("name")
def profile_add(name: str) -> None:
    """Add or update a named connection profile (interactive prompts)."""
    pm = ProfileManager()

    mode = click.prompt(
        "Transport mode",
        type=click.Choice(["stdio", "sse", "http"]),
        default="http",
    )

    if mode == "stdio":
        target = click.prompt("Shell command")
    else:
        target = click.prompt("URL")

    headers: dict[str, str] = {}
    while click.confirm("Add a header?", default=False):
        key = click.prompt("  Header name")
        val = click.prompt("  Header value")
        headers[key] = val

    pm.save_profile(name, mode, target, headers or None)
    click.echo(f"Profile {name!r} saved to {pm.path}")


@profile.command("remove")
@click.argument("name")
def profile_remove(name: str) -> None:
    """Remove a named connection profile."""
    pm = ProfileManager()
    pm.delete_profile(name)
    click.echo(f"Profile {name!r} removed.")
