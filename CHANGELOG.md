# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-10-23

### Added

- README: "Prerequisite: install uv" section (macOS/Linux, Windows, Homebrew, winget, PATH setup)
- README, TUTORIAL and example: documented the `#payload on|off` and `#loglevel [LEVEL]` meta-commands
- `RELEASING.md` with the release process and Trusted Publishing configuration
- `CLAUDE.md` with project guidance for AI coding assistants

### Changed

- TUTORIAL and the hello-world example install mcphee from PyPI (`uv tool install mcphee`)
- TUTORIAL: `#debug` is described accurately (argument echo and DEBUG logging); raw request and
  response payloads are shown by `#payload`
- Release instructions moved out of the README into `RELEASING.md`

### Fixed

- `connect --stdio 'npx …'` / `'bunx …'` failed with `Script not found: …/npx`; package runners now
  use the generic stdio transport, and only `node <script.js>` uses the Node transport
- `mcphee.__version__` was hard-coded to `0.1.0`; it now reads the installed package version
- CI: line-length lint errors in `display.py`; test coverage raised from 85% to 94%, above the 90% gate

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

[Unreleased]: https://github.com/dgwartney/mcphee/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/dgwartney/mcphee/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/dgwartney/mcphee/releases/tag/v0.1.0
