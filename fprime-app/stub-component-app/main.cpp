/*
 * stub-component-app — Phase 6 stand-in target artifact #2.
 *
 * NOT F Prime (F´). This is a deliberately trivial C++ program that stands
 * in for an F´ component's telemetry-producing role, so the assurance
 * ladder (S0-S5) and the pipeline built against stack #1
 * (cfs-app/stub-telemetry-app, a C program) can be re-run against a
 * second, architecturally distinct stand-in — different language (C++
 * vs. C), different deterministic output shape (dotted telemetry-channel
 * naming vs. "channel=N value=M") — without Docker/cmake/root access.
 *
 * See fprime-app/README.md for how to swap in the real F´ framework, and
 * Threat-Model.md "Phase 6 results" for what generalization was actually
 * tested and found by re-running the pipeline against this stack.
 *
 * Deterministic by construction, same rationale as
 * cfs-app/stub-telemetry-app/main.c: no timestamps, no random values, no
 * uninitialized memory, no build-path strings embedded — so two builds
 * from the same source, same toolchain, produce a bit-identical binary.
 */
#include <cstdio>

namespace {

int telemetry_value(int channel) {
    return channel * 3 + 2;
}

}  // namespace

int main() {
    for (int channel = 0; channel < 4; channel++) {
        std::printf("telemetry.chan%d=%d\n", channel, telemetry_value(channel));
    }
    return 0;
}
