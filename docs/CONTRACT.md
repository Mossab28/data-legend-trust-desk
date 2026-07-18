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
| n_fields_corroborating | int | distinct fields (capability/procedure/equipment/description) with evidence |
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

## Trust logic (authoritative definition)

- CORROBORATED: evidence in ≥2 distinct fields, trust_score ≥ 0.6
- CLAIMED_ONLY: claim present in exactly 1 field, no corroboration
- UNKNOWN: record too sparse to judge (record_completeness < 0.35) — display as "not enough data", NEVER as "low trust"
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
