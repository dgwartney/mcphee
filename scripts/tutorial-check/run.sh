#!/usr/bin/env bash
# Walk TUTORIAL.md on a fresh Linux machine (Docker) and fail if any step breaks.
#
#   scripts/tutorial-check/run.sh              # test a wheel built from this checkout
#   scripts/tutorial-check/run.sh --pypi       # test the latest release on PyPI
#   scripts/tutorial-check/run.sh --pypi 0.2.0 # test a specific PyPI release
#
# Behind a TLS-intercepting proxy, set EXTRA_CA_CERT to the proxy's root CA (PEM).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
ctx="$(mktemp -d)"
trap 'rm -rf "$ctx"' EXIT
mkdir -p "$ctx/dist" "$ctx/certs"
cp "$here/Dockerfile" "$here/check.py" "$repo/TUTORIAL.md" "$ctx/"

if [[ "${1:-}" == "--pypi" ]]; then
  mcphee="mcphee${2:+==$2}"
else
  uv build --wheel -q -o "$ctx/dist" "$repo"
  mcphee="./dist/$(basename "$ctx"/dist/*.whl)"
fi

if [[ -n "${EXTRA_CA_CERT:-}" ]]; then
  cp "$EXTRA_CA_CERT" "$ctx/certs/extra-ca.crt"
fi

echo "Testing: $mcphee"
docker build -q -t mcphee-tutorial-check --build-arg "MCPHEE=$mcphee" "$ctx" >/dev/null
docker run --rm mcphee-tutorial-check
