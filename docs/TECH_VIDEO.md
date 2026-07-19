# Tech Video (≤ 60 s) — script & screen plan

Goal (per brief): **technical explanation — stack, architecture, implementation.**
Screen recording + webcam (picture-in-picture). Diagram to show: `docs/architecture.png`.

Kept simple: **one script, two screens** — but with one moment of real depth.

---

## Script (spoken, English) — ~150 words ≈ 58–62 s

Calm pace. The **bold** phrases are the technical hooks — hit them. The middle
paragraph is the point; don't rush it.

> **Facility Trust Desk runs entirely on Databricks. We treat every capability a
> hospital claims as evidence to verify — not fact.**
>
> Read-only data — Virtue Foundation, India Post, and the NFHS-5 health survey —
> flows into a **Trust Engine: pure, replayable SQL on a Databricks SQL Warehouse.**
>
> The core idea: **corroboration counts only independent sources.** The same sentence
> copied across fields counts once — so a facility can't inflate its own trust by
> repeating itself. A claim is corroborated only when structured **procedures or
> equipment** back the narrative. And since there's **no ground truth**, each score
> carries a **Wilson confidence band** — that's how we separate solid from speculative.
>
> On top of that: the engine **validates its own scores**, the whole pipeline is
> **traced in MLflow**, free-text search **embeds every facility via `ai_query`**, and
> state lives in **Lakebase Postgres** with a Delta fallback.
>
> The app is **Streamlit with SSO** — every rating **cites the exact sentence** behind
> it, and flags when **our own validator disagrees.**

---

## Screen plan — 2 scenes only

| Time | Show on screen | Say |
|---|---|---|
| 0 – 30 s | **`architecture.png`, full screen.** Move the cursor down the 3 layers (data → engine → app) as you name them. | Intro + data + the "core idea" paragraph |
| 30 – 60 s | **One facility card, expanded** — the verbatim citations, the confidence band, and the red **"Our own validator disagrees"** banner. | The "on top of that" + app paragraphs |

The card **literally illustrates** the core-idea line you just said — citations =
independent sources, the band = solid vs speculative, the red banner = self-validation.
No tab-hopping, no live search — two clean shots.

---

## Record it (macOS)

- **OBS Studio** (free): *Display Capture* + a small *webcam* bubble in a corner → one take.
  Or **QuickTime** screen recording + a separate webcam clip.
- Warm the app up first (open the facility card you'll use). Do **2–3 takes** — 60 s is short.
- Pick the facility card in advance (ideally one where the validator disagrees).
- Land the final line — *"cites the exact sentence… our own validator disagrees"* —
  looking at the camera.
