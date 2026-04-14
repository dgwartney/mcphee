"""
hello-world-mcp: A tutorial MCP server built with FastMCP.

Demonstrates all three MCP primitives — tools, resources, and prompts —
with a variety of argument types and return shapes. Designed to be used
alongside the mcphee interactive CLI.

Usage:
    uv run python server.py            # stdio transport (default)
    uv run python server.py --http     # Streamable HTTP on 127.0.0.1:8000/mcp
    uv run python server.py --http --port 9000
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import math
import platform
import sys
from typing import Optional

from fastmcp import FastMCP

mcp = FastMCP(
    name="hello-world-mcp",
    instructions=(
        "A tutorial MCP server demonstrating tools, resources, and prompts. "
        "Use 'list tools', 'list resources', and 'list prompts' in mcphee to "
        "explore everything available. Every item has a description that "
        "explains what it demonstrates and how to call it."
    ),
)


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fastmcp_version() -> str:
    try:
        import fastmcp
        return getattr(fastmcp, "__version__", "unknown")
    except Exception:
        return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool
def greet(name: str, greeting: str = "Hello") -> str:
    """
    Return a personalized greeting string.

    Demonstrates: one required string argument and one optional string
    argument with a default value.

    Args:
        name: The name of the person to greet.
        greeting: The greeting word to use (default: Hello).

    Examples:
        call greet name=Alice
        call greet name=Bob greeting=Howdy
    """
    return f"{greeting}, {name}!"


@mcp.tool
def add(a: int, b: int) -> int:
    """
    Add two integers and return the sum.

    Demonstrates: two required integer arguments. mcphee automatically
    parses '3' and '7' as integers when passed as key=value pairs.

    Args:
        a: The first integer.
        b: The second integer.

    Examples:
        call add a=3 b=7
        call add a=-10 b=42
    """
    return a + b


@mcp.tool
def multiply(x: float, y: float) -> float:
    """
    Multiply two numbers and return the product.

    Demonstrates: float arguments. mcphee parses '3.14' as a float
    automatically.

    Args:
        x: The first number.
        y: The second number.

    Examples:
        call multiply x=3.14 y=2.0
        call multiply x=100 y=0.5
    """
    return x * y


@mcp.tool
def shout(text: str, exclaim: bool = True) -> str:
    """
    Convert text to uppercase, optionally appending exclamation marks.

    Demonstrates: a boolean argument. In mcphee, pass 'true' or 'false'
    (without quotes) to supply boolean values.

    Args:
        text: The text to shout.
        exclaim: Whether to append '!!!' (default: true).

    Examples:
        call shout text="hello world"
        call shout text="hello world" exclaim=false
    """
    result = text.upper()
    return result + "!!!" if exclaim else result


@mcp.tool
def calculate_circle(radius: float) -> dict:
    """
    Calculate geometric properties of a circle given its radius.

    Demonstrates: a tool that returns a structured dictionary (displayed
    as formatted JSON in mcphee). Shows how to return multiple related
    values in one call. Raises ValueError for invalid input.

    Args:
        radius: The circle's radius — must be a positive number.

    Examples:
        call calculate_circle radius=5
        call calculate_circle radius=3.14159
    """
    if radius <= 0:
        raise ValueError(f"radius must be positive, got {radius}")
    return {
        "radius": radius,
        "diameter": radius * 2,
        "area": round(math.pi * radius ** 2, 6),
        "circumference": round(2 * math.pi * radius, 6),
    }


@mcp.tool
def hash_text(text: str, algorithm: str = "sha256") -> dict:
    """
    Compute a cryptographic hash of the given text.

    Demonstrates: a string argument that acts like an enum. Supported
    algorithms: md5, sha1, sha256, sha512.

    Args:
        text: The text to hash.
        algorithm: Hash algorithm — md5, sha1, sha256, or sha512
                   (default: sha256).

    Examples:
        call hash_text text="hello world"
        call hash_text text="secret" algorithm=md5
    """
    supported = {"md5", "sha1", "sha256", "sha512"}
    if algorithm not in supported:
        raise ValueError(f"Unknown algorithm {algorithm!r}. Choose from: {sorted(supported)}")
    digest = hashlib.new(algorithm, text.encode()).hexdigest()
    return {"algorithm": algorithm, "input": text, "digest": digest}


@mcp.tool
def get_server_info() -> dict:
    """
    Return metadata about this MCP server and its runtime environment.

    Demonstrates: a zero-argument tool. Useful for verifying connectivity
    and understanding the server's capabilities.

    Examples:
        call get_server_info
    """
    return {
        "server_name": "hello-world-mcp",
        "fastmcp_version": _fastmcp_version(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "utc_now": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "capabilities": ["tools", "resources", "resource_templates", "prompts"],
    }


@mcp.tool
def repeat(text: str, times: int = 3) -> list[str]:
    """
    Repeat a string a given number of times, returning each copy as a list element.

    Demonstrates: a tool that returns a JSON array. mcphee displays this
    as a formatted list. The 'times' argument has a default and is capped
    at 20 to prevent abuse.

    Args:
        text: The text to repeat.
        times: How many copies to return (default: 3, max: 20).

    Examples:
        call repeat text=hello
        call repeat text=ping times=5
    """
    if not 1 <= times <= 20:
        raise ValueError(f"'times' must be between 1 and 20, got {times}")
    return [text] * times


@mcp.tool
def word_stats(text: str, include_chars: bool = False) -> dict:
    """
    Analyze a block of text and return word statistics.

    Demonstrates: a realistic multi-value analysis tool with an optional
    boolean flag that gates additional output. Good for exploring mcphee's
    JSON rendering of nested data structures.

    Args:
        text: The text to analyze.
        include_chars: If true, include per-character frequency counts
                       in the result (default: false).

    Examples:
        call word_stats text="The quick brown fox jumps over the lazy dog"
        call word_stats text="hello hello world" include_chars=true
    """
    words = text.lower().split()
    word_freq: dict[str, int] = {}
    for w in words:
        cleaned = w.strip(".,!?;:'\"()")
        if cleaned:
            word_freq[cleaned] = word_freq.get(cleaned, 0) + 1

    result: dict = {
        "char_count": len(text),
        "word_count": len(words),
        "unique_words": len(word_freq),
        "most_common": sorted(word_freq.items(), key=lambda kv: -kv[1])[:5],
    }
    if include_chars:
        char_freq: dict[str, int] = {}
        for c in text.lower():
            if c.isalpha():
                char_freq[c] = char_freq.get(c, 0) + 1
        result["char_frequency"] = dict(sorted(char_freq.items()))
    return result


@mcp.tool
def celsius_to_fahrenheit(celsius: float) -> dict:
    """
    Convert a temperature from Celsius to Fahrenheit (and Kelvin).

    Demonstrates: a simple unit-conversion tool that returns a dict with
    multiple temperature scales. A good first tool to try after connecting.

    Args:
        celsius: Temperature in degrees Celsius.

    Examples:
        call celsius_to_fahrenheit celsius=0
        call celsius_to_fahrenheit celsius=100
        call celsius_to_fahrenheit celsius=-40
    """
    return {
        "celsius": celsius,
        "fahrenheit": round((celsius * 9 / 5) + 32, 4),
        "kelvin": round(celsius + 273.15, 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Resources
# ─────────────────────────────────────────────────────────────────────────────

@mcp.resource("info://server")
def server_info_resource() -> str:
    """
    A static text resource describing this server's capabilities.

    Demonstrates: a static resource with a custom URI scheme. Static
    resources appear in 'list resources' and are read with 'read info://server'.
    """
    return f"""\
