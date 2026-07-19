# Tech Video (≤ 45 s) — script & screen plan

Goal (per brief): **technical explanation — stack, architecture, implementation.**
Screen recording + webcam (picture-in-picture). Diagram to show: `docs/architecture.png`.

Kept deliberately simple: **one script, two screens.**

---

## Script (spoken, English) — ~105 words ≈ 45 s

Calm pace. The **bold** phrases are the technical hooks — hit them.

> **Facility Trust Desk runs entirely on Databricks.** We treat every capability a
> hospital claims as evidence to verify — **not fact.**
>
> Three layers. Read-only data — Virtue Foundation, India Post, NFHS-5 — flows into a
> **Trust Engine: pure, replayable SQL on a Databricks SQL Warehouse.** It scores every
> claim with a **confidence band**, **validates its own scores**, and the whole pipeline
> is **traced in MLflow.** Free-text search **embeds each facility with a foundation
> model via `ai_query`** — no vector endpoint. State lives in **Lakebase Postgres**, with
> a Delta fallback.
>
> On top, a **Streamlit app with SSO** — every rating **cites the exact sentence** behind
> it, and flags when **our own validator disagrees.**

---

## Screen plan — 2 scenes only

| Time | Show on screen | Say |
|---|---|---|
| 0 – 28 s | **`architecture.png`, full screen.** Move the cursor down the 3 layers (data → engine → app) as you name them. | Intro + the middle paragraph |
| 28 – 45 s | **One facility card, expanded** — the verbatim citations, the confidence band, and the red **"Our own validator disagrees"** banner. | The last paragraph |

That's it. No tab-hopping, no live search — two clean shots.

---

## Record it (macOS)

- **OBS Studio** (free): *Display Capture* + a small *webcam* bubble in a corner → one take.
  Or **QuickTime** screen recording + a separate webcam clip.
- Warm the app up first (open the facility card you'll use). Do **2–3 takes** — 45 s is short.
- Pick the facility card in advance (ideally one where the validator disagrees).
- Land the final line — *"cites the exact sentence… our own validator disagrees"* —
  looking at the camera.
