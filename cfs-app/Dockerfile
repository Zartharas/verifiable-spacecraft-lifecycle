# Reproducible build environment for the real NASA cFS target artifact.
#
# NOT run/verified in the Claude sandbox that authored this file (no Docker
# there) — run and verify this on a Docker-capable machine, then update
# cfs-app/README.md and docs/Technical-Design-Document.md to mark it
# confirmed.
#
# Per Legal-Data-Sourcing-Notes.md § 3a: cFS source is never vendored into
# this repository. This Dockerfile clones it fresh at a pinned tag/commit
# on every build, preserving upstream LICENSE/NOTICE files as distributed.
#
# Pinned reference (confirmed via github.com/nasa/cFS/releases):
#   Repository: https://github.com/nasa/cFS
#   Tag:        v7.0.0  ("Draco" bundle release)
#   Commit:     b4ec679b2fd9d825610515ceb186cbfa80c60cfc
#   License:    Apache License 2.0 (NASA Docket No. GSC-19,200-1)
#
# If this tag is later superseded, re-pin deliberately and record the
# change in Legal-Data-Sourcing-Notes.md § 5 change log — don't silently
# float to `main`.

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        cmake \
        build-essential \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Pinned checkout — recursive for the cFS bundle's submodules (cFE, OSAL,
# PSP, sample_app, etc.), never copied/vendored into this repo.
RUN git clone --recursive https://github.com/nasa/cFS.git cfs-src \
    && cd cfs-src \
    && git checkout b4ec679b2fd9d825610515ceb186cbfa80c60cfc \
    && git submodule update --init --recursive

WORKDIR /build/cfs-src

# Standard cFS build flow (see upstream README for the authoritative
# instructions — this mirrors it for the sample_app target used as this
# project's real target artifact once confirmed working).
RUN cp -r cfe/cmake/sample_defs sample_defs \
    && mkdir -p build \
    && cd build \
    && cmake -DSIMULATION=native -DCMAKE_BUILD_TYPE=debug .. \
    && make mission-install

# Build log + resulting binaries land in /output when run with
# `-v "$(pwd)/build-output:/output"` per cfs-app/README.md.
CMD ["/bin/bash", "-c", \
     "mkdir -p /output && \
      cp -r /build/cfs-src/build/exe /output/ 2>/dev/null; \
      cp -r /build/cfs-src/build/*.log /output/ 2>/dev/null; \
      echo 'Build artifacts copied to /output (see cfs-app/README.md)'"]
