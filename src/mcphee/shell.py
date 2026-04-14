"""Interactive REPL shell for mcphee using prompt_toolkit."""

from __future__ import annotations

import json
import os
import shlex
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from mcphee.connection import MCPConnection
from mcphee.display import Display, console

# ------------------------------------------------------------------
# XDG history path
# ------------------------------------------------------------------

def _history_path() -> Path:
    data_home = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser()
    path = data_home / "mcphee" / "history"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# ------------------------------------------------------------------
# Argument parser
# ------------------------------------------------------------------

def parse_kv_args(tokens: list[str]) -> dict[str, Any]:
    """Parse ['key=value', ...] into a typed dict.

    Values are JSON-decoded when possible (true→bool, 3→int, etc.).
    Quoted values with spaces are already split by shlex in the caller.
    """
    result: dict[str, Any] = {}
    for token in tokens:
        if "=" not in token:
            raise ValueError(f"Expected key=value, got: {token!r}")
        key, _, raw = token.partition("=")
        key = key.strip()
        raw = raw.strip()
        # Strip surrounding quotes
        if (raw.startswith('"') and raw.endswith('"')) or (
            raw.startswith("'") and raw.endswith("'")
        ):
            raw = raw[1:-1]
        # Attempt JSON decode for booleans, numbers, arrays, objects
        try:
            result[key] = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            result[key] = raw
    return result


# ------------------------------------------------------------------
# Tab completion
# ------------------------------------------------------------------

class MCPCompleter(Completer):
    """Dynamic completer that suggests MCP entities and their parameters."""

    def __init__(self, shell: "MCPShell") -> None:
        self._shell = shell

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        try:
            tokens = shlex.split(text)
        except ValueError:
            tokens = text.split()

        # If text ends with a space, we're starting a new token
        ends_with_space = text.endswith(" ")
        n = len(tokens)

        # --- top-level command ---
        if n == 0 or (n == 1 and not ends_with_space):
            word = tokens[0] if tokens else ""
            for cmd in ("list", "call", "read", "prompt", "help", "exit", "quit"):
                if cmd.startswith(word):
                    yield Completion(cmd, start_position=-len(word))
            return

        cmd = tokens[0]

        # --- list <subcommand> ---
        if cmd == "list":
            if n == 1 and ends_with_space or (n == 2 and not ends_with_space):
                word = tokens[1] if n == 2 else ""
                for sub in ("tools", "resources", "prompts"):
                    if sub.startswith(word):
                        yield Completion(sub, start_position=-len(word))
            return

        # --- call <tool_name> [key=...] ---
        if cmd == "call":
            if n == 1 and ends_with_space or (n == 2 and not ends_with_space):
                word = tokens[1] if n == 2 else ""
                for name in self._shell.tool_names:
                    if name.startswith(word):
                        yield Completion(name, start_position=-len(word))
                return
            if n >= 2 and (ends_with_space or n > 2):
                # Complete key= names for the selected tool
                tool_name = tokens[1]
                schema = self._shell.tool_schemas.get(tool_name, {})
                props = schema.get("properties", {})
                already = {t.split("=")[0] for t in tokens[2:]}
                word = "" if ends_with_space else tokens[-1].split("=")[0]
                for pname in props:
                    if pname not in already and pname.startswith(word):
                        yield Completion(f"{pname}=", start_position=-len(word))
            return

        # --- read <uri> ---
        if cmd == "read":
            if n == 1 and ends_with_space or (n == 2 and not ends_with_space):
                word = tokens[1] if n == 2 else ""
                for uri in self._shell.resource_uris:
                    if uri.startswith(word):
                        yield Completion(uri, start_position=-len(word))
            return

        # --- prompt <name> [key=...] ---
        if cmd == "prompt":
            if n == 1 and ends_with_space or (n == 2 and not ends_with_space):
                word = tokens[1] if n == 2 else ""
                for name in self._shell.prompt_names:
                    if name.startswith(word):
                        yield Completion(name, start_position=-len(word))
                return
            if n >= 2 and (ends_with_space or n > 2):
                prompt_name = tokens[1]
                arg_names = self._shell.prompt_args.get(prompt_name, [])
                already = {t.split("=")[0] for t in tokens[2:]}
                word = "" if ends_with_space else tokens[-1].split("=")[0]
                for aname in arg_names:
                    if aname not in already and aname.startswith(word):
                        yield Completion(f"{aname}=", start_position=-len(word))
            return


# ------------------------------------------------------------------
# Shell
# ------------------------------------------------------------------

