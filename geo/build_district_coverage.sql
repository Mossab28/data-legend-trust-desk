-- =============================================================================
-- build_district_coverage.sql
-- "Data desert != medical desert" — one row per (statename, district) from the
-- India Post pincode directory, enriched with:
--   * facility counts from the Virtue Foundation facilities table (pincode join)
--   * data_richness = avg share of 6 key facility fields with real content
--   * NFHS-5 official district health indicators (fuzzy name join)
--   * desert_class: honest 4-state classification
-- Rejouable: CREATE OR REPLACE TABLE workspace.default.district_coverage
-- Warehouse: any serverless SQL warehouse with read access to the VF catalog.
-- =============================================================================

CREATE OR REPLACE TABLE workspace.default.district_coverage AS

WITH
-- ---------------------------------------------------------------------------
-- 1. Reference frame: one row per (statename, district) from India Post.
--    District names normalized (lower/trim + alpha-only key for joins).
-- ---------------------------------------------------------------------------
districts AS (
  SELECT
    lower(trim(statename))                                  AS statename,
    lower(trim(district))                                   AS district,
    regexp_replace(lower(trim(district)), '[^a-z]', '')     AS district_key,
    count(DISTINCT pincode)                                 AS n_pincodes
  FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.india_post_pincode_directory
  GROUP BY 1, 2, 3
),

-- Distinct pincode -> (state, district) mapping. A pincode can straddle two
-- districts in rare cases; we keep one arbitrary-but-deterministic mapping
-- (max district) to avoid double counting facilities.
pin_map AS (
  SELECT pin, sd.statename, sd.district
  FROM (
    SELECT
      lpad(cast(pincode AS string), 6, '0')  AS pin,
      -- coherent (state, district) pair: max over structs, not per-column max
      max(struct(lower(trim(statename)) AS statename,
                 lower(trim(district))  AS district)) AS sd
    FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.india_post_pincode_directory
    GROUP BY 1
  )
),

-- ---------------------------------------------------------------------------
-- 2. Facilities: clean the pincode (first 6-digit run not starting with 0)
--    and score data richness over 6 key fields.
--    Placeholders treated as EMPTY: NULL, '', '[]', 'nan', 'null', 'none'.
-- ---------------------------------------------------------------------------
fac AS (
  SELECT
    unique_id,
    regexp_extract(trim(address_zipOrPostcode), '([1-9][0-9]{5})', 1) AS pin,
    (latitude  IS NOT NULL AND longitude IS NOT NULL
     AND abs(latitude)  > 0.001 AND abs(longitude) > 0.001
     AND latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180) AS has_geo,
    ( CASE WHEN lower(trim(coalesce(description,  ''))) NOT IN ('', '[]', 'nan', 'null', 'none') THEN 1 ELSE 0 END
    + CASE WHEN lower(trim(coalesce(capability,   ''))) NOT IN ('', '[]', 'nan', 'null', 'none') THEN 1 ELSE 0 END
    + CASE WHEN lower(trim(coalesce(procedure,    ''))) NOT IN ('', '[]', 'nan', 'null', 'none') THEN 1 ELSE 0 END
    + CASE WHEN lower(trim(coalesce(equipment,    ''))) NOT IN ('', '[]', 'nan', 'null', 'none') THEN 1 ELSE 0 END
    + CASE WHEN lower(trim(coalesce(numberDoctors,''))) NOT IN ('', '[]', 'nan', 'null', 'none') THEN 1 ELSE 0 END
    + CASE WHEN lower(trim(coalesce(capacity,     ''))) NOT IN ('', '[]', 'nan', 'null', 'none') THEN 1 ELSE 0 END
    ) / 6.0 AS richness
  FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
),

fac_by_district AS (
  SELECT
    pm.statename,
    pm.district,
    count(*)                                    AS n_facilities,
    sum(CASE WHEN f.has_geo THEN 1 ELSE 0 END)  AS n_facilities_geoloc,
    avg(f.richness)                             AS data_richness
  FROM fac f
  JOIN pin_map pm ON f.pin = pm.pin
  GROUP BY 1, 2
),

-- ---------------------------------------------------------------------------
-- 3. NFHS-5 indicators, cleaned. NFHS wraps low-sample values in parentheses
--    (e.g. '(60.4)') and uses '*' — stripped before try_cast.
-- ---------------------------------------------------------------------------
nfhs AS (
  SELECT
    lower(trim(state_ut))                                        AS s,
    regexp_replace(lower(trim(district_name)), '[^a-z]', '')     AS district_key,
    avg(try_cast(regexp_replace(institutional_birth_5y_pct,                        '[()*]', '') AS double)) AS institutional_birth_5y_pct,
    avg(try_cast(regexp_replace(births_delivered_by_csection_5y_pct,               '[()*]', '') AS double)) AS births_delivered_by_csection_5y_pct,
    avg(try_cast(regexp_replace(mothers_who_had_at_least_4_anc_visits_lb5y_pct,    '[()*]', '') AS double)) AS mothers_anc4_visits_pct,
    avg(try_cast(regexp_replace(hh_member_covered_health_insurance_pct,            '[()*]', '') AS double)) AS hh_health_insurance_pct
  FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.nfhs_5_district_health_indicators
  GROUP BY 1, 2
),

