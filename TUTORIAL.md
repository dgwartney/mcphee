# mcphee Tutorial — Exploring MCP with hello-world-mcp

`mcphee` is an interactive command-line client for any MCP (Model Context Protocol) server.
It gives you a REPL where you can discover and invoke a server's tools, read its resources,
and render its prompts — all without writing a single line of code.

This tutorial uses the `hello-world-mcp` example server that ships with the mcphee repository.
The server intentionally covers every MCP primitive and every argument type so you can see
exactly how mcphee handles each one.

By the end you will know how to:

- Connect mcphee to a server via stdio and HTTP
- List and call tools, passing strings, integers, floats, and booleans
- Read static and template resources
- Render prompts with required and optional arguments
- Use tab completion, Vi editing, and persistent history
- Apply meta-commands to control session behaviour

---

## Prerequisites

| Requirement | Install |
|---|---|
| `uv` | `curl -Ls https://astral.sh/uv/install.sh \| sh` |
| `mcphee` | `uv tool install git+https://github.com/dgwartney/mcphee` |
| mcphee repo | `git clone https://github.com/dgwartney/mcphee` |

The `hello-world-mcp` server lives at `examples/hello-world-mcp/server.py` inside the repo.
Its Python dependencies are managed by `uv` and install automatically the first time you run it.

---

## Connecting

### Option A — stdio (recommended, one terminal)

mcphee spawns the server as a subprocess. No second terminal is needed.

```bash
mcphee connect --stdio "python /path/to/mcphee/examples/hello-world-mcp/server.py"
```

Replace `/path/to/mcphee` with the actual clone location, for example `~/git/mcphee`.

### Option B — saved profile

If you followed the mcphee README and already have a profile configured:

```bash
mcphee connect --profile hello-world
```

To create the profile if it is missing:

```bash
mcphee profile add hello-world
# Transport mode: stdio
# Shell command: python /path/to/mcphee/examples/hello-world-mcp/server.py
```

### Option C — HTTP (two terminals)

```bash
# Terminal 1: start the server
cd examples/hello-world-mcp
uv run python server.py --http
# → Starting hello-world-mcp HTTP server on http://127.0.0.1:8000/mcp

# Terminal 2: connect
mcphee connect --http http://127.0.0.1:8000/mcp
```

### What the connection banner shows

```
╭─── mcphee ────────────────────────────────────────────────────╮
│ Connected via stdio                                           │
│ python .../server.py                                          │
│ Type help for commands or exit to quit.                       │
╰────────────────────────────────────────────────────────────────╯
```

Once you see this, you are at the `> ` prompt and ready to explore.

---

## First Steps

### Get oriented

```
> help
```

Prints a table of every REPL command. Two categories exist:

- **MCP commands** — `list`, `call`, `read`, `prompt`, `help`, `exit`
- **Meta-commands** — prefixed with `#`; type `#help` for that list

### Discover what the server offers

```
> list tools
> list resources
> list prompts
```

Each prints a Rich table with names, descriptions, and parameter summaries.

### Read the server overview

```
> read info://server
```

This is a resource the hello-world-mcp server provides as a starting point. It lists every
tool, resource, and prompt with brief notes — a map of the whole tutorial.

---

## Section 1 — Tools

Tools are functions exposed by the server. You call them with `call <name> [key=value ...]`.
mcphee automatically parses bare values into the right Python type: `42` becomes an integer,
`3.14` a float, `true`/`false` a boolean, and anything else stays a string.

### 1.1 Verifying the connection

```
> call get_server_info
```

`get_server_info` takes no arguments. It returns a JSON object showing the server name,
FastMCP version, Python version, platform, and current UTC time.

> **What this shows:** A zero-argument tool. Useful as a first call to confirm the
> connection is alive and see what environment the server is running in.

---

### 1.2 String arguments — required and optional

```
> call greet name=Alice
```

Result: `Hello, Alice!`

```
> call greet name=Bob greeting=Howdy
```

Result: `Howdy, Bob!`

