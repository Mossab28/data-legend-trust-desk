# Integration guide — workstream A → app (for Mossab)

Everything workstream A shipped, and exactly how to wire it into the app. All
interfaces are frozen in `docs/CONTRACT.md`; this doc is the "how to plug it in".

Branches to merge (stacked, in this order): `feat/a-scoring-v2` → `feat/a-validator`
→ `feat/a-uncertainty` → `feat/a-mlflow` → `feat/a-brief` → `feat/a-vector` →
`feat/a-lakebase`. Each is an independent PR; merging in order avoids conflicts.

---

## 0. Prerequisite — build the tables/functions in the app's workspace

⚠️ We run on **two different Databricks workspaces**. I built and tested everything
in mine; the tables/functions/Lakebase instance do **not** exist in yours yet. After
merging, run these once against the workspace the app deploys to (SQL warehouse), in order:

```
pipeline/build_facility_trust.sql        -- facility_trust (scores + confidence bands)
pipeline/build_trust_validations.sql     -- trust_validations (self-validator)
pipeline/build_semantic_index.sql        -- facility_semantic (embeddings, ~50s)
pipeline/build_semantic_function.sql     -- semantic_facilities(query) SQL function
pipeline/build_planner_actions.sql       -- planner_actions Delta table (fallback store)
geo/build_facility_geo.sql               -- facility_geo (clean per-facility state/district; app dropdown + region filter)
geo/build_district_coverage.sql          -- district_coverage (data desert vs medical desert, NFHS-5)
```

Without `facility_geo` the app's main "Find facilities" tab and state dropdown come up
empty (`load_states()` reads it), so build it before the demo.

`facility_semantic` needs the `databricks-gte-large-en` embedding endpoint (present in
Free Edition). For Lakebase (§6), create the instance in your workspace too — or just
rely on the Delta fallback, which needs nothing extra.

---

## 1. A2 · Self-validator — "our own app double-checks itself"

Table `workspace.default.trust_validations` (one row per finding). Join it to each
facility card:

```sql
SELECT t.*, v.code, v.severity, v.message, v.disagrees_with_score
FROM facility_trust t
LEFT JOIN trust_validations v
  ON v.unique_id = t.unique_id
 AND (v.capability_key = t.capability_key OR v.capability_key IS NULL)
WHERE t.capability_key = :cap;
```

**UX:** if any finding has `disagrees_with_score = true`, show a prominent banner on the
card — *"⚠ Our own validator disagrees with this rating"* + the `message`(s). Other
findings render as muted caveats. This is the headline answer to the 35% "Evidence &
Trust / apps that double-check their work" criterion — make it visible.

## 2. A3 · Confidence bands — solid vs speculative

New columns on `facility_trust`: `trust_score_low`, `trust_score_high` (≈90% Wilson
interval). Render the band next to the score, e.g. a bar with a shaded low→high range.

**UX:** two facilities can share `trust_score` but differ in solidity — a tight band =
many independent sources agree; a wide band = rests on thin evidence. A one-liner like
"78%–100% (solid)" vs "40%–95% (speculative)" sells it.

## 3. A5 · Semantic search — beyond the 8 fixed capabilities

SQL function, call it directly:

```sql
SELECT * FROM workspace.default.semantic_facilities('cardiac cath lab');
-- unique_id, name, city, state, latitude, longitude, profile_snippet, similarity (top 50)
```

With a trust overlay for one of the 8 scored capabilities:

```sql
SELECT s.name, s.city, s.similarity, t.trust_state, t.trust_score, s.profile_snippet
FROM workspace.default.semantic_facilities(:query) s
LEFT JOIN facility_trust t
  ON t.unique_id = s.unique_id AND t.capability_key = :cap
ORDER BY s.similarity DESC LIMIT :k;
```

**UX:** a free-text search box ("what are you looking for?") above the 8-capability
filter. Handles "burns unit", "IVF", "keyhole surgery" — queries no dropdown can. ~2–3s
per search. Python helper if you prefer: `from scripts.semantic_search import search`.

## 4. A7 · Decision Brief — "a decision I'm saving for my team"

```python
from scripts.decision_brief import build_brief
md = build_brief(unique_ids, capability="icu", planner="Léo", host=DATABRICKS_HOST)
# returns a Markdown string: verdict + confidence band + verbatim evidence + gaps +
# validator findings (disagreements flagged) + human overrides + sources + methodology
```

**UX:** a "Generate decision brief" button on the shortlist → render `md` (st.markdown)
and a download button (`decision_brief.md`). Degrades fine if `planner_actions` is empty.
CLI to see it: `python scripts/decision_brief.py --ids id1,id2 --capability icu`.

## 5. A4 · MLflow trace — "How was this computed?"

Every rebuild is replayed as an MLflow 3 trace (`mlflow/trace_pipeline.py`), one span per
reasoning step (extract → score → rank → self-validate).

**UX:** a "How was this computed?" link that deep-links to the trace UI:
`${DATABRICKS_HOST}/ml/experiments/${experiment_id}/traces`. The script prints
`experiment_id` on each run — store the latest (or hardcode the experiment path
`/Users/<you>/trust-engine`). Fallback: the same receipts are already on the card
(evidence, band, validator findings), so the button can just expand those.

## 6. A6 · Persistence — where planner actions go

Use one interface; it picks the backend automatically:

```python
from scripts.persistence import PlannerActionsStore
store = PlannerActionsStore()          # store.backend == 'lakebase' (in Databricks) or 'delta'
store.write_action(unique_id, action_type, capability_key=..., planner=..., new_state=..., note=...)
store.list_actions(unique_id=None)     # -> list[dict]
```

- `action_type` ∈ {`override`, `note`, `shortlist`}; `new_state` for overrides.
- **Primary = Lakebase** (Postgres OLTP). Reachable only from inside Databricks, so when
  the app runs as a Databricks App it uses Lakebase; local dev auto-falls-back to the
  Delta table `workspace.default.planner_actions`. You don't have to handle either case —
  just call the interface.

---

## Gotchas

- **Two workspaces:** rebuild everything in the app's workspace (§0). Don't assume my
  tables exist in yours.
- **`planner_actions` now exists** as a Delta table (created by the A6 fallback test in my
  workspace). Same schema as before — your existing read/write still works, but prefer the
  `PlannerActionsStore` interface so Lakebase is used in production.
- **Lakebase instance** `trust-desk-oltp` lives in my workspace. For your deploy, either
  create your own instance (name it the same or set `LAKEBASE_INSTANCE`) or rely on Delta.
- **Semantic index cost:** `build_semantic_index.sql` embeds ~10k profiles (~50s, one-off).
  Re-run only when the source dataset changes.

Ping me (Léo) on any interface question — happy to adjust column names/shapes if it makes
the app cleaner. Nothing here is set in stone except what's in `docs/CONTRACT.md`.
