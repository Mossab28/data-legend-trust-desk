"""Generate docs/architecture.png — Facility Trust Desk system architecture.

On-brand (matches the app's dark theme). Reproducible: `python docs/make_architecture.py`.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

BG = "#0D1117"; CARD = "#161B22"; BORDER = "#30363D"
TEXT = "#E6EDF3"; MUTED = "#9DA7B3"; ACCENT = "#2F81F7"
GREEN = "#3FB950"; AMBER = "#D29922"; PURPLE = "#BC8CFF"

fig, ax = plt.subplots(figsize=(16, 10.5), dpi=150)
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
ax.set_xlim(0, 16); ax.set_ylim(0, 10.5); ax.axis("off")


def box(x, y, w, h, title, sub="", tc=TEXT, edge=BORDER, face=CARD,
        title_size=12.5, sub_size=10, lw=1.4, bold=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.10",
                                linewidth=lw, edgecolor=edge, facecolor=face))
    if sub:
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
                color=tc, fontsize=title_size, fontweight="bold" if bold else "normal")
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center",
                color=MUTED, fontsize=sub_size, wrap=True)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                color=tc, fontsize=title_size, fontweight="bold" if bold else "normal")


def arrow(x1, y1, x2, y2, color=ACCENT, lw=1.8, style="-|>"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 mutation_scale=16, color=color, lw=lw,
                                 shrinkA=2, shrinkB=2))


def label(x, y, txt, color=MUTED, size=10, ha="left", weight="normal", style="normal"):
    ax.text(x, y, txt, ha=ha, va="center", color=color, fontsize=size,
            fontweight=weight, fontstyle=style)


# ---- title -----------------------------------------------------------------
ax.text(0.35, 10.15, "Facility Trust Desk — Architecture", color=TEXT,
        fontsize=20, fontweight="bold")
ax.text(0.37, 9.75, "Every capability claim is treated as noisy evidence, not fact. "
        "100% on Databricks.", color=MUTED, fontsize=11.5)

# ---- 1. Sources ------------------------------------------------------------
label(0.35, 9.28, "DATA SOURCES", color=ACCENT, size=10.5, weight="bold")
box(0.35, 8.15, 4.5, 1.0, "Virtue Foundation facilities",
    "~10,088 records · Delta Share (read-only)")
box(5.15, 8.15, 3.3, 1.0, "India Post", "PIN-code directory → state/district")
box(8.75, 8.15, 3.4, 1.0, "NFHS-5", "official district health survey")

# ---- 2. Trust Engine -------------------------------------------------------
ax.add_patch(FancyBboxPatch((0.35, 4.35), 11.8, 3.25,
             boxstyle="round,pad=0.02,rounding_size=0.10",
             linewidth=1.8, edgecolor=ACCENT, facecolor="#0E1726"))
label(0.65, 7.32, "TRUST ENGINE", color=ACCENT, size=10.5, weight="bold")
label(2.55, 7.32, "pure SQL on a Databricks SQL Warehouse · replayable (CREATE OR REPLACE)",
      color=MUTED, size=10)

# transforms row
tw, th, ty = 2.16, 0.92, 5.95
trans = [
    ("Scoring v2", "independence buckets ·\nnegation · Wilson band", GREEN),
    ("Self-validation", "audits its own\nscores", AMBER),
    ("Forensics", "geo mismatch ·\ndigitally silent", AMBER),
    ("Geo + deserts", "PIN + NFHS-5\njoin", TEXT),
    ("Semantic index", "profile embeddings\nper facility", PURPLE),
]
for i, (t, s, c) in enumerate(trans):
    x = 0.62 + i * (tw + 0.12)
    box(x, ty, tw, th, t, s, tc=c, title_size=11, sub_size=8.5, face=CARD)

# output tables row
label(0.65, 5.55, "DELTA TABLES & FUNCTIONS", color=MUTED, size=9.5, weight="bold")
outs = [
    "facility_trust\n+ trust_score_low/high",
    "trust_validations\ndisagrees_with_score",
    "trust_anomalies",
    "facility_geo /\ndistrict_coverage",
    "facility_semantic +\nsemantic_facilities()",
]
ow, oh, oy = 2.16, 0.82, 4.55
for i, t in enumerate(outs):
    x = 0.62 + i * (ow + 0.12)
    name, _, sub = t.partition("\n")
    box(x, oy, ow, oh, name, sub, title_size=10, sub_size=8, face="#12181F")
    arrow(x + ow / 2, ty, x + ow / 2, oy + oh, color=BORDER, lw=1.2)

# ---- side callouts ---------------------------------------------------------
box(12.4, 6.55, 3.25, 1.05, "Foundation model",
    "databricks-gte-large-en\nai_query() embeddings", tc=PURPLE, edge=PURPLE)
arrow(12.4, 7.05, 11.55, 6.55, color=PURPLE, lw=1.6)   # → semantic index chip
box(12.4, 5.25, 3.25, 1.05, "MLflow 3 tracing",
    "experiment: trust-engine\nextract→score→rank→validate", tc=PURPLE, edge=PURPLE)
arrow(12.4, 5.78, 12.15, 5.9, color=PURPLE, lw=1.6)

# sources -> engine
arrow(2.6, 8.15, 2.6, 7.62, color=ACCENT)
arrow(6.8, 8.15, 6.8, 7.62, color=ACCENT)
arrow(10.4, 8.15, 10.4, 7.62, color=ACCENT)

# ---- 3. State / persistence ------------------------------------------------
label(0.35, 4.05, "STATE (read/write from the app)", color=ACCENT, size=10.5, weight="bold")
box(0.35, 2.95, 4.7, 0.95, "Lakebase · Postgres OLTP",
    "planner_actions — overrides · notes · shortlist", tc=GREEN, edge=GREEN)
box(5.3, 2.95, 3.4, 0.95, "Delta fallback",
    "when Lakebase is off-network", tc=AMBER)
box(8.95, 2.95, 3.2, 0.95, "app_roles",
    "RBAC: viewer/planner/admin", tc=TEXT)

# ---- 4. App ----------------------------------------------------------------
ax.add_patch(FancyBboxPatch((0.35, 0.35), 15.3, 2.15,
             boxstyle="round,pad=0.02,rounding_size=0.10",
             linewidth=1.8, edgecolor=GREEN, facecolor="#0E1A12"))
label(0.65, 2.22, "DATABRICKS APP · Streamlit", color=GREEN, size=11, weight="bold")
label(4.7, 2.22, "identity from Databricks SSO (X-Forwarded-Email) — never a text box · "
      "deep-links: Genie (NL query) · MLflow trace", color=MUTED, size=9.5)
tabs = [
    ("Find facilities", "citations · confidence\nbands · validator · search"),
    ("Medical deserts", "data desert ≠\nmedical desert"),
    ("Data quality", "ratings we\noverturned ourselves"),
    ("Shortlist & decisions", "export Decision\nBrief (.md)"),
]
tw2 = 3.6
for i, (t, s) in enumerate(tabs):
    x = 0.62 + i * (tw2 + 0.18)
    box(x, 0.6, tw2, 1.25, t, s, title_size=11.5, sub_size=9, face=CARD)

# engine/state -> app
arrow(6.0, 4.35, 6.0, 3.9, color=GREEN, lw=1.6)      # engine tables -> state
arrow(3.0, 2.95, 3.0, 2.5, color=GREEN, lw=1.6)      # state -> app
arrow(9.0, 4.35, 9.0, 2.5, color=GREEN, lw=1.6, style="<|-|>")  # app reads tables directly

plt.savefig("docs/architecture.png", facecolor=BG, bbox_inches="tight", pad_inches=0.25)
print("wrote docs/architecture.png")
