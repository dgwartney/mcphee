"""Walk TUTORIAL.md in a real terminal and fail on any wrong output.

Runs inside the tutorial-check container (see README.md) after mcphee is installed with
`uv tool install`. Every `> command` line in TUTORIAL.md is typed into a live REPL connected to
`mcphee-hello-world`; key commands are checked against expected output, and every command is
checked for error markers that mean the tutorial is broken. Separate sessions cover the
connection options, Ctrl+C / Ctrl+D, tab completion and the Vi / Emacs key bindings.

Usage: python check.py TUTORIAL.md   (exit status 0 = all checks passed)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import textwrap

import pexpect

ANSI = re.compile(
    r"\x1b\][^\x07\x1b]*(\x07|\x1b\\)|\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[()=>][A-Z0-9]?|\r"
)
ENV = {**os.environ, "TERM": "xterm", "PROMPT_TOOLKIT_NO_CPR": "1", "COLUMNS": "100"}

# Output that means the tutorial is broken, whatever the command.
BROKEN = [
    "Traceback",
    "Connection failed",
    "Unknown command",
    "Parse error",
    "is not fully defined",
]

# Substrings each command's output must contain. Commands not listed only get the BROKEN check.
EXPECT = {
    "help": ["REPL Commands"],
    "list tools": ["celsius_to_fahrenheit", "word_stats"],
    "list resources": ["docs://tool/{name}"],
    "list prompts": ["code_review", "summarize"],
    "read info://server": ["hello-world-mcp"],
    "call get_server_info": ['"server_name": "hello-world-mcp"'],
    "call greet name=Alice": ["Hello, Alice!"],
    "call greet name=Bob greeting=Howdy": ["Howdy, Bob!"],
    'call shout text="hello world"': ["HELLO WORLD!!!"],
    'call shout text="quiet please" exclaim=false': ["QUIET PLEASE"],
    "call add a=10 b=32": ["42"],
    "call multiply x=3.14 y=2.0": ["6.28"],
    "call celsius_to_fahrenheit celsius=100": ['"fahrenheit": 212.0'],
    "call calculate_circle radius=5": ['"area": 78.539816'],
    "call calculate_circle radius=-1": ["radius must be positive, got -1.0"],
    "call hash_text text=secret algorithm=md5": ["5ebe2294ecd0e0f08eab7690d2a6ee69"],
    "call hash_text text=hello algorithm=blake2": ["Unknown algorithm 'blake2'"],
    'call word_stats text="The quick brown fox jumps over the lazy dog"': ['"unique_words": 8'],
    "read docs://tool/greet": ["greet(name: str, greeting: str = 'Hello') -> str"],
    "read docs://tool/unknown": ["No documentation found for tool 'unknown'"],
    'prompt brainstorm topic="Python tools" count=10 style=creative': ["10 creative ideas"],
    'prompt summarize text="MCP is an open protocol for connecting AI to tools." max_sentences=2': [
        "in no more than 2 sentences"
    ],
    "#refresh": ["Refreshed: 10 tools, 3 resources, 4 prompts"],
    "#payload on": ["Payload mode: ON"],
    "#debug": ["Debug mode:"],
    "#loglevel info": ["Log level set to INFO"],
    "#timeout 60": ["Timeout set to 60.0s"],
    "call nonexistent_tool": ["Unknown tool: 'nonexistent_tool'"],
    "call greet name": ["Expected key=value, got: 'name'"],
}
# These commands are expected to show an error panel, so "Error" is not a failure for them.
EXPECTED_ERRORS = {
    "call calculate_circle radius=-1",
    "call hash_text text=hello algorithm=blake2",
    "call nonexistent_tool",
    "call greet name",
}

failures: list[str] = []
passes = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global passes
    if ok:
        passes += 1
    else:
        failures.append(f"{label}: {detail}")
        print(f"  FAIL {label}: {detail}", flush=True)


def clean(text: str) -> str:
    return ANSI.sub("", text or "")


def spawn(cmd: str) -> pexpect.spawn:
    return pexpect.spawn(
        "/bin/bash", ["-lc", cmd], encoding="utf-8", timeout=180, dimensions=(60, 100), env=ENV
    )


def quiet(p: pexpect.spawn, first: float = 180, idle: float = 2.5) -> tuple[str, bool]:
    """Collect output until the terminal is silent for `idle` seconds. Returns (text, alive)."""
    buf, wait = "", first
    while True:
        try:
            buf += p.read_nonblocking(65536, timeout=wait)
            wait = idle
        except pexpect.TIMEOUT:
            return clean(buf), True
        except pexpect.EOF:
            return clean(buf), False


def session(label: str, cmd: str, steps: list[str]) -> list[tuple[str, str]]:
    """Run `cmd`, send each step after the output settles, return [(step, output-after-it)]."""
    print(f"\n== {label}\n$ {cmd}", flush=True)
    p = spawn(cmd)
    banner, alive = quiet(p)
    check(f"{label}: connects", alive and "Connected via" in banner, banner[-400:])
    results = []
    for step in steps:
        if not alive:
            check(f"{label}: {step!r}", False, "session ended early")
            break
        if step == "^C":
            p.sendintr()
        elif step == "^D":
            p.sendeof()
        elif step.startswith("RAW:"):
            p.send(step[4:].encode().decode("unicode_escape"))
        else:
            p.sendline(step)
        out, alive = quiet(p, first=60)
        results.append((step, out))
    p.close(force=True)
    return results


def main(tutorial_path: str) -> int:
    text = open(tutorial_path, encoding="utf-8").read()
    commands = [
        line[2:]
        for line in text.splitlines()
        if re.match(r"> (list|call|read|prompt|help|#)", line) and not line.startswith("> #clear")
    ]
    print(f"{len(commands)} REPL commands found in {tutorial_path}")

    # Prerequisites: both commands installed, no repo needed.
    out = subprocess.run(
        ["bash", "-lc", "mcphee --version && mcphee-hello-world --help"],
        capture_output=True,
        text=True,
        env=ENV,
    ).stdout
    check("prerequisites", "mcphee, version" in out and "usage: mcphee-hello-world" in out, out)

    # Option A plus every tutorial command.
    for step, out in session(
        "Option A", "mcphee connect --stdio mcphee-hello-world", commands + ["exit"]
    ):
        if step == "exit":
            check("exit", "Disconnecting..." in out, out[-200:])
            continue
        for want in EXPECT.get(step, []):
            check(
                step, want in out, f"expected {want!r}; got:\n{textwrap.indent(out[-600:], '    ')}"
            )
        markers = [m for m in BROKEN if m in out]
        if step not in EXPECTED_ERRORS:
            markers += ["Error"] if "─ Error ─" in out else []
        check(step, not markers, f"found {markers}; got:\n{textwrap.indent(out[-600:], '    ')}")

    # --demo shortcut.
    res = session("--demo", "mcphee connect --demo", ["call greet name=Demo", "quit"])
    check("--demo call", "Hello, Demo!" in res[0][1], res[0][1][-300:])
    check("quit", "Disconnecting..." in res[1][1], res[1][1][-200:])

    # Ctrl+C while a call is running returns to the prompt and keeps the session.
    tool_python = os.path.expanduser("~/.local/share/uv/tools/mcphee/bin/python")
    with open("/tmp/slow_server.py", "w") as fh:
        fh.write(
            "import time\nfrom fastmcp import FastMCP\nm = FastMCP('slow')\n"
            "@m.tool\ndef nap(s: int) -> str:\n    time.sleep(s)\n    return 'woke'\n"
            "@m.tool\ndef ping() -> str:\n    return 'pong'\n"
            "m.run(show_banner=False, log_level='CRITICAL')\n"
        )
    res = session(
        "Ctrl+C during a call",
        f'mcphee connect --stdio "{tool_python} /tmp/slow_server.py"',
        ["call nap s=30", "^C", "call ping", "exit"],
    )
    check("Ctrl+C interrupts", "Interrupted" in res[1][1], res[1][1][-300:])
    check("session survives Ctrl+C", "pong" in res[2][1], res[2][1][-300:])

    # Option B: saved profile.
    p = spawn("mcphee profile add hello-world")
    p.expect(r"Transport mode.*: ")
    p.sendline("stdio")
    p.expect("Shell command: ")
    p.sendline("mcphee-hello-world")
    p.expect(r"Add a header\? \[y/N\]: ")
    p.sendline("N")
    p.expect(pexpect.EOF)
    check("profile add", "saved" in clean(p.before), clean(p.before))
    res = session(
        "Option B", "mcphee connect --profile hello-world", ["call greet name=Alice", "exit"]
    )
    check("Option B call", "Hello, Alice!" in res[0][1], res[0][1][-300:])

    # Option C: HTTP server from the packaged command.
    start = (
        "(mcphee-hello-world --http >/tmp/http.log 2>&1 &); "
        'for i in $(seq 90); do grep -q "Uvicorn running" /tmp/http.log 2>/dev/null && break; '
        "sleep 1; done; head -1 /tmp/http.log; mcphee connect --http http://127.0.0.1:8000/mcp"
    )
    res = session("Option C", start, ["call greet name=Alice", "exit"])
    check("Option C call", "Hello, Alice!" in res[0][1], res[0][1][-300:])

    # Key bindings and completion. Each edit must produce a working call.
    emacs = session(
        "Emacs bindings",
        "mcphee connect --emacs --stdio mcphee-hello-world",
        [
            "RAW:greet name=Ctrl-A\\x01call \\x05\\r",  # Ctrl+A, insert, Ctrl+E
            "RAW:call greet name=Ctrl-W junk\\x17\\r",  # Ctrl+W deletes "junk"
            "RAW:call add a=1 b=2 garbage\\x01" + "\\x06" * 17 + "\\x0b\\r",  # Ctrl+F x17, Ctrl+K
            "exit",
        ],
    )
    check("Emacs Ctrl+A/E", "Hello, Ctrl-A!" in emacs[0][1], emacs[0][1][-300:])
    check("Emacs Ctrl+W", "Hello, Ctrl-W!" in emacs[1][1], emacs[1][1][-300:])
    check("Emacs Ctrl+F/K", "│ 3 " in emacs[2][1], emacs[2][1][-300:])
    vi = session(
        "Vi bindings, tab, Ctrl+D",
        "mcphee connect --stdio mcphee-hello-world",
        ["RAW:call gr\\t", "RAW:\\x15", "RAW:greet name=Vi\\x1b0icall \\r", "^D"],
    )
    check("tab completion", "greet" in vi[0][1], vi[0][1][-300:])
    check("Vi Esc/0/i", "Hello, Vi!" in vi[2][1], vi[2][1][-300:])

    print(f"\n{passes} checks passed, {len(failures)} failed")
    for failure in failures:
        print(f"FAIL {failure.splitlines()[0]}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "TUTORIAL.md"))
