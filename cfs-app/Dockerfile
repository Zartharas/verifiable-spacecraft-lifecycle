# Reproducible build environment for the real NASA cFS target artifact.
#
# CORRECTED after a real failed build attempt (2026-08-03): the original
# version of this file assumed a bare `cmake .. && make mission-install`
# invocation from a `build/` subdirectory would work. It does not — the
# cFS BUNDLE repo's top-level build system is Make-based
# (`make native_std.prep` / `make native_std.install`, which invoke cmake
# internally with the correct source directory and generated build tree),
# not a directly-invokable bare cmake project. Confirmed against the
# authoritative build instructions in github.com/nasa/cFS's own README
# ("Build and Run Quick Start" section) after the first attempt failed
# with "CMake Error: The source directory /build/cfs-src does not appear
# to contain CMakeLists.txt." Also re-pinned from v7.0.0 to v7.0.1 (the
# actual current official release per that README) while fixing this.
#
# Per Legal-Data-Sourcing-Notes.md § 3a: cFS source is never vendored into
# this repository. This Dockerfile clones it fresh at a pinned tag on
# every build, preserving upstream LICENSE/NOTICE files as distributed.
#
# Pinned reference (confirmed via github.com/nasa/cFS's README, 2026-08-03):
#   Repository: https://github.com/nasa/cFS
#   Tag:        v7.0.1 ("OFFICIAL RELEASE" per the repo's own README)
#   License:    Apache License 2.0
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
RUN git clone --recursive --branch v7.0.1 https://github.com/nasa/cFS.git cfs-src

WORKDIR /build/cfs-src

# Official build flow per the repo's own README ("Build and Run Quick
# Start"): the Makefile wraps cmake and stages the compiled software to
# build-native_std/exe/cpu1/ for the "native_std" (local-machine,
# pc-linux PSP) configuration — the one that runs on a bare Docker
# container without special hardware/cross-toolchain requirements.
RUN make native_std.prep
RUN make native_std.install

# Build log + resulting binaries land in /output when run with
# `-v "$(pwd)/build-output:/output"` per cfs-app/README.md.
CMD ["/bin/bash", "-c", \
     "mkdir -p /output && \
      cp -r /build/cfs-src/build-native_std/exe /output/ 2>/dev/null; \
      echo 'Build artifacts copied to /output (see cfs-app/README.md)'"]