hello-world-mcp — Tutorial MCP Server
======================================
FastMCP version : {_fastmcp_version()}
Python version  : {sys.version.split()[0]}
Server started  : {datetime.datetime.now(datetime.timezone.utc).isoformat()}

TOOLS  (call <name> [key=value ...])
  greet                  Greeting with optional style
  add                    Integer addition
  multiply               Float multiplication
  shout                  Uppercase with bool flag
  calculate_circle       Circle geometry (dict return)
  hash_text              Cryptographic hash (enum-like arg)
  get_server_info        Server metadata (no args)
  repeat                 Repeat a string (list return)
  word_stats             Text analysis (optional bool flag)
  celsius_to_fahrenheit  Temperature conversion

RESOURCES  (read <uri>)
  info://server          This overview (you are here)
  info://mcp-primer      MCP concepts primer
  docs://tool/{{name}}    Per-tool documentation (template)

PROMPTS  (prompt <name> [key=value ...])
  explain_tool           Ask an LLM to explain a tool
  brainstorm             Generate ideas on a topic
  code_review            Review a code snippet
  summarize              Summarize a block of text

Tip: start with 'call get_server_info' to verify the connection.
"""


@mcp.resource("info://mcp-primer")
def mcp_primer_resource() -> str:
    """
    A short primer on Model Context Protocol (MCP) concepts.

    Demonstrates: a static resource used as embedded reference documentation.
    Read it with 'read info://mcp-primer'.
    """
    return """\
Model Context Protocol (MCP) — Quick Reference
===============================================