class MCPShell:
    """Interactive REPL that wraps a connected MCPConnection."""

    def __init__(
        self,
        conn: MCPConnection,
        mode: str,
        target: str,
        json_mode: bool = False,
        vi_mode: bool = True,
    ) -> None:
        self._conn = conn
        self._mode = mode
        self._target = target
        self._json_mode = json_mode
        self._vi_mode = vi_mode

        # Completion caches (populated at connect time)
        self.tool_names: list[str] = []
        self.tool_schemas: dict[str, dict] = {}
        self.resource_uris: list[str] = []
        self.prompt_names: list[str] = []
        self.prompt_args: dict[str, list[str]] = {}

        # Track last result for #export
        self._last_result: Any = None

        # Debug mode
        self._debug = False

        self._session: PromptSession | None = None

    # ------------------------------------------------------------------
    # Completion cache
    # ------------------------------------------------------------------

    def _load_caches(self) -> None:
        """Fetch tools/resources/prompts and populate completion data."""
        try:
            tools = self._conn.list_tools()
            self.tool_names = [getattr(t, "name", str(t)) for t in tools]
            self.tool_schemas = {}
            for t in tools:
                name = getattr(t, "name", str(t))
                schema = getattr(t, "inputSchema", None) or getattr(t, "input_schema", None)
                self.tool_schemas[name] = schema if isinstance(schema, dict) else {}
        except Exception:
            pass

        try:
            resources = self._conn.list_resources()
            templates = self._conn.list_resource_templates()
            self.resource_uris = [
                str(getattr(r, "uri", r)) for r in resources
            ] + [
                str(getattr(t, "uriTemplate", t)) for t in templates
            ]
        except Exception:
            pass

        try:
            prompts = self._conn.list_prompts()
            self.prompt_names = [getattr(p, "name", str(p)) for p in prompts]
            self.prompt_args = {}
            for p in prompts:
                name = getattr(p, "name", str(p))
                args = getattr(p, "arguments", None) or []
                self.prompt_args[name] = [getattr(a, "name", str(a)) for a in args]
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the REPL loop."""
        self._load_caches()
        Display.connected_banner(self._mode, self._target)

        history = FileHistory(str(_history_path()))
        completer = MCPCompleter(self)
        style = Style.from_dict({"prompt": "bold green"})

        self._session = PromptSession(
            history=history,
            completer=completer,
            auto_suggest=AutoSuggestFromHistory(),
            vi_mode=self._vi_mode,
            style=style,
            complete_while_typing=False,
        )

        while True:
            try:
                line = self._session.prompt("> ").strip()
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

            if not line:
                continue

            if self._dispatch(line):
                break  # exit/quit returned True

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def _dispatch(self, line: str) -> bool:
        """Route input to a handler. Returns True to exit the loop."""
        # Meta-commands
        if line.startswith("#"):
            self._handle_meta(line)
            return False

        try:
            tokens = shlex.split(line)
        except ValueError as exc:
            Display.error(f"Parse error: {exc}")
            return False

        if not tokens:
            return False

        cmd = tokens[0].lower()

        if cmd in ("exit", "quit"):
            return self._cmd_exit()
        elif cmd == "list":
            self._cmd_list(tokens[1:])
        elif cmd == "call":
            self._cmd_call(tokens[1:])
        elif cmd == "read":
            self._cmd_read(tokens[1:])
        elif cmd == "prompt":
            self._cmd_prompt(tokens[1:])
        elif cmd == "help":
            self._cmd_help(tokens[1:])
        else:
            Display.error(f"Unknown command: {cmd!r}. Type 'help' for available commands.")

        return False

    # ------------------------------------------------------------------
    # MCP commands
    # ------------------------------------------------------------------

    def _cmd_list(self, args: list[str]) -> None:
        if not args:
            Display.error("Usage: list tools | list resources | list prompts")
            return
        sub = args[0].lower()
        try:
            if sub == "tools":
                tools = self._conn.list_tools()
                if self._json_mode:
                    data = [{"name": getattr(t, "name", str(t))} for t in tools]
                    print(json.dumps(data, indent=2))
                else:
                    Display.tools_table(tools)
            elif sub == "resources":
                resources = self._conn.list_resources()
                templates = self._conn.list_resource_templates()
                if self._json_mode:
                    data = [{"uri": str(getattr(r, "uri", r))} for r in resources]
                    print(json.dumps(data, indent=2))
                else:
                    Display.resources_table(resources, templates)
            elif sub == "prompts":
                prompts = self._conn.list_prompts()
                if self._json_mode:
                    data = [{"name": getattr(p, "name", str(p))} for p in prompts]
                    print(json.dumps(data, indent=2))
                else:
                    Display.prompts_table(prompts)
            else:
                Display.error(f"Unknown: {sub!r}. Try: list tools | list resources | list prompts")
        except Exception as exc:
            Display.error(str(exc))

    def _cmd_call(self, args: list[str]) -> None:
        if not args:
            Display.error("Usage: call <tool_name> [key=value ...]")
            return
        tool_name = args[0]
        try:
            kv_args = parse_kv_args(args[1:])
        except ValueError as exc:
            Display.error(str(exc))
            return

        if self._debug:
            Display.info(f"[debug] call_tool({tool_name!r}, {kv_args})")

        try:
            result = self._conn.call_tool(tool_name, kv_args)
            self._last_result = result
            Display.tool_result(result, json_mode=self._json_mode)
        except Exception as exc:
            Display.error(str(exc))

    def _cmd_read(self, args: list[str]) -> None:
        if not args:
            Display.error("Usage: read <resource_uri>")
            return
        uri = args[0]

        if self._debug:
            Display.info(f"[debug] read_resource({uri!r})")

        try:
            content = self._conn.read_resource(uri)
            self._last_result = content
            Display.resource_content(content, uri=uri, json_mode=self._json_mode)
        except Exception as exc:
            Display.error(str(exc))

    def _cmd_prompt(self, args: list[str]) -> None:
        if not args:
            Display.error("Usage: prompt <name> [key=value ...]")
            return
        prompt_name = args[0]
        try:
            kv_args = parse_kv_args(args[1:])
        except ValueError as exc:
            Display.error(str(exc))
            return

        if self._debug:
            Display.info(f"[debug] get_prompt({prompt_name!r}, {kv_args})")

        try:
            result = self._conn.get_prompt(prompt_name, kv_args)
            self._last_result = result
            Display.prompt_result(result, name=prompt_name, json_mode=self._json_mode)
        except Exception as exc:
            Display.error(str(exc))

    def _cmd_help(self, args: list[str]) -> None:
        Display.help_table()

    def _cmd_exit(self) -> bool:
        Display.info("Disconnecting...")
        return True

    # ------------------------------------------------------------------
    # Meta-commands
    # ------------------------------------------------------------------

    def _handle_meta(self, line: str) -> None:
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "#clear":
            print("\033[2J\033[H", end="")
        elif cmd == "#refresh":
            self._meta_refresh()
        elif cmd == "#json":
            self._json_mode = not self._json_mode
            state = "ON" if self._json_mode else "OFF"
            Display.info(f"JSON mode: {state}")
        elif cmd == "#history":
            self._meta_history(rest)
        elif cmd == "#export":
            self._meta_export(rest)
        elif cmd == "#timeout":
            self._meta_timeout(rest)
        elif cmd == "#debug":
            self._debug = not self._debug
            state = "ON" if self._debug else "OFF"
            Display.info(f"Debug mode: {state}")
        elif cmd == "#help":
            Display.meta_help_table()
        else:
            Display.error(f"Unknown meta-command: {cmd!r}. Type '#help' for meta-commands.")

    def _meta_refresh(self) -> None:
        Display.info("Refreshing...")
        self._load_caches()
        Display.success(
            f"Refreshed: {len(self.tool_names)} tools, "
            f"{len(self.resource_uris)} resources, "
            f"{len(self.prompt_names)} prompts"
        )

    def _meta_history(self, rest: str) -> None:
        n = 20
        if rest:
            try:
                n = int(rest)
            except ValueError:
                Display.error(f"#history expects a number, got: {rest!r}")
                return

        if self._session and self._session.history:
            all_entries = list(self._session.history.load_history_strings())
            # load_history_strings returns newest first
            entries = all_entries[:n]
            entries.reverse()
            for i, entry in enumerate(entries, 1):
                console.print(f"[dim]{i:4d}[/dim]  {entry}")
        else:
            Display.warning("No history available.")

    def _meta_export(self, rest: str) -> None:
        path = rest if rest else "mcphee_export.json"
        if self._last_result is None:
            Display.warning("No result to export yet.")
            return
        try:
            import json as _json
            out = _json.dumps(self._last_result, indent=2, default=str)
            Path(path).write_text(out)
            Display.success(f"Exported to: {path}")
        except Exception as exc:
            Display.error(f"Export failed: {exc}")

    def _meta_timeout(self, rest: str) -> None:
        if not rest:
            Display.info(f"Current timeout: {self._conn.timeout}s")
            return
        try:
            secs = float(rest)
            if secs <= 0:
                raise ValueError
            self._conn.timeout = secs
            Display.success(f"Timeout set to {secs}s")
        except ValueError:
            Display.error(f"#timeout expects a positive number, got: {rest!r}")
