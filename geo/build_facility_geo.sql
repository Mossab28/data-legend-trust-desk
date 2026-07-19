-- =============================================================================
-- build_facility_geo.sql
-- Per-facility clean geography — one row per facility (unique_id), attaching a
-- trustworthy (state, district) via the India Post pincode directory.
--
-- WHY THIS TABLE EXISTS
-- The raw address_stateOrRegion field is unusable for filtering: ~254 distinct
-- values for ~36 real states (typos, abbreviations, mixed language). The app's
-- state dropdown, region filter and the district_coverage join all read this
-- table instead, so they get consistent, normalized names.
--
-- Consumed by app/app.py:
--   * load_states()      -> SELECT state_clean ...            (dropdown values)
--   * load_facilities()  -> LEFT JOIN g ON g.unique_id ...    (region filter)
--   * load_call_first()  -> JOIN district_coverage d
--        ON lower(g.district) = d.district AND lower(g.state_clean) = d.statename
--
-- CONSISTENCY WITH district_coverage
-- Uses the SAME pincode cleaning and the SAME deterministic pin -> (state,
-- district) map as geo/build_district_coverage.sql, so the two tables agree.
--   * district  is stored lower/trimmed (matches district_coverage.district;
--     the app applies initcap() for display).
--   * state_clean is stored initcap for a readable dropdown; every join against
--     district_coverage lower()s it, so casing never breaks a join.
--
-- Idempotent: CREATE OR REPLACE. Read-only w.r.t. the source share.
-- Rebuild: ./scripts/dbsql.sh "$(< geo/build_facility_geo.sql)"
-- =============================================================================

CREATE OR REPLACE TABLE workspace.default.facility_geo AS

WITH
-- Deterministic pincode -> (state, district) map. A pincode can straddle two
-- districts in rare cases; keep one arbitrary-but-deterministic mapping (max
-- over the struct, not per-column max) to avoid incoherent (state, district).
pin_map AS (
  SELECT pin, sd.statename AS statename, sd.district AS district
  FROM (
    SELECT
      lpad(cast(pincode AS string), 6, '0') AS pin,
      max(struct(lower(trim(statename)) AS statename,
                 lower(trim(district))  AS district)) AS sd
    FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.india_post_pincode_directory
    GROUP BY 1
  )
),

-- Facility pincodes are dirty: take the first 6-digit run not starting with 0.
fac AS (
  SELECT
    unique_id,
    regexp_extract(trim(address_zipOrPostcode), '([1-9][0-9]{5})', 1) AS pin
  FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
)

SELECT
  f.unique_id,
  nullif(f.pin, '')                       AS pincode,
  initcap(pm.statename)                   AS state_clean,   -- readable in the dropdown
  pm.district                             AS district       -- lower/trim, matches district_coverage
FROM fac f
LEFT JOIN pin_map pm
  ON nullif(f.pin, '') = pm.pin;

-- =============================================================================
-- VALIDATION (run after build)
-- =============================================================================
-- 1. Rows == number of facilities (one row per facility, LEFT JOIN keeps all).
-- SELECT count(*) AS facilities,
--        sum(CASE WHEN state_clean IS NOT NULL THEN 1 ELSE 0 END) AS with_state
-- FROM workspace.default.facility_geo;
--
-- 2. State dropdown preview (what load_states() will show).
-- SELECT state_clean, count(*) n FROM workspace.default.facility_geo
-- WHERE state_clean IS NOT NULL AND trim(state_clean) <> ''
-- GROUP BY state_clean ORDER BY n DESC;
--
-- 3. district_coverage join sanity (should be > 0 and mostly matching).
-- SELECT count(*) AS joined_rows
-- FROM workspace.default.facility_geo g
-- JOIN workspace.default.district_coverage d
--   ON lower(g.district) = d.district AND lower(g.state_clean) = d.statename;
