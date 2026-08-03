/*
 * stub-telemetry-app — Phase 1 stand-in target artifact.
 *
 * NOT NASA cFS. This is a deliberately trivial program that stands in for
 * a cFS sample telemetry app so the Phase 1 supply-chain pipeline
 * (build -> sign -> ground auth -> uplink -> onboard verify -> install)
 * can be built and tested end-to-end without Docker/cmake/root access.
 *
 * See cfs-app/README.md for how to swap in the real cFS build.
 *
 * Deterministic by construction: no timestamps, no random values, no
 * uninitialized memory read, no build-path strings embedded — so that
 * two builds from the same source, same toolchain, produce a bit-
 * identical binary (the reproducible-build property under test).
 */
#include <stdio.h>

int telemetry_report(int channel) {
    return channel * 2 + 1;
}

int main(void) {
    for (int channel = 0; channel < 4; channel++) {
        printf("channel=%d value=%d\n", channel, telemetry_report(channel));
    }
    return 0;
}
