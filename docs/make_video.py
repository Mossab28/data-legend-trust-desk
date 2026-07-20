#!/usr/bin/env python3
"""Montage 60s : assemblage progressif de l'architecture Facility Trust Desk.

Chaque bloc est rendu comme un calque transparent (memes coords/style que
docs/architecture.png) puis pose a l'ecran en slide + fondu, dans l'ordre
narratif : donnees brutes -> Trust Engine -> app Streamlit.

Usage:
  python docs/make_video.py                     # video muette ~62s
  python docs/make_video.py --audio voix.mp3    # colle la voix et cale la duree
  python docs/make_video.py --audio voix.mp3 --out docs/tech_final.mp4
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from PIL import Image

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import (
    ImageClip,
    ColorClip,
    CompositeVideoClip,
    concatenate_videoclips,
    AudioFileClip,
)

# ---- palette (identique au diagramme) --------------------------------------
BG = "#0D1117"; CARD = "#161B22"; BORDER = "#30363D"
TEXT = "#E6EDF3"; MUTED = "#9DA7B3"; ACCENT = "#2F81F7"; GREEN = "#3FB950"
BG_RGB = (13, 17, 23)

# ---- canvas -----------------------------------------------------------------
W, H = 1920, 1080
DPI = 120                     # 16*120 x 9*120 = 1920x1080
PX_PER_UNIT = 120             # 1 unite data = 120 px
XLIM = (-1.5, 14.5)           # span 16
YLIM = (-0.5, 8.5)            # span 9  -> aspect 16:9 sans distorsion
TOTAL = 62.0
LAYER_DIR = "docs/_layers"


def new_fig():
    fig = plt.figure(figsize=(16, 9), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(*XLIM); ax.set_ylim(*YLIM); ax.axis("off")
    fig.patch.set_alpha(0)
    return fig, ax


def box(ax, x, y, w, h, title, sub="", tc=TEXT, edge=BORDER, face=CARD,
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


def arrow(ax, x1, y1, x2, y2, color=ACCENT, lw=2.2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                 mutation_scale=22, color=color, lw=lw, shrinkA=3, shrinkB=3))


# ---- calques (fonction de dessin) ------------------------------------------
def d_title(ax):
    ax.text(6.5, 7.6, "Facility Trust Desk", color=TEXT, fontsize=24,
            fontweight="bold", ha="center")


def d_subtitle(ax):
    ax.text(6.5, 7.12,
            "Every capability claim is treated as evidence, not fact - 100% on Databricks",
            color=MUTED, fontsize=12.5, ha="center")


def d_sources(ax):
    box(ax, 1.5, 5.75, 10, 0.95, "Read-only data",
        "Virtue Foundation facilities  \u00b7  India Post  \u00b7  NFHS-5 health survey",
        ts=15, ss=12)


def d_arrow1(ax):
    arrow(ax, 6.5, 5.75, 6.5, 5.25)


def d_engine(ax):
    box(ax, 1.5, 2.55, 10, 2.7, "", face="#0E1726", edge=ACCENT, lw=2)
    ax.text(6.5, 4.85, "Trust Engine", color=ACCENT, fontsize=18,
            fontweight="bold", ha="center")
    ax.text(6.5, 4.45, "pure, replayable SQL on a Databricks SQL Warehouse",
            color=MUTED, fontsize=12, ha="center")


PTS = [
    "Trust score + confidence band",
    "Self-validation (audits itself)",
    "Semantic search (ai_query)",
    "Traced in MLflow",
]


def make_bullet(i):
    def draw(ax):
        col = 1.95 + (i % 2) * 5.2
        row = 3.75 - (i // 2) * 0.62
        ax.text(col, row, "\u25cf", color=GREEN, fontsize=11, va="center")
        ax.text(col + 0.32, row, PTS[i], color=TEXT, fontsize=13, va="center")
    return draw


def d_lakebase(ax):
    ax.text(6.5, 2.78, "State \u2192 Lakebase (Postgres) with Delta fallback",
            color=MUTED, fontsize=11, ha="center", fontstyle="italic")


def d_arrow2(ax):
    arrow(ax, 6.5, 2.55, 6.5, 2.05)


def d_app(ax):
    box(ax, 1.5, 0.85, 10, 1.2, "Databricks App \u00b7 Streamlit + SSO",
        "every claim cites the exact sentence behind it",
        tc=GREEN, edge=GREEN, face="#0E1A12", ts=16, ss=12.5)


# name, draw_fn, t0 (apparition), slide_dy (unites data, +bas), fade, slide_dur
LAYERS = [
    ("title",    d_title,        0.4,  -0.20, 0.7, 0.7),
    ("subtitle", d_subtitle,     1.1,  -0.15, 0.7, 0.7),
    ("sources",  d_sources,      8.5,   0.35, 0.6, 0.7),
    ("arrow1",   d_arrow1,      15.5,   0.00, 0.5, 0.0),
    ("engine",   d_engine,      16.5,   0.35, 0.6, 0.8),
    ("bullet0",  make_bullet(0),33.0,   0.18, 0.5, 0.5),
    ("bullet1",  make_bullet(1),36.5,   0.18, 0.5, 0.5),
    ("bullet2",  make_bullet(2),40.0,   0.18, 0.5, 0.5),
    ("bullet3",  make_bullet(3),43.5,   0.18, 0.5, 0.5),
    ("lakebase", d_lakebase,    46.5,   0.12, 0.5, 0.5),
    ("arrow2",   d_arrow2,      48.5,   0.00, 0.5, 0.0),
    ("app",      d_app,         49.5,   0.35, 0.6, 0.8),
]


def render_layers():
    os.makedirs(LAYER_DIR, exist_ok=True)
    paths = {}
    for name, fn, *_ in LAYERS:
        fig, ax = new_fig()
        fn(ax)
        p = os.path.join(LAYER_DIR, f"{name}.png")
        fig.savefig(p, transparent=True)
        plt.close(fig)
        paths[name] = p
    return paths


def ease_out(u):
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) ** 3


def slide_pos(dy_units, dur):
    dy = dy_units * PX_PER_UNIT

    def pos(t):
        return (0, dy * (1 - ease_out(t / dur))) if dur > 0 else (0, 0)
    return pos


def build_video(target=TOTAL):
    # cale la timeline d'assemblage sur la duree cible (ta voix) en gardant
    # les proportions du plan de reference (TOTAL). Les transitions courtes
    # (fondu / glisse) ne sont pas etirees pour rester nettes.
    k = target / TOTAL
    paths = render_layers()
    clips = [ColorClip((W, H), color=BG_RGB).set_duration(target)]
    for name, _fn, t0, dy, fade, sdur in LAYERS:
        start = min(t0 * k, target - 0.1)
        clip = (ImageClip(paths[name])
                .set_start(start)
                .set_duration(target - start)
                .crossfadein(fade))
        if dy and sdur:
            clip = clip.set_position(slide_pos(dy, sdur))
        clips.append(clip)
    video = CompositeVideoClip(clips, size=(W, H)).set_duration(target)
    return video.fadein(0.4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", default=None)
    ap.add_argument("--out", default="docs/architecture_video.mp4")
    args = ap.parse_args()

    if args.audio:
        audio = AudioFileClip(args.audio)
        video = build_video(target=audio.duration).set_audio(audio)
    else:
        video = build_video()

    video.write_videofile(
        args.out, fps=30, codec="libx264", audio_codec="aac",
        preset="medium", threads=4,
    )
    print("OK ->", args.out, "| duree ~", round(video.duration, 1), "s")


if __name__ == "__main__":
    main()