> **What this shows:** `name` is required (mcphee will report an error if omitted).
> `greeting` is optional with a server-side default of `Hello`. Tab-completion after
> `call greet ` suggests both parameter names as `name=` and `greeting=`.

---

### 1.3 Boolean arguments

```
> call shout text="hello world"
```

Result: `HELLO WORLD!!!`

```
> call shout text="quiet please" exclaim=false
```

Result: `QUIET PLEASE`

> **What this shows:** Pass `true` or `false` without quotes for boolean values.
> mcphee JSON-decodes the token before sending it, so the server receives a Python bool,
> not the string `"false"`.

Wrap values that contain spaces in double quotes: `text="hello world"`.

---

### 1.4 Integer arguments

```
> call add a=10 b=32
```

Result: `42`

```
> call add a=-10 b=42
```

Result: `32`

> **What this shows:** Bare numeric tokens like `10` and `-10` are decoded as integers.
> No quoting or type annotation is needed on the command line.

---

### 1.5 Float arguments

```
> call multiply x=3.14 y=2.0
```

Result: `6.28`

```
> call multiply x=100 y=0.5
```

Result: `50.0`

> **What this shows:** Decimal tokens are decoded as floats. Integer-looking values (`100`)
> are also accepted for float parameters — the server receives `100.0`.

---

### 1.6 Dict return — unit conversion

```
> call celsius_to_fahrenheit celsius=100
```

Result panel (formatted JSON):

```json
{
  "celsius": 100,
  "fahrenheit": 212.0,
  "kelvin": 373.15
}
```

```
> call celsius_to_fahrenheit celsius=-40
```

Result: `-40` Celsius is the same in both scales — `fahrenheit` will also be `-40.0`.

> **What this shows:** When a tool returns a dict or any structured value, mcphee renders
> it as syntax-highlighted JSON inside a green panel. No post-processing is needed.

---

### 1.7 Dict return — structured output and error handling

```
> call calculate_circle radius=5
```

```json
{
  "radius": 5,
  "diameter": 10,
  "area": 78.539816,
  "circumference": 31.415927
}
```

Now try an invalid value:

```
> call calculate_circle radius=-1
```

The server raises a `ValueError`. mcphee catches it and displays a red error panel:

```
╭─ Error ──────────────────────────────────────────────────────╮
│ radius must be positive, got -1                              │
╰──────────────────────────────────────────────────────────────╯
```

> **What this shows:** Server-side validation errors surface cleanly. The REPL continues
> normally — errors do not disconnect you.

---

### 1.8 Enum-like string arguments

```
> call hash_text text="hello world"
```

```json
{
  "algorithm": "sha256",
  "input": "hello world",
  "digest": "b94d27b9934d3e08a52e52d7da7dabfa..."
}
```

```
> call hash_text text=secret algorithm=md5
```

```json
{
  "algorithm": "md5",
  "input": "secret",
  "digest": "5ebe2294ecd0e0f08eab7690d2a6ee69"
}
```

Try an unsupported algorithm to see the error:

```
> call hash_text text=hello algorithm=blake2
```

> **What this shows:** A string argument that acts as an enum. The server validates the
> value and returns a clear error listing the valid choices. The `algorithm=` key is
> suggested by tab-completion because it appears in the tool's JSON schema.

---

### 1.9 List return

```
> call repeat text=ping times=5
```

```json
[
  "ping",
  "ping",
  "ping",
  "ping",
  "ping"
]
```

```
> call repeat text=hello
```

Returns three copies (default `times=3`).

> **What this shows:** When a tool returns a list, mcphee renders it as a JSON array.

---

### 1.10 Nested analysis — optional boolean flag

```
> call word_stats text="The quick brown fox jumps over the lazy dog"
```

```json
{
  "char_count": 43,
  "word_count": 9,
  "unique_words": 9,
  "most_common": [["the", 2], ["quick", 1], ...]
}
```

Now add the optional flag to get character frequency:

```
> call word_stats text="hello hello world" include_chars=true
```

