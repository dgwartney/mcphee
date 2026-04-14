"""Profile management — load/save named MCP connection configs (XDG-compliant)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import click

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


def _config_home() -> Path:
    """Return XDG_CONFIG_HOME or ~/.config as a resolved Path."""
    return Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()


def _profiles_path() -> Path:
    """Return the canonical path to profiles.toml under the XDG config directory."""
    return _config_home() / "mcphee" / "profiles.toml"


def _escape_toml_str(s: str) -> str:
    """Escape backslashes and double quotes for use in a TOML basic string."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


class ProfileManager:
    """Manage named MCP connection profiles stored in a TOML file."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _profiles_path()

    # ------------------------------------------------------------------
    # Internal TOML helpers
    # ------------------------------------------------------------------

    def _read_raw(self) -> dict[str, Any]:
        """Load the raw TOML data from disk. Returns {'profiles': {}} if the file is absent."""
        if not self._path.exists():
            return {"profiles": {}}
        with open(self._path, "rb") as f:
            data = tomllib.load(f)
        return data if "profiles" in data else {"profiles": {}}

    def _write_raw(self, data: dict[str, Any]) -> None:
        """Serialize profiles to TOML and write to disk.

        Uses a simple manual serializer that supports string and non-string scalar values
        and a single level of nested headers sub-tables. String values are escaped for
        backslashes and double quotes. Does not support multi-line values or TOML arrays.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for name, cfg in data.get("profiles", {}).items():
            lines.append(f"[profiles.{name}]")
            for key, val in cfg.items():
                if key == "headers" and isinstance(val, dict):
                    continue  # handled below
                if isinstance(val, str):
                    lines.append(f'{key} = "{_escape_toml_str(val)}"')
                else:
                    lines.append(f"{key} = {val}")
            # Write headers sub-table
            headers = cfg.get("headers", {})
            if headers:
                lines.append(f"[profiles.{name}.headers]")
                for hk, hv in headers.items():
                    lines.append(f'{hk} = "{_escape_toml_str(hv)}"')
            lines.append("")
        self._path.write_text("\n".join(lines) + "\n")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_profiles(self) -> dict[str, Any]:
        """Return all profiles as a dict keyed by name."""
        return self._read_raw().get("profiles", {})

    def get_profile(self, name: str) -> dict[str, Any]:
        """Return a single profile dict, or raise ClickException if not found."""
        profiles = self.load_profiles()
        if name not in profiles:
            available = ", ".join(profiles.keys()) or "(none)"
            raise click.ClickException(
                f"Profile {name!r} not found. Available: {available}"
            )
        return profiles[name]

    def save_profile(
        self,
        name: str,
        mode: str,
        target: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Save or overwrite a named profile."""
        data = self._read_raw()
        profiles = data.setdefault("profiles", {})
        entry: dict[str, Any] = {"mode": mode}
        if mode == "stdio":
            entry["command"] = target
        else:
            entry["url"] = target
        if headers:
            entry["headers"] = headers
        profiles[name] = entry
        self._write_raw(data)

    def delete_profile(self, name: str) -> None:
        """Remove a profile by name. Raises ClickException if not found."""
        data = self._read_raw()
        profiles = data.get("profiles", {})
        if name not in profiles:
            raise click.ClickException(f"Profile {name!r} not found.")
        del profiles[name]
        data["profiles"] = profiles
        self._write_raw(data)

    @property
    def path(self) -> Path:
        """The resolved path to the profiles TOML file."""
        return self._path
