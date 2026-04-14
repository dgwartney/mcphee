# mcphee

[![CI](https://github.com/dgwartney/mcphee/actions/workflows/ci.yml/badge.svg)](https://github.com/dgwartney/mcphee/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/mcphee.svg)](https://pypi.org/project/mcphee/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**mcphee** is an interactive CLI client for [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers.
Connect to any MCP server — local (stdio) or remote (SSE / Streamable HTTP) — and explore its tools, resources,
and prompts in a rich interactive REPL.

---

## Features

- **Universal transport support** — stdio, SSE, and Streamable HTTP
- **Interactive REPL** — Vi mode (default) or Emacs mode with full line editing
- **Tab completion** — fuzzy-match tool names, resource URIs, prompt names, and their parameters
- **Auto-suggestions** — fish-shell style history suggestions as you type
- **Persistent history** — across sessions, XDG-compliant location
- **Named profiles** — save connection configs in `~/.config/mcphee/profiles.toml`
- **Rich output** — syntax-highlighted JSON, tables, and panels; toggle to raw JSON with `#json`
- **Meta-commands** — `#refresh`, `#export`, `#timeout`, `#debug`, and more

---

## Installation

```bash
# From PyPI
pip install mcphee
uv tool install mcphee

# From GitHub (latest main)
uv tool install git+https://github.com/dgwartney/mcphee

# Specific tag
uv tool install git+https://github.com/dgwartney/mcphee@v0.1.0
pip install git+https://github.com/dgwartney/mcphee@v0.1.0
```

---

## Quick Start

```bash
# Connect to a local stdio MCP server
mcphee connect --stdio 'npx -y @modelcontextprotocol/server-filesystem /tmp'

# Connect via SSE with an API key header
mcphee connect --sse http://localhost:8080/sse --header x-api-key=secret

# Connect via Streamable HTTP
mcphee connect --http http://localhost:8080/mcp

# Connect using a saved profile
mcphee connect --profile myserver
```

Once connected you'll enter the interactive REPL:

```
╭─ mcphee ──────────────────────────────────────────────────────╮
│ Connected via http                                            │
│ http://localhost:8080/mcp                                     │
│ Type help for commands or exit to quit.                       │
╰───────────────────────────────────────────────────────────────╯
> list tools
> call read_file path=/tmp/notes.txt
> list resources
> read file:///tmp/notes.txt
> list prompts
> prompt summarize text="hello world"
> exit
```

---

## REPL Command Reference

| Command | Syntax | Description |
|---------|--------|-------------|
| `list tools` | `list tools` | List all available tools |
| `list resources` | `list resources` | List all available resources |
| `list prompts` | `list prompts` | List all available prompts |
| `call` | `call <tool> [key=value ...]` | Invoke a tool with arguments |
| `read` | `read <uri>` | Read a resource by URI |
| `prompt` | `prompt <name> [key=value ...]` | Get a prompt with arguments |
| `help` | `help` | Show command reference |
| `exit` / `quit` | `exit` | Disconnect and exit |

### Argument syntax

Tool and prompt arguments are passed as `key=value` pairs:

```
> call read_file path=/tmp/foo.txt
> call search query="hello world" limit=10
> prompt summarize text="Some long text here" language=en
```

Values are automatically typed: `true`/`false` to bool, integers to int, JSON arrays/objects to parsed.

---

## Meta-Command Reference

Meta-commands begin with `#` and control the REPL session:

| Command | Syntax | Description |
|---------|--------|-------------|
| `#clear` | `#clear` | Clear the terminal screen |
| `#refresh` | `#refresh` | Re-fetch tools/resources/prompts, rebuild completions |
| `#json` | `#json` | Toggle JSON vs Rich pretty output |
| `#history` | `#history [N]` | Show last N commands (default 20) |
| `#export` | `#export [path]` | Export last result to a JSON file |
| `#timeout` | `#timeout <seconds>` | Set request timeout |
| `#debug` | `#debug` | Toggle verbose debug output |
| `#help` | `#help` | Show meta-command reference |

---

## Profile Management

Save connection configs so you don't have to retype them:

```bash
# Add a profile interactively
mcphee profile add myserver

# List all profiles
mcphee profile list

# Remove a profile
mcphee profile remove myserver
```

Profile TOML schema (`~/.config/mcphee/profiles.toml`):

```toml
[profiles.lumen]
mode = "http"
url = "http://localhost:8080/mcp"
[profiles.lumen.headers]
x-api-key = "secret"

[profiles.filesystem]
mode = "stdio"
command = "npx -y @modelcontextprotocol/server-filesystem /tmp"

[profiles.weather]
mode = "sse"
url = "http://weather-api.internal/sse"
```

---

## Configuration Paths (XDG)

mcphee follows the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/):

| Data | Path |
|------|------|
| Profiles | `$XDG_CONFIG_HOME/mcphee/profiles.toml` (default: `~/.config/mcphee/profiles.toml`) |
| History | `$XDG_DATA_HOME/mcphee/history` (default: `~/.local/share/mcphee/history`) |

---

## Key Bindings

The REPL uses **Vi mode** by default. Use `--emacs` to switch to Emacs mode.

| Mode | Keys | Action |
|------|------|--------|
| Vi normal | `h l w b 0 $` | Move cursor |
| Vi normal | `x dd u` | Delete / undo |
| Vi normal | `/` | Search forward |
| Both | Up / Down arrows | History recall |
| Both | `Ctrl+R` | Reverse history search |
| Vi insert | `Esc` | Switch to normal mode |

---

## Publishing to PyPI

```bash
uv build          # produces dist/mcphee-*.whl and .tar.gz
uv publish        # requires PYPI_TOKEN env var or --token flag
```

---

## License

MIT
