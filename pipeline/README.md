# facility_trust pipeline

`build_facility_trust.sql` builds `workspace.default.facility_trust` (one row per facility × capability_key) from the read-only share `databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities`, in pure SQL. The claim fields (`capability`, `procedure`, `equipment`, `specialties`) are strings holding JSON arrays of sentences: they are parsed with `from_json` (fallback: raw text on parse failure) and all placeholder content (`''`, `[]`, `[""]`, `nan`, `0`, ...) is filtered out, both at field and array-element level. `description` prose is split into sentences. Each sentence is matched (lowercase `LIKE`) against the capability→keyword map from `docs/CONTRACT.md`; matches produce verbatim `evidence_json` entries (max 8, truncated to 300 chars, best source first) with their source field.

## Scoring v2 (feat/a-scoring-v2)

Three reasoning steps turn raw keyword hits into an honest trust signal (validated by hand in [`VALIDATION.md`](VALIDATION.md)):

1. **Negation / aspirational filter.** A matched sentence is dropped from the *positive* evidence when it expresses future intent or absence rather than a present capability. Detection is **proximity-based**: an unambiguous phrase anywhere (`under construction`, `not available`, `no longer`, `non-functional`, `proposed`, `(future)`) **or** a future-intent trigger (`plans to`, `upcoming`, `will be`, `to be established`, `being set up`, `opening shortly`, `sanctioned`…) appearing in the ~28 chars *immediately before* the matched keyword. Bare `planned` is deliberately **not** a trigger, so legitimate elective care ("performs planned surgeries", "planned emergency treatment") is preserved. A `(facility, capability)` with only aspirational/negated hits is removed entirely; a facility that mixes them with real evidence keeps the pair, takes a −0.15 score dampener, and gets a gap note.

2. **Source weighting.** Each evidence sentence gets a weight: specific equipment (contains a digit or >60 chars) = 1.0, generic equipment / procedure = 0.7, capability = 0.6, description = 0.5, specialties = 0.4. The best-source weight feeds the score.

3. **Independence buckets (anti-fake-corroboration).** `capability`, `description` and `specialties` are self-reported narrative — routinely the same source text copied across fields — so they collapse into **one** `narrative` bucket. `procedure` and `equipment` are separate structured buckets. `n_fields_corroborating` = distinct independent buckets (max 3). Same-source narrative can therefore no longer masquerade as multi-field corroboration.

`trust_score = 0.60·min(1, n_buckets/3) + 0.20·best_weight + 0.20·min(1, (n_evidence−1)/4) − 0.25·contradiction − 0.15·aspirational_mix`, clamped to [0,1]. The contradiction penalty fires when a surgery/trauma/oncology claim has zero anesthesia/OT evidence anywhere in the record. `record_completeness` is the share of 8 key fields with real content; `trust_state` is UNKNOWN if completeness < 0.35 (priority), CORROBORATED if ≥2 buckets and score ≥ 0.6, else CLAIMED_ONLY. `gaps_json` lists the contradiction, any aspirational wording, and empty key fields.

To replay: with the SQL warehouse running and `~/.databrickscfg` auth configured, run
`./scripts/dbsql.sh "$(< pipeline/build_facility_trust.sql)"` from the repo root (poll the returned `statement_id` via `databricks api get /api/2.0/sql/statements/<id>` if it exceeds the 30 s wait). The statement is a single `CREATE OR REPLACE TABLE`, fully idempotent — rerunning it rebuilds the table from scratch with no side effects on the source.

## Self-correction validator (`build_trust_validations.sql`)

A second, **independent** pass that audits the scorer's own output and writes
`workspace.default.trust_validations` (one row per finding — see `docs/CONTRACT.md`). It runs
*after* `facility_trust` and reads it back, so the two systems can disagree — which is the
whole point: the product shows where it doubts itself (Evidence & Trust, 35%).

- **SHARED_EVIDENCE** — the evidence sentences behind a claim are duplicated verbatim across
  ≥4 other facilities (extraction boilerplate). Detected globally over all claim sentences
  ≥45 chars; each finding reports how many of the facility's evidence sentences are shared and
  the worst multiplicity (e.g. one sentence reused on 79 facilities).
- **UNSUPPORTED_SURGERY** — surgery/trauma/oncology scored CORROBORATED, yet zero
  anesthesia/operating-theatre evidence anywhere in the record (catches e.g. eye clinics rated
  as full surgical capability).
- **CAPACITY_WITHOUT_STAFF** — declared bed capacity > 1000 with no doctors listed
  (unstaffed capacity or data-entry error; `warning` when > 2000).

`disagrees_with_score = true` marks findings that contradict a CORROBORATED rating — the app
surfaces these first. Rebuild: `./scripts/dbsql.sh "$(< pipeline/build_trust_validations.sql)"`
(run after `build_facility_trust.sql`; idempotent CREATE OR REPLACE).
