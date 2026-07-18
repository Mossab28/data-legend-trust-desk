# Interface contract between pipeline and app

## Table `workspace.default.facility_trust` (built by the scoring pipeline, read by the app)

One row = (facility × capability_key). Only rows where the facility claims OR evidences the capability.

| column | type | notes |
|---|---|---|
| unique_id | string | facility id from source |
| name | string | facility name |
| city | string | address_city |
| state | string | address_stateOrRegion (raw) |
| pincode | string | address_zipOrPostcode |
| latitude | double | may be null/0 |
| longitude | double | may be null/0 |
| capability_key | string | one of: icu, nicu, maternity, emergency, oncology, trauma, dialysis, surgery |
| trust_state | string | CORROBORATED / CLAIMED_ONLY / UNKNOWN |
| trust_score | double | 0.0–1.0 (point estimate) |
| trust_score_low | double | lower bound of the ~90% Wilson interval — the conservative floor |
| trust_score_high | double | upper bound of the ~90% Wilson interval |
| n_fields_corroborating | int | distinct INDEPENDENT evidence buckets (0–3): `narrative` (capability/description/specialties collapse into one — same self-reported source), `procedure`, `equipment` |
| evidence_json | string | JSON array of {"field": "...", "sentence": "..."} — exact sentences, verbatim |
| gaps_json | string | JSON array of strings — what is missing (e.g. "no anesthesia evidence for surgery claim") |
| record_completeness | double | 0.0–1.0 share of key fields with real (non-placeholder) content |
| number_doctors | string | raw |
| capacity | string | raw |
| source_urls | string | raw |

## Planner actions (written by the app) — Lakebase primary, Delta fallback (A6)

Persisted via `scripts/persistence.py` (`PlannerActionsStore`). **Primary store:
Lakebase** (managed Postgres OLTP, instance `trust-desk-oltp`) — the right tool for
small transactional writes. **Fallback: Delta** `workspace.default.planner_actions`
(`pipeline/build_planner_actions.sql`), used automatically when the Lakebase endpoint
is unreachable (Lakebase endpoints are only reachable from inside the Databricks
network — a Databricks App reaches them, a local laptop does not). Same schema both sides.

```python
from scripts.persistence import PlannerActionsStore
store = PlannerActionsStore()                 # auto-selects backend; store.backend == 'lakebase'|'delta'
store.write_action(unique_id, action_type, capability_key=..., planner=..., new_state=..., note=...)
store.list_actions(unique_id=None)            # -> list[dict]
```

| column | type |
|---|---|
| action_id | string (uuid) |
| ts | timestamp |
| planner | string |
| unique_id | string |
| capability_key | string |
| action_type | string (override / note / shortlist) |
| new_state | string nullable |
| note | string |
| scenario | string nullable — planning scenario name grouping shortlists (added in B2) |

## Table `workspace.default.trust_validations` (built by the self-correction validator, read by the app)

An INDEPENDENT audit of `facility_trust`. One row per finding. Built by
`pipeline/build_trust_validations.sql`. This is how the app "double-checks its own work".

| column | type | notes |
|---|---|---|
| unique_id | string | facility id |
| capability_key | string \| null | the capability the finding is about; **NULL = facility-level** finding (applies to all capabilities) |
| code | string | `SHARED_EVIDENCE` / `UNSUPPORTED_SURGERY` / `CAPACITY_WITHOUT_STAFF` |
| severity | string | `warning` / `info` |
| message | string | human-readable, planner-facing (already contains the numbers) |
| disagrees_with_score | boolean | true = this finding contradicts a CORROBORATED score → surface it prominently |
| detail_json | string | JSON with the raw numbers (`n_shared`, `max_facilities`, `capacity`, …) for traceability |

**App-side join** (workstream B): `LEFT JOIN trust_validations v ON v.unique_id = t.unique_id AND (v.capability_key = t.capability_key OR v.capability_key IS NULL)`.
Suggested UX: on a facility card, if any `disagrees_with_score` finding exists, show a
prominent *"⚠ Our own validator disagrees with this rating"* banner with the `message`(s);
other findings render as muted caveats.

## MLflow trace deep-link (for the "How was this computed?" button)

Every rebuild is replayed as an MLflow 3 trace (`mlflow/trace_pipeline.py`) with one
span per reasoning step (extract → score → rank-by-capability → self-validate). The app
can deep-link to the trace UI so a planner can inspect the engine's reasoning end-to-end:

- Experiment: `/Users/<user>/trust-engine`
- Traces URL: `${DATABRICKS_HOST}/ml/experiments/${experiment_id}/traces`

The script prints `experiment_id` / `run_id` on each run; persist the latest to build the
link. If tracing is unavailable, the button can fall back to the same receipts the trace
carries: `evidence_json` + `n_fields_corroborating` + `trust_score_low/high` + matching
`trust_validations` rows.

