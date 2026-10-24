# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `scripts/tutorial-check/`: walks TUTORIAL.md on a fresh Linux container (no Python, uv or git)
  and fails on any broken step. It runs in CI on pull requests that touch the tutorial or the
  package.

## [0.2.0] - 2026-10-23

### Added

- README: "Prerequisite: install uv" section (macOS/Linux, Windows, Homebrew, winget, PATH setup)
- README, TUTORIAL and example: documented the `#payload on|off` and `#loglevel [LEVEL]` meta-commands
- `RELEASING.md` with the release process and Trusted Publishing configuration
- `CLAUDE.md` with project guidance for AI coding assistants
- README and TUTORIAL: Emacs key bindings
- The hello-world example server ships inside the package (`mcphee.examples.hello_world`) with a
  `mcphee-hello-world` command (`--http`, `--host`, `--port`) and `mcphee connect --demo`, so the
  tutorial needs only `uv tool install mcphee` (no git clone)

### Changed

- TUTORIAL and the hello-world example install mcphee from PyPI (`uv tool install mcphee`)
- TUTORIAL: `#debug` is described accurately (argument echo and DEBUG logging); raw request and
  response payloads are shown by `#payload`
- Release instructions moved out of the README into `RELEASING.md`
- TUTORIAL: expected outputs updated to match a validated run on a fresh Linux machine
- hello-world example in stdio mode no longer prints the FastMCP banner, update notice or server
  tracebacks into the mcphee terminal

### Fixed

- `connect --stdio 'npx …'` / `'bunx …'` failed with `Script not found: …/npx`; package runners now
  use the generic stdio transport, and only `node <script.js>` uses the Node transport
- Ctrl+C while a request is running now cancels it and returns to the prompt; previously it
  exited mcphee
- Messages containing square brackets lost text (`[debug]` prefixes, `[key=value ...]` in usage
  errors) because they were parsed as Rich markup
- hello-world example: `prompt summarize … max_sentences=2` failed with a pydantic error
- `mcphee.__version__` was hard-coded to `0.1.0`; it now reads the installed package version
- The example server could not start on a fresh machine: `python server.py` lacked `fastmcp`, and
  its separate lockfile pinned a `cffi` with no Python 3.15 wheel
- CI: line-length lint errors in `display.py`; test coverage raised from 85% to 94%, above the 90% gate

### Removed

- The separate `examples/hello-world-mcp/` project (`server.py`, `pyproject.toml`, `uv.lock`);
  the server moved into the package

## [0.1.0] - 2026-10-23

### Added

- Interactive REPL shell powered by `prompt_toolkit` with Vi mode (default) and Emacs mode (`--emacs`)
- MCP commands: `list tools`, `list resources`, `list prompts`, `call`, `read`, `prompt`, `help`, `exit`
- Meta-commands: `#clear`, `#refresh`, `#json`, `#history`, `#export`, `#timeout`, `#payload`, `#debug`, `#loglevel`, `#help`
- Transport support: stdio (subprocess), SSE (HTTP + Server-Sent Events), Streamable HTTP
- Named connection profiles stored in XDG-compliant `~/.config/mcphee/profiles.toml`
- Persistent command history in XDG-compliant `~/.local/share/mcphee/history`
- Tab completion for tool names, resource URIs, prompt names, and their parameters
- Auto-suggestions from history (fish-shell style)
- Rich pretty output with syntax-highlighted JSON; toggle to raw JSON with `--json` or `#json`
- `profile list`, `profile add`, `profile remove` subcommands
- Requires fastmcp 3.x (`fastmcp>=3.2.4,<4`)
- Published to PyPI by GitHub Actions using Trusted Publishing (OIDC)
- GitHub Actions CI: lint (ruff) + test (pytest, coverage gate 90%) on Python 3.11, 3.12, 3.13

[Unreleased]: https://github.com/dgwartney/mcphee/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/dgwartney/mcphee/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/dgwartney/mcphee/releases/tag/v0.1.0
