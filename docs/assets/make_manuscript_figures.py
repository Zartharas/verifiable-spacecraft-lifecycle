"""Generates the three manuscript figures into docs/assets/manuscript/.

Values are copied from evaluation/results/phase5_report.md, phase6_report_*.md,
phase5_summary.json, phase8_tuf_baseline.json, phase9_hash_baseline.json and phase11_uptane_spec_analysis.json.
Run from the repository root:  python3 docs/assets/make_manuscript_figures.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "manuscript"
OUT.mkdir(exist_ok=True)
RES = ROOT / "evaluation" / "results"

CONDS = ["S0", "S1", "S2", "S3", "S4", "S5"]


def fig1_pipeline():
    stages = [
        ("Source", ""), ("Reproducible\nbuild", ""), ("Provenance\ngeneration", "S2+"),
        ("SBOM\ngeneration", "S1+"), ("Signed\nrelease", "S0+"),
        ("Ground\nauthorization", "S0+ (policy: S5)"), ("Simulated\nuplink", ""),
        ("Onboard\nverification", "S0+ (policy: S5)"), ("Installation", "S4: A/B slots"),
        ("Boot/runtime\nattestation", "S3+"), ("Health\nvalidation", "S3+"),
        ("Rollback or\napproval", "S4+"), ("Authorization\nevidence", "S5"),
    ]
    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.set_xlim(0, 7.3)
    ax.set_ylim(0, 2.6)
    ax.axis("off")
    pos = []
    for i in range(7):
        pos.append((0.1 + i * 1.03, 1.55))
    for i in range(6):
        pos.append((0.1 + (6 - i) * 1.03 - 0.0, 0.3))
    colors = {"": "#e8eaed", "S0+": "#cfe8d5", "S1+": "#b7dfc4", "S2+": "#9fd5b3",
              "S3+": "#bcd2ee", "S4+": "#f4c7c3", "S4: A/B slots": "#f4c7c3", "S5": "#d9c7ee"}
    for (label, cond), (x, y) in zip(stages, pos):
        c = colors.get(cond.split(" (")[0], "#e8eaed")
        ax.add_patch(FancyBboxPatch((x, y), 0.92, 0.75, boxstyle="round,pad=0.02",
                                    fc=c, ec="#444", lw=0.8))
        ax.text(x + 0.46, y + 0.5, label, ha="center", va="center", fontsize=7.5)
        if cond:
            ax.text(x + 0.46, y + 0.14, cond, ha="center", va="center", fontsize=6,
                    color="#333", style="italic")
    for i in range(6):
        ax.annotate("", xy=(pos[i + 1][0], pos[i + 1][1] + 0.37),
                    xytext=(pos[i][0] + 0.92, pos[i][1] + 0.37),
                    arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.annotate("", xy=(pos[7][0] + 0.46, pos[7][1] + 0.75),
                xytext=(pos[6][0] + 0.46, pos[6][1]), arrowprops=dict(arrowstyle="->", lw=0.8))
    for i in range(7, 12):
        ax.annotate("", xy=(pos[i + 1][0] + 0.92, pos[i + 1][1] + 0.37),
                    xytext=(pos[i][0], pos[i][1] + 0.37), arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.text(3.65, 2.5, "Fig. 1. Twelve-stage update pipeline; text in italics gives the lowest "
            "condition at which a stage's check is active.", ha="center", fontsize=8)
    fig.savefig(OUT / "fig1_pipeline.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def fig2_cost():
    evidence = [7, 9, 12, 15, 17, 21]
    storage = [0, 613, 1264, 1631, 1624, 5747]
    times = {
        "cfs (stand-in)": [0.2277, 0.2373, 0.2529, 0.2715, 0.2948, 0.3281],
        "fprime (stand-in)": [0.2880, 0.2983, 0.2908, 0.3533, 0.3635, 0.5182],
        "cfs-real": [0.2872, 0.2671, 0.3049, 2.5118, 2.4831, 2.7743],
        "fprime-real": [0.3754, 0.3853, 0.4449, 2.0019, 1.9761, 2.3252],
    }
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.2))
    axs[0].bar(CONDS, evidence, color="#5b8def")
    axs[0].set_title("Evidence records per run", fontsize=9)
    axs[1].bar(CONDS, storage, color="#e0836b")
    axs[1].set_title("Added storage vs. S0 (bytes)", fontsize=9)
    for name, ys in times.items():
        axs[2].plot(CONDS, ys, marker="o", ms=3, label=name)
    axs[2].set_yscale("log")
    axs[2].set_title("Mean happy-path time (s, log scale)", fontsize=9)
    axs[2].legend(fontsize=6.5)
    for a in axs:
        a.tick_params(labelsize=8)
    fig.suptitle("Fig. 2. Measured cost of each added mechanism (30 trials per point). "
                 "Real-framework time steps at S3 reflect container launch (Section 8).",
                 fontsize=8, y=-0.02)
    fig.tight_layout()
    fig.savefig(OUT / "fig2_cost.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def fig3_coverage():
    tuf = json.loads((RES / "phase8_tuf_baseline.json").read_text())
    hsh = json.loads((RES / "phase9_hash_baseline.json").read_text())
    upt = json.loads((RES / "phase11_uptane_spec_analysis.json").read_text())["cases"]
    first = {"1": "S2", "2": "S2", "3": "S1", "4": "S1", "5": "S2", "6": "S0", "7": "S0",
             "8": "S5", "9": "S2", "10": "S4", "11": "S4", "12": "S4", "13": "S5",
             "14": "S4", "15": "S5"}
    label = {"native": "native", "partial_analogue": "partial", "stated_out_of_scope": "out of scope",
             "not_addressed": "not addressed"}
    level = {"native": 1.0, "partial_analogue": 0.5, "stated_out_of_scope": 0, "not_addressed": 0}
    cases = [str(i) for i in range(1, 16)]
    cols = ["Hash-only\n(run)", "TUF\n(run)", "Uptane\n(spec. read)", "S0-S5 ladder\n(run)"]
    grid = []
    for c in cases:
        h = hsh[c]
        t = tuf[c]
        grid.append([
            1 if (h["applicable"] and h["caught_count"] == h["n_trials"]) else 0,
            1 if (t["applicable"] and t["caught_count"] == t["n_trials"]) else 0,
            level[upt[c]["status"]],
            1,
        ])
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    ax.imshow(grid, cmap="Greens", vmin=0, vmax=1.4, aspect="auto")
    ax.set_xticks(range(4), cols, fontsize=8)
    ax.set_yticks(range(15), [f"#{c}" for c in cases], fontsize=8)
    ax.xaxis.tick_top()
    for i, c in enumerate(cases):
        for j in range(4):
            if j == 3:
                txt = f"{first[c]}"
            elif j == 2:
                txt = label[upt[c]["status"]]
            else:
                txt = "caught" if grid[i][j] else "not covered"
            ax.text(j, i, txt, ha="center", va="center", fontsize=6.5)
    fig.text(0.5, 0.0, "Fig. 3. Attack-matrix cases covered by each approach. Uptane is classified from the\nstandard's text, not run. Ladder column: first condition at which the case is detected.", ha="center", fontsize=7.5)
    fig.savefig(OUT / "fig3_coverage.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig1_pipeline()
    fig2_cost()
    fig3_coverage()
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