## Semantic capability search (A5 — `workspace.default.semantic_facilities`)

Free-text search over facility capability profiles that goes **beyond the 8 fixed
capability keys** (e.g. "cardiac cath lab", "burns unit", "IVF"). Built fully in-warehouse
with the `databricks-gte-large-en` foundation embedding model via `ai_query` — no Vector
Search endpoint needed (none exists on Free Edition). One L2-normalised profile embedding
per facility lives in `workspace.default.facility_semantic`; similarity = dot product.

**Table-valued SQL function (primary interface for the app):**
```sql
SELECT * FROM workspace.default.semantic_facilities('cardiac cath lab');
-- -> unique_id, name, city, state, latitude, longitude, profile_snippet, similarity  (top 50, ranked)
```
Overlay trust for one of the 8 scored capabilities by joining `facility_trust`:
```sql
SELECT s.name, s.city, s.similarity, t.trust_state, t.trust_score
FROM workspace.default.semantic_facilities('neonatal intensive care') s
LEFT JOIN workspace.default.facility_trust t
  ON t.unique_id = s.unique_id AND t.capability_key = 'nicu'
ORDER BY s.similarity DESC LIMIT 10;
```
Rebuild: `pipeline/build_semantic_index.sql` then `pipeline/build_semantic_function.sql`.
CLI/demo: `python scripts/semantic_search.py "burns unit" --capability trauma --k 8`.

## Decision Brief (exportable artifact — `scripts/decision_brief.py`)

Turns a shortlist into an evidence-cited Markdown **Decision Brief** ("a decision I'm
saving for my team"). For each (facility × capability) it assembles the trust verdict +
confidence band, the verbatim evidence sentences, the gaps, the validator findings
(disagreements flagged), and any human overrides from `planner_actions`.

**App integration (workstream B):**
```python
from scripts.decision_brief import build_brief
md = build_brief(unique_ids, capability="icu", planner="Léo", host=DATABRICKS_HOST)
# -> render md, offer as download (decision_brief.md)
```
`build_brief` reads `facility_trust` (+ `trust_validations`, `planner_actions` if present)
and returns a Markdown string. `planner_actions` is optional — the brief renders fine
without it. CLI: `python scripts/decision_brief.py --from-shortlist --planner "…"` pulls
ids from `planner_actions` where `action_type='shortlist'`.

## Trust logic (authoritative definition) — scorer v2

- CORROBORATED: evidence in ≥2 independent buckets (see `n_fields_corroborating`) AND trust_score ≥ 0.6
- CLAIMED_ONLY: fewer than 2 independent buckets, or score < 0.6 — the claim exists but is not independently corroborated
- UNKNOWN: record too sparse to judge (record_completeness < 0.35) — display as "not enough data", NEVER as "low trust"
- `trust_score = 0.60·min(1, n_buckets/3) + 0.20·best_source_weight + 0.20·min(1, (n_evidence−1)/4) − 0.25·contradiction − 0.15·aspirational_mix`, clamped to [0,1]
- Uncertainty band: `trust_score_low`/`trust_score_high` are a Wilson score interval (z=1.645) with effective sample size = total evidence weight. A wide `trust_score − trust_score_low` gap = the rating rests on thin/low-quality evidence (speculative); a tight gap = many independent sources agree (solid). **App-side:** render the band next to the score (e.g. a bar with a shaded low→high range); two facilities can share a score yet differ sharply in solidity.
- Source weights: specific equipment (has digit or >60 chars) 1.0 · generic equipment/procedure 0.7 · capability 0.6 · description 0.5 · specialties 0.4
- Negation / aspirational: a matched sentence expressing future intent or absence (`proposed`, `under construction`, `plans to`, `upcoming`, `will be`, `not available`, `no longer`…) does NOT corroborate. A (facility,capability) with only such hits is dropped; mixed with real evidence → −0.15 and a gap note. `planned` alone is not a trigger (elective care preserved).
- Contradiction penalty: surgery/trauma/oncology claims with zero anesthesia/OT/theatre evidence → score −0.25, add to gaps_json
- Placeholders ('', '[]', '[""]', 'nan', '0') are NOT content anywhere.

## Capability keyword map (keep in sync app-side for labels)

icu: icu, intensive care, critical care, ventilator, hdu
nicu: nicu, neonatal, newborn intensive
maternity: matern, obstetric, delivery, labour ward, labor ward, gynec
emergency: emergency, casualty, trauma centre, ambulance, 24x7, 24/7
oncology: oncolog, cancer, chemo, radiotherapy, radiation therapy, tumor, tumour
trauma: trauma, fracture, orthopedic emergency, accident
dialysis: dialysis, nephrolog, hemodial
surgery: surger, operating theatre, operation theater, ot complex, anesthes, anaesthes
