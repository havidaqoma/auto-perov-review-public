# Container manifest for the reproducibility tiers.
#
# The Supplementary Information claims the runtime is identical across host
# operating systems. This file is what makes that true: it pins the
# interpreter, the Python packages, pandoc and tectonic, so a reviewer on
# macOS or Linux runs the same toolchain that produced the artifacts on
# Windows.
#
# Build and run tier 0 (offline verification, no model calls, no network):
#
#   docker build -t auto-perov-review .
#   docker run --rm auto-perov-review
#
# Tier 1 (rebuild the PDFs) is already possible in this image, because pandoc
# and tectonic are installed:
#
#   docker run --rm -it auto-perov-review bash
#   python reproduce.py --tier 1
#
# Tier 2 needs network and model credentials and is deliberately not wired
# into this image. See README.md.

FROM python:3.11.15-slim-bookworm

# tectonic needs a TLS stack and fontconfig at runtime; it fetches the LaTeX
# packages it needs on first use, which is why this image does not carry a
# multi-gigabyte TeX Live installation.
RUN apt-get update && apt-get install -y --no-install-recommends \
        pandoc=3.11* \
        ca-certificates \
        fontconfig \
        libfontconfig1 \
        libgraphite2-3 \
        libharfbuzz0b \
        libicu72 \
        libssl3 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Pinned to the version recorded in env.lock.json. Installed from the upstream
# release rather than apt, because Debian does not package tectonic and an
# unpinned installer script would defeat the point of this file.
ARG TECTONIC_VERSION=0.15.0
RUN curl -fsSL \
      "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40${TECTONIC_VERSION}/tectonic-${TECTONIC_VERSION}-x86_64-unknown-linux-gnu.tar.gz" \
      -o /tmp/tectonic.tar.gz \
    && tar -xzf /tmp/tectonic.tar.gz -C /usr/local/bin tectonic \
    && rm /tmp/tectonic.tar.gz \
    && tectonic --version

WORKDIR /repo

# Dependencies before source, so editing a script does not reinstall numpy.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fail the build if the image does not match its own manifest. Better to find
# a drifted pin here than to have a reviewer discover it.
RUN python tools/check_env.py

CMD ["python", "reproduce.py", "--tier", "0"]
