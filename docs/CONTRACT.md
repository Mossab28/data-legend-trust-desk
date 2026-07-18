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
| trust_score | double | 0.0–1.0 |
| n_fields_corroborating | int | distinct INDEPENDENT evidence buckets (0–3): `narrative` (capability/description/specialties collapse into one — same self-reported source), `procedure`, `equipment` |
| evidence_json | string | JSON array of {"field": "...", "sentence": "..."} — exact sentences, verbatim |
| gaps_json | string | JSON array of strings — what is missing (e.g. "no anesthesia evidence for surgery claim") |
| record_completeness | double | 0.0–1.0 share of key fields with real (non-placeholder) content |
| number_doctors | string | raw |
| capacity | string | raw |
| source_urls | string | raw |

## Table `workspace.default.planner_actions` (written by the app)

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

## Trust logic (authoritative definition) — scorer v2

- CORROBORATED: evidence in ≥2 independent buckets (see `n_fields_corroborating`) AND trust_score ≥ 0.6
- CLAIMED_ONLY: fewer than 2 independent buckets, or score < 0.6 — the claim exists but is not independently corroborated
- UNKNOWN: record too sparse to judge (record_completeness < 0.35) — display as "not enough data", NEVER as "low trust"
- `trust_score = 0.60·min(1, n_buckets/3) + 0.20·best_source_weight + 0.20·min(1, (n_evidence−1)/4) − 0.25·contradiction − 0.15·aspirational_mix`, clamped to [0,1]
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
