# Data notes — what the real dataset looks like

Source (Delta Share, read-only):
`databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset`

## Tables

| Table | Rows | Role |
|---|---|---|
| `facilities` | 10,088 | The messy facility records (51 cols) — our core |
| `india_post_pincode_directory` | — | pincode → district / state / lat-lon (geo join) |
| `nfhs_5_district_health_indicators` | — | NFHS-5 official health indicators per district (~110 cols) — external reference for *data desert ≠ medical desert* |

## `facilities` — the fields that matter

**Claim fields are JSON arrays of free-text sentences (stored as strings):**
- `capability` — array of capability claims (e.g. `["Houses Gurgaon's first stroke centre", ...]`)
- `procedure` — array of procedure claims (e.g. `["DBS therapy for neuro disorders", ...]`)
- `equipment` — array of equipment claims (e.g. `["Elekta Axesse linear accelerator", ...]`)
- `specialties` — specialties
- `description` — prose paragraph (the richest corroborating text)

→ **One sentence = one citable claim.** This is what makes row-level citations natural.

**Structured-ish fields:** `name`, `numberDoctors`, `capacity`, `yearEstablished`,
`address_stateOrRegion`, `address_city`, `address_zipOrPostcode`, `latitude`, `longitude`,
`source_urls`, `unique_id`, `cluster_id`.

## Coverage gotcha (critical for the Trust Score)

"Empty" is NOT SQL NULL — it's placeholders: `""`, `[]`, `["" ]`, `nan`, `0`. Raw
`count(col)` reports ~99% because the columns are non-null strings. Real emptiness must be
detected on content:
- `equipment` real coverage ≈ **72.5%** (excluding `''`, `[]`, `["" ]`)
- `address_stateOrRegion` has **254 distinct values** for ~36 real states → state field is
  itself dirty (needs normalization / geo join via pincode).
- ⚠️ `numberDoctors` / `capacity` read ~99% filled here, which does NOT match the brief's
  stated 36% / 25%. TODO: inspect the value distribution (may contain `nan`/`0` placeholders
  in another form). Matters for the data-desert narrative.

## Arrays also contain empty strings mid-array

e.g. `procedure = ["", "Robotic-assisted cancer surgery", ...]` — must filter empty elements
when counting evidence, or the count is inflated.