MCP is an open protocol for connecting AI models to external tools and data.
Servers expose three primitives:

1. TOOLS
   Functions that can be called to perform actions or compute results.
   They have a name, description, and typed JSON Schema input definition.
   Returns: text, structured data (JSON), or an error.
   Usage in mcphee: call <tool_name> [key=value ...]

2. RESOURCES
   Read-only data identified by a URI (similar to URLs).
   Two kinds:
     Static   — fixed URI, listed under 'list resources'
     Template — parameterized URI like docs://tool/{name}, also listed
   Returns: text or binary content.
   Usage in mcphee: read <uri>

3. PROMPTS
   Reusable message templates that accept typed arguments.
   Returns: one or more role-labeled messages (user/assistant) ready
   for an LLM to consume.
   Usage in mcphee: prompt <name> [key=value ...]

TRANSPORTS
   stdio   — server runs as a subprocess, communicates via stdin/stdout
   http    — server is a Streamable HTTP endpoint (POST to /mcp)
   sse     — server uses HTTP + Server-Sent Events (legacy, still supported)

This hello-world-mcp server supports both stdio and HTTP.
See README.md in the same directory for connection instructions.
"""


@mcp.resource("docs://tool/{name}")
def tool_docs(name: str) -> str:
    """
    Per-tool documentation, parameterized by tool name.

    Demonstrates: a TEMPLATE resource — a resource with a {placeholder}
    in its URI. Template resources appear in 'list resources' showing the
    URI pattern. Read by substituting the placeholder:
        read docs://tool/greet
        read docs://tool/hash_text
        read docs://tool/unknown   (returns a helpful error)

    Args:
        name: The tool name to look up.
    """
    docs: dict[str, str] = {
        "greet": (
            "greet(name: str, greeting: str = 'Hello') -> str\n\n"
            "Returns a greeting string. 'greeting' defaults to 'Hello'.\n\n"
            "Examples:\n"
            "  call greet name=Alice\n"
            "  call greet name=Bob greeting=Howdy"
        ),
        "add": (
            "add(a: int, b: int) -> int\n\n"
            "Returns the integer sum of a + b.\n\n"
            "Examples:\n"
            "  call add a=10 b=32\n"
            "  call add a=-5 b=3"
        ),
        "multiply": (
            "multiply(x: float, y: float) -> float\n\n"
            "Returns x * y as a float.\n\n"
            "Examples:\n"
            "  call multiply x=3.14 y=2.0\n"
            "  call multiply x=100 y=0.5"
        ),
        "shout": (
            "shout(text: str, exclaim: bool = True) -> str\n\n"
            "Uppercases text; appends '!!!' when exclaim=true.\n\n"
            "Examples:\n"
            "  call shout text=\"hello world\"\n"
            "  call shout text=\"quiet please\" exclaim=false"
        ),
        "calculate_circle": (
            "calculate_circle(radius: float) -> dict\n\n"
            "Returns {radius, diameter, area, circumference}.\n"
            "Raises ValueError for non-positive radius.\n\n"
            "Examples:\n"
            "  call calculate_circle radius=5\n"
            "  call calculate_circle radius=3.14159"
        ),
        "hash_text": (
            "hash_text(text: str, algorithm: str = 'sha256') -> dict\n\n"
            "Algorithms: md5, sha1, sha256, sha512.\n"
            "Returns {algorithm, input, digest}.\n\n"
            "Examples:\n"
            "  call hash_text text=\"hello world\"\n"
            "  call hash_text text=secret algorithm=md5"
        ),
        "get_server_info": (
            "get_server_info() -> dict\n\n"
            "No arguments. Returns server name, FastMCP version, Python "
            "version, platform, and current UTC time.\n\n"
            "Examples:\n"
            "  call get_server_info"
        ),
        "repeat": (
            "repeat(text: str, times: int = 3) -> list[str]\n\n"
            "Returns a list of 'times' copies of 'text'. Max 20.\n\n"
            "Examples:\n"
            "  call repeat text=hello\n"
            "  call repeat text=ping times=5"
        ),
        "word_stats": (
            "word_stats(text: str, include_chars: bool = False) -> dict\n\n"
            "Returns {char_count, word_count, unique_words, most_common}.\n"
            "With include_chars=true, also returns char_frequency.\n\n"
            "Examples:\n"
            "  call word_stats text=\"the quick brown fox\"\n"
            "  call word_stats text=\"hello hello world\" include_chars=true"
        ),
        "celsius_to_fahrenheit": (
            "celsius_to_fahrenheit(celsius: float) -> dict\n\n"
            "Returns {celsius, fahrenheit, kelvin}.\n\n"
            "Examples:\n"
            "  call celsius_to_fahrenheit celsius=0\n"
            "  call celsius_to_fahrenheit celsius=-40"
        ),
    }

    if name not in docs:
        known = "\n  ".join(sorted(docs.keys()))
        return f"No documentation found for tool {name!r}.\n\nAvailable tools:\n  {known}"

    return f"Tool: {name}\n{'=' * (6 + len(name))}\n{docs[name]}"


# ─────────────────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────────────────

@mcp.prompt
def explain_tool(tool_name: str) -> str:
    """
    Generate a prompt asking an LLM to explain a specific tool.

    Demonstrates: a prompt with a single required string argument.
    The returned string is wrapped as a user-role message.

    Args:
        tool_name: The name of the tool to explain.

    Examples:
        prompt explain_tool tool_name=hash_text
        prompt explain_tool tool_name=word_stats
    """
    return (
        f"Please explain the MCP tool '{tool_name}' in simple terms. "
        f"Describe what it does, what arguments it accepts, what it returns, "
        f"and give two practical examples of how someone might use it."
    )


@mcp.prompt
def brainstorm(topic: str, count: int = 5, style: str = "practical") -> str:
    """
    Generate a brainstorming prompt for a given topic.

    Demonstrates: a prompt with a required str arg, an optional int arg,
    and an optional str arg that controls the output style.

    Args:
        topic: The subject to brainstorm about.
        count: Number of ideas to generate (default: 5).
        style: Tone of ideas — practical, creative, or technical
               (default: practical).

    Examples:
        prompt brainstorm topic="MCP server use cases"
        prompt brainstorm topic="Python tools" count=10 style=creative
    """
    return (
        f"Generate {count} {style} ideas about: {topic}.\n\n"
        f"Format each idea as a numbered list item with a one-sentence explanation."
    )


@mcp.prompt
def code_review(
    code: str,
    language: str = "python",
    focus: str = "general",
    strict: bool = False,
) -> str:
    """
    Generate a code review prompt for a given code snippet.

    Demonstrates: a prompt with four arguments — two str, one str with
    default, and one bool. Good for testing how mcphee handles values
    with spaces (use quotes: code="def foo(): pass").

    Args:
        code: The code snippet to review.
        language: Programming language (default: python).
        focus: Review focus — general, security, performance, or
               readability (default: general).
        strict: If true, apply strict professional standards (default: false).

    Examples:
        prompt code_review code="def add(a,b): return a+b"
        prompt code_review code="SELECT * FROM users" language=sql focus=security
    """
    tone = "Apply strict professional standards." if strict else "Be constructive and balanced."
    return (
        f"Review the following {language} code with a focus on {focus}. "
        f"{tone}\n\n"
        f"```{language}\n{code}\n```\n\n"
        f"Provide: (1) a brief summary, (2) specific issues found, "
        f"(3) suggested improvements, (4) an overall assessment."
    )


@mcp.prompt
def summarize(
    text: str,
    max_sentences: Optional[int] = None,
    language: str = "english",
) -> str:
    """
    Generate a summarization prompt for a block of text.

    Demonstrates: a prompt with an Optional[int] argument — FastMCP
    exposes this as a non-required prompt argument that may be omitted.

    Args:
        text: The text to summarize.
        max_sentences: If set, limit the summary to this many sentences.
                       Omit for no length constraint.
        language: Language of the output summary (default: english).

    Examples:
        prompt summarize text="MCP is an open protocol for..."
        prompt summarize text="Long article here..." max_sentences=3
        prompt summarize text="Un article en français" language=french
    """
    length = f"in no more than {max_sentences} sentences" if max_sentences else "concisely"
    return f"Summarize the following text {length}, in {language}:\n\n{text}"


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="hello-world-mcp: Tutorial MCP server built with FastMCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python server.py                        stdio (default)
  uv run python server.py --http                 HTTP on 127.0.0.1:8000/mcp
  uv run python server.py --http --port 9000     custom port
  uv run python server.py --http --host 0.0.0.0  bind all interfaces
        """,
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run as Streamable HTTP server (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP bind host (default: 127.0.0.1, only used with --http)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP port (default: 8000, only used with --http)",
    )
    args = parser.parse_args()

    if args.http:
        print(
            f"Starting hello-world-mcp HTTP server on http://{args.host}:{args.port}/mcp",
            file=sys.stderr,
        )
        print(
            f"Connect with: mcphee connect --http http://{args.host}:{args.port}/mcp",
            file=sys.stderr,
        )
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")