```json
{
  "char_count": 17,
  "word_count": 3,
  "unique_words": 2,
  "most_common": [["hello", 2], ["world", 1]],
  "char_frequency": {"d": 1, "e": 2, "h": 2, ...}
}
```

> **What this shows:** An optional boolean flag that gates additional output. When omitted,
> `include_chars` defaults to `false` on the server side. Passing `include_chars=true`
> expands the response.

---

## Section 2 — Resources

Resources are read-only data identified by a URI. You read them with `read <uri>`.
They come in two kinds: **static** (fixed URI) and **template** (URI with `{placeholders}`).

### 2.1 Listing resources

```
> list resources
```

The table shows three entries:

| URI | Type | Description |
|---|---|---|
| `info://server` | static | Server overview |
| `info://mcp-primer` | static | MCP concepts primer |
| `docs://tool/{name}` | template | Per-tool documentation |

Template URIs appear in a dimmer style to distinguish them from static ones.

---

### 2.2 Static resource — server overview

```
> read info://server
```

Displays a plain-text panel with a structured listing of every tool, resource, and prompt
the server exposes. Good as a quick reference while exploring.

---

### 2.3 Static resource — MCP primer

```
> read info://mcp-primer
```

A short, self-contained reference explaining tools, resources, prompts, and transports.
Useful if you are new to MCP.

---

### 2.4 Template resource — per-tool documentation

Template resources accept values in place of `{placeholders}`.

```
> read docs://tool/greet
```

```
Tool: greet
===========
greet(name: str, greeting: str = 'Hello') -> str

Returns a greeting string. 'greeting' defaults to 'Hello'.

Examples:
  call greet name=Alice
  call greet name=Bob greeting=Howdy
```

Try other tool names:

```
> read docs://tool/hash_text
> read docs://tool/word_stats
```

Request documentation for a name that does not exist:

```
> read docs://tool/unknown
```

The server returns a helpful not-found message listing all valid tool names — the template
always returns something rather than raising an error.

> **What this shows:** Template resources let the server expose a parametric data surface.
> The caller substitutes values directly into the URI; no separate API is needed.

---

## Section 3 — Prompts

Prompts are reusable message templates that return role-labeled messages (user / assistant)
ready to be sent to an LLM. You render them with `prompt <name> [key=value ...]`.

mcphee renders the result in a magenta panel, with each message's role shown in bold.

### 3.1 Listing prompts

```
> list prompts
```

| Name | Arguments | Description |
|---|---|---|
| `explain_tool` | `tool_name` (required) | Ask an LLM to explain a tool |
| `brainstorm` | `topic`, `count`, `style` | Generate ideas on a topic |
| `code_review` | `code`, `language`, `focus`, `strict` | Review a code snippet |
| `summarize` | `text`, `max_sentences`, `language` | Summarize a block of text |

---

### 3.2 Single required argument

```
> prompt explain_tool tool_name=word_stats
```

Returns a user-role message asking an LLM to explain `word_stats` — what it does,
its arguments, return value, and practical examples.

> **What this shows:** A prompt with exactly one required argument. mcphee passes the
> rendered messages back for display; nothing is sent to an LLM unless you pipe the output.

---

### 3.3 Required + optional arguments

```
> prompt brainstorm topic="MCP server use cases"
```

Returns 5 practical ideas (default `count=5`, `style=practical`).

```
> prompt brainstorm topic="Python tools" count=10 style=creative
```

Returns 10 creative ideas.

> **What this shows:** A mix of a required string arg and two optional args — an integer
> and a string. Tab-completion after `prompt brainstorm ` suggests all three parameter names.

---

### 3.4 Four arguments including a boolean

```
> prompt code_review code="def add(a,b): return a+b"
```

Returns a code-review prompt for a Python function (default language, general focus,
non-strict mode).

```
> prompt code_review code="SELECT * FROM users" language=sql focus=security strict=true
```

Returns a strict security-focused SQL review prompt.

> **What this shows:** Four arguments of mixed types: two strings, one enum-like string,
> and a boolean. Values with spaces must be quoted.

---

### 3.5 Optional integer — nullable argument

