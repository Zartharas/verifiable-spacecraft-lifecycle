# Reproducible build environment for the real NASA JPL F Prime (F´)
# target artifact — stack #2, Phase 6 (generalizability).
#
# NOT run/verified in the Claude sandbox that authored this file (no
# Docker there) — run and verify this on a Docker-capable machine, then
# update fprime-app/README.md and docs/Technical-Design-Document.md § 7f
# to mark it confirmed. Mirrors the same status as cfs-app/Dockerfile.
#
# Per the same source-handling policy as Legal-Data-Sourcing-Notes.md
# § 3a (there written for cFS, applied identically here): F´ source is
# never vendored into this repository. This Dockerfile clones it fresh
# at a pinned tag on every build, preserving upstream LICENSE/NOTICE
# files as distributed.
#
# Pinned reference (confirmed via github.com/nasa/fprime/releases,
# 2026-08-03):
#   Repository: https://github.com/nasa/fprime
#   Tag:        v4.2.2 (latest tagged release at time of pinning)
#   License:    Apache License 2.0, copyright California Institute of
#               Technology, "United States Government Sponsorship
#               acknowledged" (verified directly from the repo's
#               LICENSE.txt at the devel branch)
#
# If this tag is later superseded, re-pin deliberately and record the
# change in Legal-Data-Sourcing-Notes.md § 5 change log — don't silently
# float to `devel`.

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        cmake \
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

# F´ builds via its Python toolchain (fprime-tools/fprime-gds), not a
# bare cmake invocation — install into a venv, then generate and build
# the framework's own reference deployment ("Ref") as the target
# artifact once confirmed working. This mirrors cfs-app/Dockerfile's
# "standard build flow per upstream README" approach for cFS's
# sample_app.
RUN python3 -m venv /build/venv \
    && /build/venv/bin/pip install --upgrade pip \
    && /build/venv/bin/pip install -e .

WORKDIR /build/fprime-src/Ref

RUN /build/venv/bin/fprime-util generate \
    && /build/venv/bin/fprime-util build

# Build log + resulting binaries land in /output when run with
# `-v "$(pwd)/build-output:/output"` per fprime-app/README.md.
CMD ["/bin/bash", "-c", \
     "mkdir -p /output && \
      cp -r /build/fprime-src/Ref/build-artifacts /output/ 2>/dev/null; \
      echo 'Build artifacts copied to /output (see fprime-app/README.md)'"]
