# Reproducible build environment for the real NASA JPL F Prime (F´)
# target artifact — stack #2, Phase 6 (generalizability).
#
# CORRECTED after a real failed build attempt (2026-08-03): the original
# version of this file assumed `pip install -e .` on a bare clone of
# nasa/fprime would install the F´ tool suite. It does not — the
# framework repo has no setup.py/pyproject.toml at its root (the tools
# are separate PyPI packages: fprime-tools, fprime-gds, fprime-fpp, etc.,
# all pinned in the repo's own requirements.txt). Confirmed against the
# authoritative F´ installation guide
# (nasa/fprime devel branch, docs/getting-started/installing-fprime.md,
# "Working With An Existing Project" section) after the first attempt
# failed with "does not appear to be a Python project: neither 'setup.py'
# nor 'pyproject.toml' found." Fixed by installing from the framework's
# own pinned requirements.txt instead, then using `fprime-util` (one of
# those installed tools) to generate and build the framework's own `Ref`
# reference deployment directly — confirmed present at this tag via
# Ref/CMakeLists.txt.
#
# Per the same source-handling policy as Legal-Data-Sourcing-Notes.md
# § 3a (there written for cFS, applied identically here): F´ source is
# never vendored into this repository. This Dockerfile clones it fresh
# at a pinned tag on every build, preserving upstream LICENSE/NOTICE
# files as distributed.
#
# Pinned reference (confirmed via github.com/nasa/fprime/releases and
# the repo's own requirements.txt at this tag, 2026-08-03):
#   Repository: https://github.com/nasa/fprime
#   Tag:        v4.2.2 (latest tagged release at time of pinning)
#   License:    Apache License 2.0, copyright California Institute of
#               Technology, "United States Government Sponsorship
#               acknowledged" (verified directly from the repo's
#               LICENSE.txt at the devel branch)
#   Pinned tool versions (from requirements.txt at v4.2.2):
#               fprime-tools==4.2.1, fprime-gds==4.2.1,
#               fprime-fpp==3.2.0, cmake==3.26.0 (installed via pip, not
#               apt — Ref/CMakeLists.txt requires CMake >= 3.26, newer
#               than Ubuntu 22.04's default apt package)
#
# If this tag is later superseded, re-pin deliberately and record the
# change in Legal-Data-Sourcing-Notes.md § 5 change log — don't silently
# float to `devel`.

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        build-essential \
        python3 \
        python3-venv \
        python3-pip \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Pinned checkout, never copied/vendored into this repo.
RUN git clone --recursive --branch v4.2.2 https://github.com/nasa/fprime.git fprime-src

WORKDIR /build/fprime-src

# Install the F´ tool suite from the framework's own pinned
# requirements.txt (fprime-tools, fprime-gds, fprime-fpp, and a
# compatible `cmake` — installed via pip specifically because
# Ref/CMakeLists.txt requires CMake >= 3.26, newer than what Ubuntu
# 22.04's apt repository ships).
RUN python3 -m venv /build/venv \
    && /build/venv/bin/pip install --upgrade pip \
    && /build/venv/bin/pip install -r requirements.txt

ENV PATH="/build/venv/bin:${PATH}"

# Build the framework's own "Ref" reference deployment — a real,
# maintained F´ deployment (not something authored by this project) that
# ships inside the framework repo for its own testing/demonstration
# purposes. This is the real target artifact once confirmed working;
# see fprime-app/README.md.
WORKDIR /build/fprime-src/Ref

RUN fprime-util generate \
    && fprime-util build

# Build log + resulting binaries land in /output when run with
# `-v "$(pwd)/build-output:/output"` per fprime-app/README.md.
CMD ["/bin/bash", "-c", \
     "mkdir -p /output && \
      cp -r /build/fprime-src/Ref/build-artifacts /output/ 2>/dev/null; \
      echo 'Build artifacts copied to /output (see fprime-app/README.md)'"]
