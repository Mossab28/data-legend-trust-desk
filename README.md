# Facility Trust Desk — India

> Databricks × Hack-Nation · Challenge 04 "Data Legend" · Track: **Facility Trust Desk**

A live Databricks App that turns 10,088 messy Indian healthcare-facility records into
decisions a non-technical NGO planner can **trust, defend, and save** — by treating every
capability as a *claim to verify*, showing the exact sentences behind every verdict, and
being honest about what it does not know.

**Live app:** https://facility-trust-desk-7474647859757540.aws.databricksapps.com
(Databricks Free Edition · workspace login required)

## The two distinctions that drive everything

- **Claim ≠ fact.** `capability = "ICU"` is an assertion. The app scores how much
  *independent* evidence backs it — and "proposed ICU" or "NICU not available" corroborate
  nothing.
- **Data desert ≠ medical desert.** An empty region in our records is an *unknown*, not a
  verdict. District-level views join the official NFHS-5 health survey to tell real unmet
  need (solid red) apart from missing data (hollow gray).

## What the planner does

1. Picks a capability (ICU, NICU, maternity, emergency, oncology, trauma, dialysis,
   surgery) and a region → facilities ranked by trust state:
   **Corroborated** (2+ independent sources agree) · **Claimed only** (stated, not
   confirmed) · **Unknown** (record too sparse to judge — never shown as "bad").
2. Expands any facility → the exact sentences from the record, field by field, plus
   "what we don't know".
3. Disagrees? → **override with a signed note**, persisted for the whole team.
   Shortlists group into named planning scenarios.
4. *Medical deserts* tab → 755 districts classified (likely underserved / data desert /
   no data / covered) on an interactive map.

## Architecture

```
Delta Share (read-only)                     workspace.default (ours)
┌──────────────────────────┐   pure-SQL     ┌──────────────────────────┐
│ facilities (10,088×51)   │──scorer v2────▶│ facility_trust (29k)     │
│ india_post_pincode_dir   │──geo joins────▶│ facility_geo, centroids  │
│ nfhs_5_district_health   │──desert class─▶│ district_coverage (755)  │
└──────────────────────────┘                │ planner_actions (writes) │
                                            └────────────┬─────────────┘
                                     serverless SQL warehouse
                                                         │
                                            Databricks App (Streamlit)
```

- **Scoring** (`pipeline/`): transparent rule engine in one replayable SQL statement —
  negation/aspirational filter, source weighting, independence buckets
  (narrative/procedure/equipment), contradiction penalties, sparsity → UNKNOWN.
  Hand-validated on 10 real cases: `pipeline/VALIDATION.md`.
- **Geo layer** (`geo/`): pincode-normalized states/districts (35 clean states from 254
  dirty values), NFHS-5 join (81% districts matched), 4-way desert classification.
- **App** (`app/`): Streamlit on Databricks Apps; parameterized SQL only; planner
  actions persisted with scenario grouping.

## Key tradeoffs (assumed)

- **No trained model.** There is no ground truth to train or score against; an auditable
  rule engine + human overrides beats a black box here — and the override log is exactly
  the labeled data a future model would need. LLM extraction was done upstream by the
  organizers (their "reasoning layer"); embeddings/LLM-judge are the planned next step.
- **District-level map** (PIN aggregated to district): individual PINs are too sparse to
  classify honestly.
- **Keyword+rules matching** can miss paraphrases; mitigated by matching across 5 fields
  and disclosed in `pipeline/VALIDATION.md` (residual limitations section).

## Replay / develop

```bash
# rebuild the trust table (idempotent)
./scripts/dbsql.sh "$(< pipeline/build_facility_trust.sql)"
# rebuild district coverage
./scripts/dbsql.sh "$(< geo/build_district_coverage.sql)"
# deploy the app (from main only)
databricks workspace import-dir app /Workspace/Users/<you>/facility-trust-desk --overwrite
databricks apps deploy facility-trust-desk --source-code-path /Workspace/Users/<you>/facility-trust-desk
```

Roadmap and team workflow: `ROADMAP.md` · Data contract: `docs/CONTRACT.md` ·
Demo script: `docs/DEMO.md` · Data findings: `docs/DATA_NOTES.md`

## Team

Mossab (product surface, ops) · Léo (trust engine) — built with Claude Code agents,
feature branches and cross-reviewed PRs.