```
> prompt summarize text="MCP is an open protocol for connecting AI to tools."
```

Returns a summarize prompt with no sentence limit.

```
> prompt summarize text="MCP is an open protocol for connecting AI to tools." max_sentences=2
```

Returns a prompt that constrains the summary to two sentences.

```
> prompt summarize text="Un article en français" language=french
```

> **What this shows:** `max_sentences` is an `Optional[int]` — it may be omitted entirely.
> When omitted, the server receives `None` and produces an unconstrained prompt.

---

## Section 4 — Tab Completion

mcphee builds a completion cache when it connects. Press **Tab** (or Ctrl+I) to trigger it.

| Cursor position | Completions offered |
|---|---|
| After nothing | `list`, `call`, `read`, `prompt`, `help`, `exit` |
| `call ` | All tool names |
| `call greet ` | `name=`, `greeting=` |
| `call word_stats ` | `text=`, `include_chars=` |
| `read ` | All resource URIs (including template pattern) |
| `prompt ` | All prompt names |
| `prompt brainstorm ` | `topic=`, `count=`, `style=` |
| `list ` | `tools`, `resources`, `prompts` |

Already-supplied parameters are excluded from further suggestions — if you have typed
`name=Alice`, `name=` will not appear again.

If the server changes while you are connected (new tools added, prompts renamed), run:

```
> #refresh
```

Output: `Refreshed: 10 tools, 3 resources, 4 prompts`

---

## Section 5 — REPL Features

### History

Commands persist across sessions in `~/.local/share/mcphee/history`.

| Action | Result |
|---|---|
| Up / Down arrow | Step through previous commands |
| Ctrl+R | Reverse-search history |
| `#history` | Print last 20 commands with line numbers |
| `#history 5` | Print last 5 commands |

### Vi editing mode (default)

mcphee defaults to Vi key bindings. The cursor shape changes between modes.

| Key | Action |
|---|---|
| `Esc` | Enter normal mode (block cursor) |
| `i` | Enter insert mode (beam cursor) |
| `h` / `l` | Move left / right in normal mode |
| `w` / `b` | Move forward / back by word |
| `0` / `$` | Beginning / end of line |
| `x` | Delete character |
| `dd` | Delete line |
| `/` | Search history forward |
| `ciw` | Change inner word |

To use Emacs bindings instead:

```bash
mcphee connect --emacs --stdio "python .../server.py"
```

### Auto-suggestions

Ghost text from history appears as you type. Press **→** (right arrow) to accept the
full suggestion, or keep typing to ignore it.

---

## Section 6 — Meta-commands

Meta-commands start with `#` and control session behaviour rather than calling the server.

### Toggle raw JSON output

```
> call greet name=Alice
```

Rich panel output:

```
╭─ Result ────────────────────────────────────────────╮
│ "Hello, Alice!"                                     │
╰─────────────────────────────────────────────────────╯
```

```
> #json
JSON mode: ON

> call greet name=Alice
"Hello, Alice!"

> #json
JSON mode: OFF
```

> Useful for scripting or when you want to pipe output to another tool.

---

### Debug mode — see raw requests and responses

```
> #debug
Debug mode: ON

> call add a=3 b=4
[debug] call_tool('add', {'a': 3, 'b': 4})
... result ...

> #debug
Debug mode: OFF
```

> Shows the exact arguments being sent and the raw result returned. Helpful when a tool
> call produces unexpected output.

---

### Export the last result

```
> call calculate_circle radius=7
> #export /tmp/circle.json
Exported to: /tmp/circle.json
```

The last result from any `call`, `read`, or `prompt` command is saved to the path you
specify. Omit the path to use the default `mcphee_export.json` in the current directory.

---

### Adjust the request timeout

```
> #timeout 60
Timeout set to 60.0s

> #timeout
Current timeout: 60.0s
```

Applies to all subsequent calls. The default is 30 seconds.

---

### Other meta-commands

