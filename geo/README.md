# Geography layer

Two tables, both built purely from the read-only source share (India Post pincode
directory + Virtue Foundation facilities), both idempotent `CREATE OR REPLACE`.

## `workspace.default.facility_geo` — clean per-facility state/district

One row per facility (`unique_id`). Rebuild with `geo/build_facility_geo.sql`.

The raw `address_stateOrRegion` is unusable for filtering (~254 distinct values for
~36 real states). This table attaches a trustworthy `(state_clean, district)` by joining
the cleaned facility pincode to the India Post directory — using the **same** pin-cleaning
and deterministic `pin → (state, district)` map as `district_coverage`, so the two agree.
`district` is stored lower/trimmed (matches `district_coverage.district`; the app applies
`initcap()`); `state_clean` is initcap for a readable dropdown (joins lower() it).

**Read by the app** (`app/app.py`): `load_states()` (state dropdown), `load_facilities()`
(region filter), `load_call_first()` (join to `district_coverage`). Without this table the
main "Find facilities" tab comes up empty — build it before any demo.

---

# District Coverage — "data desert ≠ medical desert"

Table: **`workspace.default.district_coverage`** — 755 rows, one per `(statename, district)`
of the India Post pincode directory. Rebuild with `geo/build_district_coverage.sql`
(single `CREATE OR REPLACE TABLE`, rejouable via `scripts/dbsql.sh`).

## Why this table exists

A district with zero facilities in the Virtue Foundation dataset is **not proven empty** —
it may just be a *data* desert. This table separates the two by triangulating with an
independent official source (NFHS-5 district health indicators) and by measuring how much
we actually know about the facilities we do have.

## Pipeline

1. **Reference frame** — every `(statename, district)` in
   `india_post_pincode_directory` (755 districts, names lower/trimmed; alpha-only key
   for joins). Also builds a deterministic `pincode → (state, district)` map
   (struct-max when a pincode straddles two districts).
2. **Facility attachment** — facility pincodes are dirty; we extract the first
   6-digit run not starting with 0 via `regexp_extract(trim(address_zipOrPostcode), '([1-9][0-9]{5})')`
   and join on the directory. We deliberately do **not** use `address_stateOrRegion`
   (254 distinct values for ~36 real states — unusable).
3. **`data_richness`** — per facility, share of 6 key fields with real content
   (`description, capability, procedure, equipment, numberDoctors, capacity`), then
   averaged per district. Placeholders counted as empty: `NULL, '', '[]', 'nan', 'null', 'none'`
   (the dataset stores the *string* `'null'`, not SQL NULL).
4. **NFHS-5 join** — fuzzy: exact on `(lower(state), alpha-only district name)`, plus a
   fallback on district name alone **only when that name is unique across all of NFHS**
   (fixes state renames like orissa/odisha without cross-state false matches).
   NFHS numeric strings like `'(60.4)'` (low-sample flag) are cleaned with
   `regexp_replace(col, '[()*]', '')` + `try_cast`.

## Match rates (measured on this build)

| Join | Rate |
|---|---|
| Facility has a parseable 6-digit pincode | 9 785 / 10 088 = **97.0 %** |
| Facility attached to a directory district | 9 572 / 10 088 = **94.9 %** |
| Facility with valid lat/lon among attached | 9 542 / 9 572 = 99.7 % |
| District matched to an NFHS-5 row | 612 / 755 = **81.1 %** (553 exact + 59 unique-name fallback) |

Unmatched NFHS districts are concentrated in states with many post-2019 district splits
(Maharashtra 36, J&K 20, West Bengal 16…) — NFHS-5 uses the 2019-21 district frame.

## `desert_class` — thresholds and rationale

Evaluated in order:

| Class | Rule | Meaning |
|---|---|---|
| `NO_DATA_NO_FACILITIES` | 0 facilities AND (no NFHS match OR no need signal) | **We don't know.** Not proven empty — this is the honest "unknown" bucket. |
| `LIKELY_UNDERSERVED` | ≤ 2 facilities AND NFHS matched AND need signal | Official data shows maternal-health need but our dataset has (almost) nothing there → probable **true medical desert**. |
| `DATA_DESERT` | facilities present AND `data_richness < 0.40` | Facilities exist but their records are mostly empty → **we know that we don't know**. |
| `COVERED` | facilities present, `data_richness ≥ 0.40` | Present and reasonably documented. |

**Need signal** = any of (≈ NFHS bottom quartile, measured on this dataset:
p25 institutional birth = 83.7, p25 ANC4 = 45.1, p25 c-section = 10.7):

- `institutional_birth_5y_pct < 85`
- `mothers_anc4_visits_pct < 45`
- `births_delivered_by_csection_5y_pct < 11`

**Why `data_richness < 0.40`:** a facility scores 0.33 when only description/capability
are filled (the two near-universal LLM-extracted fields). Below 0.40 a district's
records carry essentially no operational content (no procedures, equipment, doctors,
capacity).

## Validation (this build)

| Class | Districts | Facilities |
|---|---|---|
| COVERED | 454 | 9 434 |
| LIKELY_UNDERSERVED | 192 | 135 |
| NO_DATA_NO_FACILITIES | 106 | 0 |
| DATA_DESERT | 3 | 3 |

DATA_DESERT is small **by honest measurement, not by construction**: field fill rates are
high (description 99 %, capability 99 %, procedure 91 %, equipment 76 %) so district-level
richness rarely drops below 0.40 (5th percentile = 0.50). The scarce fields are
`numberDoctors` (36 %) and `capacity` (25 %) — richness still discriminates *within*
COVERED for prioritization.

Plausible `LIKELY_UNDERSERVED` examples (all real remote districts):
**Mon** (Nagaland — institutional birth 21.4 %, ANC4 9.7 %, c-section 1.4 %),
**Phek** (Nagaland — 32.2 % / 9.5 % / 1.7 %), **Kiphire** (Nagaland — 34.8 % / 5.8 % / 2.1 %).

## Honest limits

- 516 facilities (5.1 %) have no usable pincode and are excluded from district counts.
- NFHS fallback join tolerates state-name mismatch; a renamed *district* with a
  non-unique name stays unmatched (143 districts, 18.9 %).
- `data_richness` measures **presence** of content, not its accuracy — LLM-extracted
  claims can be filled and still wrong.
- `LIKELY_UNDERSERVED` is a *probable* label: absence from this dataset + NFHS need
  is evidence, not proof, of a medical desert. Ground-truthing needed before action.
- NFHS-5 indicators are 2019-21; district boundaries have since changed in several states.
