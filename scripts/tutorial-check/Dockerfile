# A "new machine" for walking TUTORIAL.md: Debian with no Python, no uv and no git.
# Built by run.sh, which assembles the build context (see README.md).
FROM debian:bookworm-slim

# certs/ holds an optional corporate root CA (*.crt) for TLS-intercepting proxies; it may be empty.
COPY certs/ /usr/local/share/ca-certificates/
RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends curl ca-certificates >/dev/null \
 && update-ca-certificates >/dev/null 2>&1 \
 && rm -rf /var/lib/apt/lists/*
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

RUN useradd -m learner
USER learner
WORKDIR /home/learner
ENV PATH=/home/learner/.local/bin:$PATH

# The README's documented uv install.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# MCPHEE is what `uv tool install` gets: "mcphee" (PyPI), "mcphee==X.Y.Z", or ./dist/<wheel>.
ARG MCPHEE=mcphee
COPY --chown=learner dist/ dist/
RUN uv tool install "$MCPHEE"

COPY --chown=learner check.py TUTORIAL.md ./
CMD ["uv", "run", "--no-project", "--with", "pexpect", "python", "-I", "check.py", "TUTORIAL.md"]