-- Districts whose normalized name is unique across all of NFHS: safe for a
-- district-only fallback join (fixes state renames like orissa/odisha).
nfhs_unique AS (
  SELECT district_key FROM nfhs GROUP BY district_key HAVING count(*) = 1
),

nfhs_joined AS (
  SELECT
    d.statename, d.district, d.district_key, d.n_pincodes,
    coalesce(e.institutional_birth_5y_pct,          fb.institutional_birth_5y_pct)          AS institutional_birth_5y_pct,
    coalesce(e.births_delivered_by_csection_5y_pct, fb.births_delivered_by_csection_5y_pct) AS births_delivered_by_csection_5y_pct,
    coalesce(e.mothers_anc4_visits_pct,             fb.mothers_anc4_visits_pct)             AS mothers_anc4_visits_pct,
    coalesce(e.hh_health_insurance_pct,             fb.hh_health_insurance_pct)             AS hh_health_insurance_pct,
    (e.district_key IS NOT NULL OR fb.district_key IS NOT NULL)                             AS nfhs_matched
  FROM districts d
  -- exact: state + normalized district name
  LEFT JOIN nfhs e
    ON d.statename = e.s AND d.district_key = e.district_key
  -- fallback: district name unique across NFHS (state name mismatch tolerated)
  LEFT JOIN (SELECT n.* FROM nfhs n JOIN nfhs_unique u ON n.district_key = u.district_key) fb
    ON e.district_key IS NULL AND d.district_key = fb.district_key
)

-- ---------------------------------------------------------------------------
-- 4. Final assembly + honest 4-state classification.
--    Thresholds (documented in geo/README.md):
--      data_richness < 0.40           -> we don't actually know this district
--      need signal = NFHS bottom-quartile on any of:
--        institutional_birth < 85 | ANC4 < 45 | c-section < 11
-- ---------------------------------------------------------------------------
SELECT
  nj.statename,
  nj.district,
  nj.n_pincodes,
  coalesce(fd.n_facilities, 0)          AS n_facilities,
  coalesce(fd.n_facilities_geoloc, 0)   AS n_facilities_geoloc,
  round(fd.data_richness, 3)            AS data_richness,
  nj.nfhs_matched,
  nj.institutional_birth_5y_pct,
  nj.births_delivered_by_csection_5y_pct,
  nj.mothers_anc4_visits_pct,
  nj.hh_health_insurance_pct,
  CASE
    -- 0 facilities and no external data: unknown, NOT proven empty
    WHEN coalesce(fd.n_facilities, 0) = 0 AND NOT nj.nfhs_matched
      THEN 'NO_DATA_NO_FACILITIES'
    -- 0-2 facilities but official NFHS data shows maternal-health need:
    -- probable true medical desert
    WHEN coalesce(fd.n_facilities, 0) <= 2 AND nj.nfhs_matched
         AND (   nj.institutional_birth_5y_pct          < 85
              OR nj.mothers_anc4_visits_pct             < 45
              OR nj.births_delivered_by_csection_5y_pct < 11)
      THEN 'LIKELY_UNDERSERVED'
    -- 0 facilities, NFHS matched but no need signal: still unknown coverage
    WHEN coalesce(fd.n_facilities, 0) = 0
      THEN 'NO_DATA_NO_FACILITIES'
    -- facilities exist but their records are mostly empty: data desert —
    -- we know that we don't know
    WHEN fd.data_richness < 0.40
      THEN 'DATA_DESERT'
    ELSE 'COVERED'
  END AS desert_class
FROM nfhs_joined nj
LEFT JOIN fac_by_district fd
  ON nj.statename = fd.statename AND nj.district = fd.district;

-- =============================================================================
-- VALIDATION (run after build)
-- =============================================================================
-- 1. Class distribution
-- SELECT desert_class, count(*) n, sum(n_facilities) fac
-- FROM workspace.default.district_coverage GROUP BY 1 ORDER BY n DESC;
--
-- 2. Pincode join coverage (facility side)
-- WITH fac AS (SELECT regexp_extract(trim(address_zipOrPostcode),'([1-9][0-9]{5})',1) pin
--              FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities)
-- SELECT count(*) total, sum(CASE WHEN p.pin IS NOT NULL THEN 1 ELSE 0 END) matched
-- FROM fac LEFT JOIN (SELECT DISTINCT lpad(cast(pincode AS string),6,'0') pin
--   FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.india_post_pincode_directory) p
--   ON fac.pin = p.pin;
--
-- 3. NFHS match rate
-- SELECT count(*) districts, sum(CASE WHEN nfhs_matched THEN 1 ELSE 0 END) matched
-- FROM workspace.default.district_coverage;
