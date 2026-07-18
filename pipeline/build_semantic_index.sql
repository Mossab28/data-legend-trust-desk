-- =============================================================================
-- build_semantic_index.sql  ·  A5 · Semantic capability search
-- Builds workspace.default.facility_semantic: one L2-normalised embedding per
-- facility (a "capability profile" = capability + procedure + equipment +
-- specialties + description), computed with the Databricks foundation embedding
-- model `databricks-gte-large-en` via ai_query() — 100% in-warehouse, no Vector
-- Search endpoint required (none is available on Free Edition).
--
-- Why per-facility (not per-sentence): 285k distinct claim sentences is too much
-- to embed for a hackathon build; one profile embedding per facility (~10k) is
-- the right granularity for "find facilities that do X" free-text search that
-- goes BEYOND the 8 fixed capability keys (e.g. "cardiac cath lab", "burns unit").
--
-- Embeddings are L2-normalised at build time, so semantic similarity at query
-- time is a plain dot product (see semantic_search.py / semantic_facilities()).
-- =============================================================================

CREATE OR REPLACE TABLE workspace.default.facility_semantic AS
WITH src AS (
  SELECT
    unique_id, name,
    address_city            AS city,
    address_stateOrRegion   AS state,
    try_cast(latitude AS double)  AS latitude,
    try_cast(longitude AS double) AS longitude,
    capability, `procedure`, equipment, specialties, description
  FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
),
prof AS (
  SELECT
    unique_id, name, city, state, latitude, longitude,
    -- Assemble a readable capability profile from all claim fields. Parse the
    -- JSON-array-as-string fields; fall back to raw text. Trim to 1500 chars.
    substr(trim(concat_ws('. ',
      concat_ws(' ', coalesce(from_json(capability,   'array<string>'), array(capability))),
      concat_ws(' ', coalesce(from_json(`procedure`,  'array<string>'), array(`procedure`))),
      concat_ws(' ', coalesce(from_json(equipment,    'array<string>'), array(equipment))),
      concat_ws(' ', coalesce(from_json(specialties,  'array<string>'), array(specialties))),
      coalesce(description, '')
    )), 1, 1500) AS profile_text
  FROM src
),
kept AS (
  -- Drop records with no real profile content (placeholders only).
  SELECT * FROM prof
  WHERE length(profile_text) >= 12
    AND lower(profile_text) NOT IN ('nan','null','none','0','[]','[""]')
),
embedded AS (
  SELECT
    unique_id, name, city, state, latitude, longitude, profile_text,
    ai_query('databricks-gte-large-en', profile_text) AS emb
  FROM kept
)
SELECT
  unique_id, name, city, state, latitude, longitude, profile_text,
  -- L2-normalise so cosine similarity == dot product at query time.
  transform(
    emb,
    x -> x / sqrt(greatest(1e-12, aggregate(transform(emb, y -> y * y), CAST(0 AS DOUBLE), (a, b) -> a + b)))
  ) AS embedding
FROM embedded;
