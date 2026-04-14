"""Rich-based pretty-printing helpers for mcphee output."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


def _to_json_str(obj: Any) -> str:
    """Convert obj to a pretty-printed JSON string."""
    if isinstance(obj, str):
        try:
            parsed = json.loads(obj)
            return json.dumps(parsed, indent=2)
        except (json.JSONDecodeError, ValueError):
            return obj
    try:
        return json.dumps(obj, indent=2, default=str)
    except (TypeError, ValueError):
        return str(obj)


class Display:
    """Static display methods for all mcphee output."""

    # ------------------------------------------------------------------
    # List outputs
    # ------------------------------------------------------------------

    @staticmethod
    def tools_table(tools: list) -> None:
        table = Table(title="Tools", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="green", no_wrap=True)
        table.add_column("Description")
        table.add_column("Parameters", style="dim")

        for tool in tools:
            name = getattr(tool, "name", str(tool))
            desc = getattr(tool, "description", "") or ""
            schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None)
            if schema and isinstance(schema, dict):
                props = schema.get("properties", {})
                required = set(schema.get("required", []))
                param_parts = []
                for pname, pdef in props.items():
                    ptype = pdef.get("type", "any")
                    marker = "*" if pname in required else ""
                    param_parts.append(f"{pname}{marker}: {ptype}")
                params = ", ".join(param_parts) if param_parts else ""
            else:
                params = ""
            table.add_row(name, desc, params)

        console.print(table)

    @staticmethod
    def resources_table(resources: list, templates: list | None = None) -> None:
        table = Table(title="Resources", show_header=True, header_style="bold cyan")
        table.add_column("URI", style="green")
        table.add_column("Description")
        table.add_column("MIME Type", style="dim")

        for res in resources:
            uri = str(getattr(res, "uri", res))
            desc = getattr(res, "description", "") or ""
            mime = getattr(res, "mimeType", "") or ""
            table.add_row(uri, desc, mime)

        if templates:
            for tmpl in templates:
                uri = str(getattr(tmpl, "uriTemplate", tmpl))
                desc = getattr(tmpl, "description", "") or ""
                mime = getattr(tmpl, "mimeType", "") or ""
                table.add_row(f"[dim]{uri}[/dim]", f"[dim]{desc}[/dim]", f"[dim]{mime}[/dim]")

        if not resources and not templates:
            console.print("[dim]No resources available.[/dim]")
            return

        console.print(table)

    @staticmethod
    def prompts_table(prompts: list) -> None:
        table = Table(title="Prompts", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="green", no_wrap=True)
        table.add_column("Description")
        table.add_column("Arguments", style="dim")

        for prompt in prompts:
            name = getattr(prompt, "name", str(prompt))
            desc = getattr(prompt, "description", "") or ""
            args = getattr(prompt, "arguments", None) or []
            arg_parts = []
            for arg in args:
                aname = getattr(arg, "name", str(arg))
                required = getattr(arg, "required", False)
                marker = " (required)" if required else ""
                arg_parts.append(f"{aname}{marker}")
            arg_str = ", ".join(arg_parts) if arg_parts else ""
            table.add_row(name, desc, arg_str)

        if not prompts:
            console.print("[dim]No prompts available.[/dim]")
            return

        console.print(table)

    # ------------------------------------------------------------------
    # Result outputs
    # ------------------------------------------------------------------

    @staticmethod
    def tool_result(result: Any, json_mode: bool = False) -> None:
        """Render a tool call result."""
        # Extract text content from fastmcp result objects
        raw = _extract_result(result)

        if json_mode:
            print(_to_json_str(raw))
            return

        json_str = _to_json_str(raw)
        try:
            json.loads(json_str)
            syntax = Syntax(json_str, "json", theme="monokai", word_wrap=True)
            console.print(Panel(syntax, title="Result", border_style="green"))
        except (json.JSONDecodeError, ValueError):
            console.print(Panel(str(raw), title="Result", border_style="green"))

    @staticmethod
    def resource_content(content: Any, uri: str = "", json_mode: bool = False) -> None:
        """Render resource content."""
        items = content if isinstance(content, list) else [content]

        for item in items:
            # Text content
            text = getattr(item, "text", None)
            mime = getattr(item, "mimeType", "") or ""

            if text is not None:
                if json_mode:
                    print(text)
                    return
                # Pretty-print JSON resources
                if "json" in mime or _looks_like_json(text):
                    try:
                        parsed = json.loads(text)
                        syntax = Syntax(
                            json.dumps(parsed, indent=2), "json", theme="monokai", word_wrap=True
                        )
                        title = f"Resource: {uri}" + (f" ({mime})" if mime else "")
                        console.print(Panel(syntax, title=title, border_style="blue"))
                    except (json.JSONDecodeError, ValueError):
                        title = f"Resource: {uri}" + (f" ({mime})" if mime else "")
                        console.print(Panel(text, title=title, border_style="blue"))
                else:
                    title = f"Resource: {uri}" + (f" ({mime})" if mime else "")
                    console.print(Panel(text, title=title, border_style="blue"))
                continue

            # Binary content
            blob = getattr(item, "blob", None)
            if blob is not None:
                size = len(blob) if isinstance(blob, (bytes, bytearray)) else "?"
                msg = f"[dim][binary content: {size} bytes, mime: {mime}][/dim]"
                console.print(msg)
                continue

            # Fallback
            console.print(Panel(str(item), title=f"Resource: {uri}", border_style="blue"))

    @staticmethod
    def prompt_result(result: Any, name: str = "", json_mode: bool = False) -> None:
        """Render a prompt result (list of role/content messages)."""
        messages = getattr(result, "messages", None) or result or []

        if json_mode:
            out = []
            for msg in messages:
                role = getattr(msg, "role", "?")
                content = getattr(msg, "content", msg)
                text = getattr(content, "text", str(content))
                out.append({"role": role, "content": text})
            print(json.dumps(out, indent=2))
            return

        title = f"Prompt: {name}" if name else "Prompt"
        parts: list[str] = []
        for msg in messages:
            role = getattr(msg, "role", "?")
            content = getattr(msg, "content", msg)
            text = getattr(content, "text", str(content))
            parts.append(f"[bold][{role}][/bold]\n{text}")

        body = "\n\n".join(parts) if parts else "[dim](empty)[/dim]"
        console.print(Panel(body, title=title, border_style="magenta"))

    # ------------------------------------------------------------------
    # Status / error
    # ------------------------------------------------------------------

    @staticmethod
    def error(msg: str) -> None:
        console.print(Panel(f"[red]{msg}[/red]", title="Error", border_style="red"))

    @staticmethod
    def connected_banner(mode: str, target: str) -> None:
        console.print(
            Panel(
                f"[green]Connected[/green] via [bold]{mode}[/bold]\n[dim]{target}[/dim]\n"
                "Type [bold]help[/bold] for commands or [bold]exit[/bold] to quit.",
                title="[bold green]mcphee[/bold green]",
                border_style="green",
            )
        )

    @staticmethod
    def info(msg: str) -> None:
        console.print(f"[cyan]{msg}[/cyan]")

    @staticmethod
    def success(msg: str) -> None:
        console.print(f"[green]{msg}[/green]")

    @staticmethod
    def warning(msg: str) -> None:
        console.print(f"[yellow]{msg}[/yellow]")

    @staticmethod
    def help_table() -> None:
        """Print the REPL command reference."""
        table = Table(title="REPL Commands", show_header=True, header_style="bold cyan")
        table.add_column("Command", style="green", no_wrap=True)
        table.add_column("Syntax")
        table.add_column("Description")

        rows = [
            ("list tools", "list tools", "List all available tools"),
            ("list resources", "list resources", "List all available resources"),
            ("list prompts", "list prompts", "List all available prompts"),
            ("call", "call <tool> [key=value ...]", "Invoke a tool with arguments"),
            ("read", "read <uri>", "Read a resource by URI"),
            ("prompt", "prompt <name> [key=value ...]", "Get a prompt with arguments"),
            ("help", "help", "Show this help"),
            ("exit / quit", "exit", "Disconnect and exit"),
        ]
        for cmd, syntax, desc in rows:
            table.add_row(cmd, syntax, desc)

        console.print(table)

    @staticmethod
    def meta_help_table() -> None:
        """Print the # meta-command reference."""
        table = Table(title="Meta Commands (#)", show_header=True, header_style="bold cyan")
        table.add_column("Command", style="yellow", no_wrap=True)
        table.add_column("Syntax")
        table.add_column("Description")

        rows = [
            ("#clear", "#clear", "Clear the terminal screen"),
            ("#refresh", "#refresh", "Re-fetch tools/resources/prompts, rebuild completions"),
            ("#json", "#json", "Toggle JSON vs Rich pretty output"),
            ("#history", "#history [N]", "Show last N commands (default 20)"),
            ("#export", "#export [path]", "Export last result to a JSON file"),
            ("#timeout", "#timeout <seconds>", "Set request timeout"),
            ("#debug", "#debug", "Toggle verbose debug output"),
            ("#help", "#help", "Show this meta-command help"),
        ]
        for cmd, syntax, desc in rows:
            table.add_row(cmd, syntax, desc)

        console.print(table)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _extract_result(result: Any) -> Any:
    """Pull the meaningful value out of a fastmcp tool result."""
    # fastmcp 3.x: result has .data
    if hasattr(result, "data") and result.data is not None:
        return result.data

    # List of content blocks
    if hasattr(result, "content"):
        blocks = result.content
        if len(blocks) == 1:
            block = blocks[0]
            text = getattr(block, "text", None)
            if text is not None:
                try:
                    return json.loads(text)
                except (json.JSONDecodeError, ValueError):
                    return text
        texts = [getattr(b, "text", str(b)) for b in blocks]
        return texts

    # Iterable of content
    if isinstance(result, list):
        texts = []
        for item in result:
            text = getattr(item, "text", None)
            if text is not None:
                texts.append(text)
        return texts if len(texts) != 1 else texts[0]

    return result


def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith(("{", "["))
