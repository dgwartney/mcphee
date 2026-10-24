# Tutorial check

Walks [TUTORIAL.md](../../TUTORIAL.md) on a fresh Linux machine and fails if any step breaks.
The machine is a Debian container with no Python, no uv and no git. It follows the README to
install uv, installs mcphee with `uv tool install`, then drives the real `mcphee` REPL in a
terminal.

## Run it

Requires Docker.

```bash
scripts/tutorial-check/run.sh              # a wheel built from this checkout
scripts/tutorial-check/run.sh --pypi       # the latest release on PyPI
scripts/tutorial-check/run.sh --pypi 0.2.0 # a specific release
```

The last line reads `N checks passed, M failed`, and the exit status is non-zero on any
failure. A run takes a few minutes.

Run it before every release (see [RELEASING.md](../../RELEASING.md)), and again with `--pypi`
after publishing.

## Behind a corporate proxy

If your network intercepts TLS (Zscaler and similar), the container cannot verify HTTPS until
it trusts the proxy's root CA. Export the CA as PEM and pass it with `EXTRA_CA_CERT`. It is
copied into the container's trust store for that build only and is never committed.

```bash
# macOS example (Zscaler)
security find-certificate -a -c "Zscaler Root CA" -p /Library/Keychains/System.keychain > /tmp/proxy-ca.pem
EXTRA_CA_CERT=/tmp/proxy-ca.pem scripts/tutorial-check/run.sh
```

## What it checks

- **Prerequisites:** `mcphee --version` and `mcphee-hello-world --help` work with no repo checkout.
- **Option A:** every `> command` line in TUTORIAL.md runs against `mcphee connect --stdio
  mcphee-hello-world`.
  - Key commands are compared with the output the tutorial shows.
  - Every command is checked for broken output: tracebacks, unknown command, and unexpected
    error panels.
- **`--demo`**, **Option B** (`profile add` plus `--profile`) and **Option C** (`mcphee-hello-world
  --http` plus `--http`).
- **Ctrl+C** during a slow call prints `Interrupted`, and the session keeps working.
- **Emacs** (Ctrl+A/E/W/F/K) and **Vi** (Esc, `0`, `i`) editing, Tab completion and Ctrl+D.

## When the tutorial changes

`check.py` reads its commands from TUTORIAL.md, so new `> ...` lines are exercised
automatically. If you change an example's expected output, update its entry in `EXPECT` in
`check.py`.
