"""Generate docs/architecture.png — Facility Trust Desk, simple 3-layer view.

Built to be read in ~5 seconds on screen. Reproducible:
    python docs/make_architecture.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

BG = "#0D1117"; CARD = "#161B22"; BORDER = "#30363D"
TEXT = "#E6EDF3"; MUTED = "#9DA7B3"; ACCENT = "#2F81F7"; GREEN = "#3FB950"

fig, ax = plt.subplots(figsize=(13, 8), dpi=150)
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
ax.set_xlim(0, 13); ax.set_ylim(0, 8); ax.axis("off")


def box(x, y, w, h, title, sub="", tc=TEXT, edge=BORDER, face=CARD,
        ts=17, ss=12, lw=1.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=0.02,rounding_size=0.12",
                 linewidth=lw, edgecolor=edge, facecolor=face))
    if sub:
        ax.text(x + w / 2, y + h * 0.63, title, ha="center", va="center",
                color=tc, fontsize=ts, fontweight="bold")
        ax.text(x + w / 2, y + h * 0.27, sub, ha="center", va="center",
                color=MUTED, fontsize=ss)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                color=tc, fontsize=ts, fontweight="bold")


def arrow(x1, y1, x2, y2, color=ACCENT, lw=2.2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                 mutation_scale=22, color=color, lw=lw, shrinkA=3, shrinkB=3))


# ---- title -----------------------------------------------------------------
ax.text(6.5, 7.6, "Facility Trust Desk", color=TEXT, fontsize=24,
        fontweight="bold", ha="center")
ax.text(6.5, 7.12, "Every capability claim is treated as evidence, not fact — 100% on Databricks",
        color=MUTED, fontsize=12.5, ha="center")

# ---- 1. Sources ------------------------------------------------------------
box(1.5, 5.75, 10, 0.95, "Read-only data",
    "Virtue Foundation facilities  ·  India Post  ·  NFHS-5 health survey",
    ts=15, ss=12)
arrow(6.5, 5.75, 6.5, 5.25)

# ---- 2. Trust Engine -------------------------------------------------------
box(1.5, 2.55, 10, 2.7, "", face="#0E1726", edge=ACCENT, lw=2)
ax.text(6.5, 4.85, "Trust Engine", color=ACCENT, fontsize=18, fontweight="bold",
        ha="center")
ax.text(6.5, 4.45, "pure, replayable SQL on a Databricks SQL Warehouse",
        color=MUTED, fontsize=12, ha="center")
pts = [
    "Trust score + confidence band",
    "Self-validation (audits itself)",
    "Semantic search (ai_query)",
    "Traced in MLflow",
]
for i, p in enumerate(pts):
    col = 1.95 + (i % 2) * 5.2
    row = 3.75 - (i // 2) * 0.62
    ax.text(col, row, "\u25cf", color=GREEN, fontsize=11, va="center")
    ax.text(col + 0.32, row, p, color=TEXT, fontsize=13, va="center")
ax.text(6.5, 2.78, "State \u2192 Lakebase (Postgres) with Delta fallback",
        color=MUTED, fontsize=11, ha="center", fontstyle="italic")
arrow(6.5, 2.55, 6.5, 2.05)

# ---- 3. App ----------------------------------------------------------------
box(1.5, 0.85, 10, 1.2, "Databricks App \u00b7 Streamlit + SSO",
    "every claim cites the exact sentence behind it",
    tc=GREEN, edge=GREEN, face="#0E1A12", ts=16, ss=12.5)

plt.savefig("docs/architecture.png", facecolor=BG, bbox_inches="tight", pad_inches=0.3)
print("wrote docs/architecture.png")
