# Tech Video (≤ 60 s) — script, screen cues & recording guide

Goal (per brief): **technical explanation — cover your stack, architecture, and
implementation.** Screen recording + webcam (picture-in-picture) commentary.

Architecture diagram to show: `docs/architecture.png` (regenerate with
`python docs/make_architecture.py`).

---

## The 60-second script (spoken, English)

~150 words ≈ 58–62 s at a calm pace. **Don't rush** — if you're tight, drop the
sentences marked *(cut-ok)*.

> **Facility Trust Desk runs entirely on Databricks. Every capability an Indian
> hospital claims, we treat as noisy evidence — not fact.**
>
> The stack is three layers. Read-only sources — the Virtue Foundation facilities
> share, India Post, and the NFHS-5 health survey — feed a **Trust Engine written
> as pure, replayable SQL on a Databricks SQL Warehouse.** It outputs Delta tables:
> a trust score with a **Wilson confidence band**, an **independent self-validation**
> pass, forensic anomaly flags, and district-level desert analysis.
>
> Three things make it defensible. **Corroboration counts only independent sources,**
> so copied text can't inflate a score. *(cut-ok)* Free-text search **embeds every
> facility with a foundation model through `ai_query`** — no vector endpoint needed.
> And the **whole pipeline is traced in MLflow.** State lives in **Lakebase Postgres,
> with a Delta fallback.**
>
> On top: a **Streamlit Databricks App with single sign-on**, where every claim
> cites the exact sentence behind it.

---

## Screen + camera timeline

| Time | Say (from script) | Show on screen | Camera |
|---|---|---|---|
| 0–8 s | "runs entirely on Databricks … noisy evidence, not fact" | **App header** — title, tagline, headline band (10,088 facilities · corroborated · "N times a human corrected this app") | Big smile, look at camera |
| 8–30 s | "three layers … Trust Engine … Delta tables … Wilson band …" | **`architecture.png` full-screen.** Move cursor top→bottom as you name each layer (sources → engine → state → app) | Glance at cam on key words |
| 30–38 s | "counts only independent sources … copied text can't inflate" | **A facility card, expanded** — the verbatim citations with field tags (equipment / procedure), the confidence band, and the red **"Our own validator disagrees"** banner | — |
| 38–46 s | "embeds every facility … `ai_query` … no vector endpoint" | Type **"burns unit"** in the free-text search box → semantic results with trust chips | — |
| 46–53 s | "whole pipeline is traced in MLflow" | Click **"How was this computed?"** (sidebar) → the **MLflow trace tree** (extract→score→rank→validate spans) | Point at the spans |
| 53–60 s | "Streamlit app with SSO … cites the exact sentence" | Back to app — sidebar **"Signed in as … Role"**, then a citation quote | Look at camera, land the line |

Keep transitions snappy; the architecture diagram is the anchor (biggest slice).

---

## Setup checklist (before you hit record)

- [ ] App already open and **logged in** (so the sidebar shows your email + role).
- [ ] Pre-run each click once so tables are warm (semantic search first call is ~2–3 s).
- [ ] Open `docs/architecture.png` in Preview, full-screen, ready to alt-tab to.
- [ ] Pre-load the MLflow trace URL in a tab (sidebar "How was this computed?").
- [ ] Browser at **1920×1080**, zoom 100–110 %, hide bookmarks bar, close noisy tabs.
- [ ] Pick **one** striking facility card in advance (ideally one where the validator
      disagrees with the score) — don't hunt for it live.
- [ ] Quiet room, mic close, webcam at eye level, light in front of you.

## Recording it on macOS

- Simplest: **QuickTime → File → New Screen Recording** for the screen, and record
  your webcam separately, or use the built-in **Cmd-Shift-5** toolbar.
- For real picture-in-picture (screen + webcam bubble in one take): use **OBS
  Studio** (free) — add a *Display Capture* source + a *Video Capture Device*
  (webcam) sized small in a corner. One export, done.
- Record a few seconds of silence first; trim later. Do **2–3 takes** — 60 s is short,
  the third is always the best.

## Delivery tips

- Say the **product name once**, early. Then it's all substance.
- Emphasize the **bolded phrases** — those are the technical hooks the judges score.
- It's a *technical* video: it's fine to sound like an engineer, not a marketer.
- End on the citation line — "every claim cites the exact sentence" — that's the
  whole thesis in six words.