| Command | Effect |
|---|---|
| `#clear` | Clear the terminal screen |
| `#refresh` | Re-fetch tools/resources/prompts, rebuild completion cache |
| `#history [N]` | Show last N commands (default 20) |
| `#help` | List all meta-commands with descriptions |

---

## Section 7 — Error Examples

Errors in mcphee are surfaced as red panels. The REPL always continues after an error.

### Server-side validation error

```
> call calculate_circle radius=-1
```

```
╭─ Error ──────────────────────────────────────────────╮
│ radius must be positive, got -1                      │
╰──────────────────────────────────────────────────────╯
```

### Unknown tool

```
> call nonexistent_tool
```

```
╭─ Error ──────────────────────────────────────────────╮
│ Unknown tool: 'nonexistent_tool'                     │
╰──────────────────────────────────────────────────────╯
```

### Parse error — missing `=`

```
> call greet name
```

```
╭─ Error ──────────────────────────────────────────────╮
│ Expected key=value, got: 'name'                      │
╰──────────────────────────────────────────────────────╯
```

### Unsupported hash algorithm

```
> call hash_text text=hello algorithm=blake2
```

```
╭─ Error ──────────────────────────────────────────────╮
│ Unknown algorithm 'blake2'. Choose from:             │
│ ['md5', 'sha1', 'sha256', 'sha512']                  │
╰──────────────────────────────────────────────────────╯
```

---

## Disconnecting

```
> exit
```

or

```
> quit
```

Both print `Disconnecting...` and return you to the shell. Ctrl+D (EOF) also exits cleanly.
Ctrl+C during a call interrupts the wait and returns to the `> ` prompt without disconnecting.

---

## Quick Reference

### Tools

| Tool | Signature | Demonstrates |
|---|---|---|
| `get_server_info` | `() → dict` | Zero-argument tool |
| `greet` | `(name: str, greeting: str = "Hello") → str` | Required + optional string |
| `shout` | `(text: str, exclaim: bool = True) → str` | Boolean argument |
| `add` | `(a: int, b: int) → int` | Integer arguments |
| `multiply` | `(x: float, y: float) → float` | Float arguments |
| `celsius_to_fahrenheit` | `(celsius: float) → dict` | Dict return, unit conversion |
| `calculate_circle` | `(radius: float) → dict` | Dict return, error on bad input |
| `hash_text` | `(text: str, algorithm: str = "sha256") → dict` | Enum-like string arg |
| `repeat` | `(text: str, times: int = 3) → list[str]` | List return |
| `word_stats` | `(text: str, include_chars: bool = False) → dict` | Optional bool flag |

### Resources

| URI | Kind | Description |
|---|---|---|
| `info://server` | Static | Server overview and capability listing |
| `info://mcp-primer` | Static | MCP concepts primer |
| `docs://tool/{name}` | Template | Per-tool documentation — substitute any tool name |

### Prompts

| Prompt | Arguments | Demonstrates |
|---|---|---|
| `explain_tool` | `tool_name: str` | Single required string |
| `brainstorm` | `topic: str, count: int = 5, style: str = "practical"` | Required + two optional |
| `code_review` | `code: str, language: str, focus: str, strict: bool = False` | Four mixed args |
| `summarize` | `text: str, max_sentences: Optional[int] = None, language: str` | Nullable int arg |

### REPL commands

| Command | Syntax |
|---|---|
| List available items | `list tools` / `list resources` / `list prompts` |
| Call a tool | `call <name> [key=value ...]` |
| Read a resource | `read <uri>` |
| Get a prompt | `prompt <name> [key=value ...]` |
| Show command help | `help` |
| Exit | `exit` or `quit` |

### Meta-commands

| Command | Effect |
|---|---|
| `#json` | Toggle Rich panels ↔ raw JSON |
| `#debug` | Toggle verbose request/response logging |
| `#export [path]` | Save last result to a JSON file |
| `#timeout <s>` | Set request timeout in seconds |
| `#refresh` | Re-fetch server capabilities, rebuild completions |
| `#history [N]` | Show last N commands |
| `#clear` | Clear the terminal |
| `#help` | List all meta-commands |
