# hello-world-mcp

A tutorial MCP server built with [FastMCP](https://gofastmcp.com). It demonstrates all three MCP
primitives — **tools**, **resources**, and **prompts** — with a variety of argument types and return shapes.

Use it to learn mcphee and to test any MCP client.

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- Python 3.11+
- [mcphee](https://github.com/dgwartney/mcphee) installed (`uv tool install git+https://github.com/dgwartney/mcphee`)

---

## Quick Start

### stdio transport (server spawned automatically)

```bash
# mcphee spawns the server as a subprocess — no separate terminal needed
mcphee connect --stdio 'python /path/to/examples/hello-world-mcp/server.py'
```

### HTTP transport (server runs separately)

```bash
# Terminal 1: start the server
cd examples/hello-world-mcp
uv run python server.py --http
# → Starting hello-world-mcp HTTP server on http://127.0.0.1:8000/mcp

# Terminal 2: connect with mcphee
mcphee connect --http http://127.0.0.1:8000/mcp
```

---

## Using Profiles (Recommended)

Add these entries to `~/.config/mcphee/profiles.toml`:

```toml
[profiles.hello-world]
mode = "stdio"
command = "python /Users/yourname/path/to/examples/hello-world-mcp/server.py"

[profiles.hello-world-http]
mode = "http"
url = "http://127.0.0.1:8000/mcp"
```

Then connect with:

```bash
mcphee connect --profile hello-world
# or, after starting the HTTP server:
mcphee connect --profile hello-world-http
```

---

## mcphee Tutorial Session

Once connected, you'll see the REPL prompt `> `. Here's a guided walkthrough:

### 1. Discover what's available

```
> list tools
> list resources
> list prompts
```

### 2. Read the server overview

```
> read info://server
```

### 3. Call tools

```
# Basic greeting (required + optional arg)
> call greet name=Alice
> call greet name=Bob greeting=Howdy

# Integer arithmetic
> call add a=10 b=32

# Float arithmetic
> call multiply x=3.14 y=2.0

# Boolean argument
> call shout text="hello world"
> call shout text="quiet please" exclaim=false

# Dict return (displayed as syntax-highlighted JSON)
> call calculate_circle radius=5

# Enum-like string arg
> call hash_text text="hello world"
> call hash_text text=secret algorithm=md5

# No-argument tool
> call get_server_info

# List return
> call repeat text=ping times=5

# Multi-value analysis with optional flag
> call word_stats text="The quick brown fox jumps over the lazy dog"
> call word_stats text="hello hello world" include_chars=true

# Unit conversion
> call celsius_to_fahrenheit celsius=100
> call celsius_to_fahrenheit celsius=-40
```

### 4. Read resources

```
# Static resource — server overview
> read info://server

# Static resource — MCP concepts primer
> read info://mcp-primer

# Template resource — substitute {name} with any tool name
> read docs://tool/greet
> read docs://tool/hash_text
> read docs://tool/unknown
```

### 5. Use prompts

```
# Single required arg
> prompt explain_tool tool_name=word_stats

# Optional int and str args
> prompt brainstorm topic="MCP server use cases"
> prompt brainstorm topic="Python tools" count=10 style=creative

# Four args including a bool
> prompt code_review code="def add(a,b): return a+b"
> prompt code_review code="SELECT * FROM users" language=sql focus=security strict=true

# Optional int — omit for no limit
> prompt summarize text="MCP is an open protocol for connecting AI to tools."
> prompt summarize text="Long text here..." max_sentences=2
```

### 6. Meta-commands

```
# Toggle JSON output (raw JSON instead of Rich panels)
> #json
> call greet name=Alice
> #json                     # toggle back to Rich

# Refresh completion caches after server changes
> #refresh

# Export last result to a file
> call calculate_circle radius=7
> #export /tmp/circle.json

# Set request timeout
> #timeout 60

# Enable debug output (shows raw requests/responses)
> #debug
> call add a=1 b=2
> #debug                    # toggle off

# Show command history
> #history 10

# Help
> help
> #help

# Exit
> exit
```

---

## Tool Reference

| Tool | Signature | Demonstrates |
|------|-----------|--------------|
| `greet` | `greet(name: str, greeting: str = "Hello") -> str` | Required + optional string args |
| `add` | `add(a: int, b: int) -> int` | Integer arguments |
| `multiply` | `multiply(x: float, y: float) -> float` | Float arguments |
| `shout` | `shout(text: str, exclaim: bool = True) -> str` | Boolean argument |
| `calculate_circle` | `calculate_circle(radius: float) -> dict` | Dict return, error on bad input |
| `hash_text` | `hash_text(text: str, algorithm: str = "sha256") -> dict` | Enum-like string arg |
| `get_server_info` | `get_server_info() -> dict` | Zero-argument tool |
| `repeat` | `repeat(text: str, times: int = 3) -> list[str]` | List return |
| `word_stats` | `word_stats(text: str, include_chars: bool = False) -> dict` | Optional bool flag |
| `celsius_to_fahrenheit` | `celsius_to_fahrenheit(celsius: float) -> dict` | Unit conversion, dict return |

---

## Resource Reference

| URI | Type | Description |
|-----|------|-------------|
| `info://server` | Static | Server overview and capability listing |
| `info://mcp-primer` | Static | MCP concepts primer (tools/resources/prompts/transports) |
| `docs://tool/{name}` | Template | Per-tool documentation — substitute `{name}` with any tool name |

---

## Prompt Reference

| Prompt | Arguments | Demonstrates |
|--------|-----------|--------------|
| `explain_tool` | `tool_name: str` | Single required string arg |
| `brainstorm` | `topic: str, count: int = 5, style: str = "practical"` | Required + two optional args |
| `code_review` | `code: str, language: str = "python", focus: str = "general", strict: bool = False` | Four mixed args including bool |
| `summarize` | `text: str, max_sentences: Optional[int] = None, language: str = "english"` | Optional[int] (nullable arg) |

---

## Running Options

```bash
# stdio (default) — used when mcphee spawns this as a subprocess
uv run python server.py

# HTTP on default address
uv run python server.py --http

# Custom port
uv run python server.py --http --port 9000

# Bind all interfaces (for remote access)
uv run python server.py --http --host 0.0.0.0 --port 8080
```
