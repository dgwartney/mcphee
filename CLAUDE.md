# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`mcphee` is an interactive command-line client for MCP (Model Context Protocol) servers. It
connects over stdio, SSE or Streamable HTTP and gives a REPL for listing and calling tools,
reading resources and rendering prompts. It is published to PyPI as `mcphee` and requires
Python 3.11+ and fastmcp 3.x (`fastmcp>=3.2.4,<4`; fastmcp 4 breaks it).

> **uv only — never pip.** Use `uv sync`, `uv add`, `uv run`, `uv build`, `uv tool install`.

## Commands

```bash
# Install dependencies (including the dev group)
uv sync --all-groups

# Run the CLI from source
uv run mcphee connect --http http://localhost:8000/mcp

# What CI runs (Python 3.11, 3.12, 3.13)
uv run ruff check src/
uv run pytest --cov=mcphee --cov-report=term-missing --cov-fail-under=90
```

## Architecture

- **src/mcphee/cli.py** — Click entry point: `connect` (`--stdio`, `--sse`, `--http` or a
  saved profile) and `profile list|add|remove`. `--version` reads package metadata.
- **src/mcphee/connection.py** — `MCPConnection` base class wrapping an async fastmcp `Client`
  behind a synchronous API; `StdioMCPConnection`, `SSEMCPConnection`, `HTTPMCPConnection`
  subclasses implement `_make_client()`; `ConnectionFactory` picks one.
- **src/mcphee/shell.py** — `MCPShell` REPL (prompt_toolkit): `_dispatch` routes MCP commands
  (`list`, `call`, `read`, `prompt`) and `_handle_meta` routes `#` meta-commands.
  `MCPCompleter` provides tab completion from cached tool, resource and prompt names.
- **src/mcphee/display.py** — `Display` static methods for all Rich output (tables, result
  panels, `#payload` request/response panels, meta-command help).
- **src/mcphee/profiles.py** — `ProfileManager` for `$XDG_CONFIG_HOME/mcphee/profiles.toml`.
- **src/mcphee/examples/hello_world.py** — the tutorial server, installed as the
  `mcphee-hello-world` command and used by `mcphee connect --demo` (launched with
  `sys.executable -I -m`). TUTORIAL.md quotes its output, so re-check the tutorial when you
  change it. `examples/hello-world-mcp/` is only a pointer README.

## Conventions

- Tests never touch real user config: `tests/conftest.py` redirects the XDG directories, and
  the `mcp_connection` fixture runs against an in-memory FastMCP server.
- A new meta-command needs a branch in `MCPShell._handle_meta`, a row in
  `Display.meta_help_table`, and entries in README.md (Meta-Command Reference) and TUTORIAL.md.
- After changing TUTORIAL.md or `src/mcphee/examples/`, run `scripts/tutorial-check/run.sh` (Docker),
  and update `EXPECT` in `scripts/tutorial-check/check.py` when an example's output changes.
- The version lives only in `pyproject.toml`; `mcphee.__version__` reads it from package
  metadata. Release steps are in [RELEASING.md](RELEASING.md); record changes in CHANGELOG.md.

## Project Tracking

Open work is tracked in the GitHub Project **MCP Seminar Readiness**:
<https://github.com/users/dgwartney/projects/4>. It spans `dgwartney/mcphee`,
`dgwartney/mcp-seminar` and `dgwartney/mcp-examples`.

- Record new work as an issue in the repo that owns it, then add it to the project and set
  **Status** (Todo / In Progress / Done):

  ```bash
  gh project item-add 4 --owner dgwartney --url <issue-url>
  ```

- Move items to Done when the work merges or ships.
