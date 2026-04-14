# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-14

### Added

- Interactive REPL shell powered by `prompt_toolkit` with Vi mode (default) and Emacs mode (`--emacs`)
- MCP commands: `list tools`, `list resources`, `list prompts`, `call`, `read`, `prompt`, `help`, `exit`
- Meta-commands: `#clear`, `#refresh`, `#json`, `#history`, `#export`, `#timeout`, `#debug`, `#help`
- Transport support: stdio (subprocess), SSE (HTTP + Server-Sent Events), Streamable HTTP
- Named connection profiles stored in XDG-compliant `~/.config/mcphee/profiles.toml`
- Persistent command history in XDG-compliant `~/.local/share/mcphee/history`
- Tab completion for tool names, resource URIs, prompt names, and their parameters
- Auto-suggestions from history (fish-shell style)
- Rich pretty output with syntax-highlighted JSON; toggle to raw JSON with `--json` or `#json`
- `profile list`, `profile add`, `profile remove` subcommands
- PyPI-publishable package via `uv build` / `uv publish`
- GitHub Actions CI: lint (ruff) + test (pytest --cov ≥ 90%) on Python 3.11, 3.12, 3.13

[Unreleased]: https://github.com/dgwartney/mcphee/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dgwartney/mcphee/releases/tag/v0.1.0
