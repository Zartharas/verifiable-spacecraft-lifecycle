"""Graphical abstract for the revised manuscript (Revision 1).

Writes Graphical-Abstract.pdf and Graphical-Abstract.tiff (300 dpi, 13.28 x 5.31 in,
3x the Elsevier minimum of 531 x 1328 px) to the directory given as argv[1]
(default: docs/assets/manuscript).
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "manuscript"
out.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(13.28, 5.31))
ax.set_xlim(0, 100)
ax.set_ylim(0, 40)
ax.axis("off")

ax.text(50, 38, "Measuring Software Supply-Chain Assurance for Spacecraft Flight Software",
        ha="center", fontsize=15, fontweight="bold", color="#14213d")
ax.text(50, 35.2, "Controlled evaluation of an additive S0-S5 assurance ladder on four target software stacks",
        ha="center", fontsize=10, style="italic", color="#333")

levels = [("S0", "Signature\nonly", "#e4e4e4"), ("S1", "+SBOM", "#eef2f8"),
          ("S2", "+Build\nprovenance", "#eef2f8"), ("S3", "+Onboard\nattestation", "#eef2f8"),
          ("S4", "+Trusted\nrollback", "#eef2f8"), ("S5", "+Authorization\nevidence", "#eef2f8")]
x0, w, gap = 4, 13.5, 2.4
for i, (tag, txt, col) in enumerate(levels):
    x = x0 + i * (w + gap)
    ax.add_patch(FancyBboxPatch((x, 22), w, 9, boxstyle="round,pad=0.3", fc=col, ec="#4a6fa5", lw=1.2))
    ax.text(x + w / 2, 28, tag, ha="center", fontsize=13, fontweight="bold", color="#14213d")
    ax.text(x + w / 2, 24.4, txt, ha="center", fontsize=9.5, color="#14213d")
    if i < 5:
        ax.annotate("", xy=(x + w + gap - 0.2, 26.5), xytext=(x + w + 0.2, 26.5),
                    arrowprops=dict(arrowstyle="->", color="#555", lw=1.2))

ax.text(50, 20.2, "One codebase, six configurations: any difference between adjacent levels is attributable to one added mechanism",
        ha="center", fontsize=9, color="#333")

boxes = [
    ("Detection by mechanism", "100% active, 0% ablated\n15 injected cases, 4 stacks\n30 trials each",
     "#e8f4ee", "#1b7f5c"),
    ("Mutation testing", "~2,100 document variants,\n2 defects found and fixed;\nunread fields identified",
     "#fdf3e1", "#a86a00"),
    ("Cost of full ladder over S0", "+44% / +80% pipeline time\n(two stand-ins)\n3x evidence records, +5.7 kB",
     "#eef2f8", "#2a5d9f"),
    ("Baseline coverage", "Hash-only 1 of 15, TUF 3 of 15\nUptane (read, not run): 3 native,\n4 partial; the rest out of scope",
     "#fbeeee", "#b03030"),
]
bw = 21.5
for i, (head, body, fc, ec) in enumerate(boxes):
    x = 3 + i * (bw + 3.0)
    ax.add_patch(FancyBboxPatch((x, 3), bw, 13, boxstyle="round,pad=0.3", fc=fc, ec=ec, lw=1.2))
    ax.text(x + bw / 2, 13, head, ha="center", fontsize=10.5, fontweight="bold", color=ec)
    ax.text(x + bw / 2, 8, body, ha="center", va="center", fontsize=9, color="#222")

ax.text(50, 0.6, "Simulation-based: verifies the implemented checks and measures their cost; no flight hardware, no hardware root of trust",
        ha="center", fontsize=8.5, color="#555")

fig.savefig(out / "Graphical-Abstract.pdf", bbox_inches="tight")
fig.savefig(out / "Graphical-Abstract.tiff", dpi=300, bbox_inches="tight",
            pil_kwargs={"compression": "tiff_lzw"})
print("wrote", out)
