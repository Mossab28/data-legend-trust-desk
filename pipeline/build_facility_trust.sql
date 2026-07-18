-- =============================================================================
-- build_facility_trust.sql
-- Builds workspace.default.facility_trust from the read-only Virtue Foundation
-- facilities share. Pure SQL, replayable (CREATE OR REPLACE). See docs/CONTRACT.md.
-- =============================================================================

CREATE OR REPLACE TABLE workspace.default.facility_trust AS
WITH kw (capability_key, keyword) AS (
  VALUES
    ('icu','icu'),('icu','intensive care'),('icu','critical care'),('icu','ventilator'),('icu','hdu'),
    ('nicu','nicu'),('nicu','neonatal'),('nicu','newborn intensive'),
    ('maternity','matern'),('maternity','obstetric'),('maternity','delivery'),('maternity','labour ward'),('maternity','labor ward'),('maternity','gynec'),
    ('emergency','emergency'),('emergency','casualty'),('emergency','trauma centre'),('emergency','ambulance'),('emergency','24x7'),('emergency','24/7'),
    ('oncology','oncolog'),('oncology','cancer'),('oncology','chemo'),('oncology','radiotherapy'),('oncology','radiation therapy'),('oncology','tumor'),('oncology','tumour'),
    ('trauma','trauma'),('trauma','fracture'),('trauma','orthopedic emergency'),('trauma','accident'),
    ('dialysis','dialysis'),('dialysis','nephrolog'),('dialysis','hemodial'),
    ('surgery','surger'),('surgery','operating theatre'),('surgery','operation theater'),('surgery','ot complex'),('surgery','anesthes'),('surgery','anaesthes')
),

src AS (
  SELECT
    unique_id, name,
    address_city, address_stateOrRegion, address_zipOrPostcode,
    try_cast(latitude AS double)  AS latitude,
    try_cast(longitude AS double) AS longitude,
    numberDoctors, capacity, source_urls,
    capability, `procedure`, equipment, description, specialties
  FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
),

-- Parse JSON-array-as-string claim fields; fall back to raw text on parse failure.
-- Filter placeholder elements ('', 'nan', '0', 'null', ...) everywhere.
parsed AS (
  SELECT
    *,
    filter(
      coalesce(from_json(capability, 'array<string>'), array(capability)),
      x -> x IS NOT NULL AND length(trim(x)) > 1 AND lower(trim(x)) NOT IN ('nan','null','none','0','[]','[""]')
    ) AS cap_arr,
    filter(
      coalesce(from_json(`procedure`, 'array<string>'), array(`procedure`)),
      x -> x IS NOT NULL AND length(trim(x)) > 1 AND lower(trim(x)) NOT IN ('nan','null','none','0','[]','[""]')
    ) AS proc_arr,
    filter(
      coalesce(from_json(equipment, 'array<string>'), array(equipment)),
      x -> x IS NOT NULL AND length(trim(x)) > 1 AND lower(trim(x)) NOT IN ('nan','null','none','0','[]','[""]')
    ) AS equip_arr,
    filter(
      coalesce(from_json(specialties, 'array<string>'), array(specialties)),
      x -> x IS NOT NULL AND length(trim(x)) > 1 AND lower(trim(x)) NOT IN ('nan','null','none','0','[]','[""]')
    ) AS spec_arr,
    -- description is prose: split into sentences
    filter(
      transform(split(coalesce(description, ''), '(?<=[.!?])\\s+'), x -> trim(x)),
      x -> length(x) > 1 AND lower(x) NOT IN ('nan','null','none','0','[]','[""]')
    ) AS desc_arr,
    -- facility-level anesthesia / operating-theatre evidence (equipment + procedure + description)
    CASE WHEN lower(concat_ws(' ', equipment, `procedure`, description)) LIKE '%anesthes%'
           OR lower(concat_ws(' ', equipment, `procedure`, description)) LIKE '%anaesthes%'
           OR lower(concat_ws(' ', equipment, `procedure`, description)) LIKE '%operating theat%'
           OR lower(concat_ws(' ', equipment, `procedure`, description)) LIKE '%operation theat%'
           OR lower(concat_ws(' ', equipment, `procedure`, description)) LIKE '%ot complex%'
           OR concat_ws(' ', equipment, `procedure`, description) RLIKE '\\bO\\.?T\\.?\\b'
         THEN 1 ELSE 0 END AS has_anes,
    -- placeholder-aware "real content" flags for completeness
    CASE WHEN numberDoctors IS NOT NULL AND lower(trim(numberDoctors)) NOT IN ('','nan','null','none','0','[]','[""]') THEN 1 ELSE 0 END AS ok_doctors,
    CASE WHEN capacity      IS NOT NULL AND lower(trim(capacity))      NOT IN ('','nan','null','none','0','[]','[""]') THEN 1 ELSE 0 END AS ok_capacity,
    CASE WHEN address_city  IS NOT NULL AND lower(trim(address_city))  NOT IN ('','nan','null','none','0','[]','[""]') THEN 1 ELSE 0 END AS ok_city,
    CASE WHEN try_cast(latitude AS double)  IS NOT NULL AND try_cast(latitude AS double)  <> 0
          AND try_cast(longitude AS double) IS NOT NULL AND try_cast(longitude AS double) <> 0 THEN 1 ELSE 0 END AS ok_coords
  FROM src
),

completeness AS (
  SELECT
    *,
    ( CASE WHEN size(desc_arr)  > 0 THEN 1 ELSE 0 END
    + CASE WHEN size(cap_arr)   > 0 THEN 1 ELSE 0 END
    + CASE WHEN size(proc_arr)  > 0 THEN 1 ELSE 0 END
    + CASE WHEN size(equip_arr) > 0 THEN 1 ELSE 0 END
    + ok_doctors + ok_capacity + ok_city + ok_coords ) / 8.0 AS record_completeness
  FROM parsed
),

-- one row per (facility, field, sentence)
sent AS (
  SELECT unique_id, 'capability'  AS field, sentence FROM completeness LATERAL VIEW explode(cap_arr)   t AS sentence
  UNION ALL
  SELECT unique_id, 'procedure'   AS field, sentence FROM completeness LATERAL VIEW explode(proc_arr)  t AS sentence
  UNION ALL
  SELECT unique_id, 'equipment'   AS field, sentence FROM completeness LATERAL VIEW explode(equip_arr) t AS sentence
  UNION ALL
  SELECT unique_id, 'description' AS field, sentence FROM completeness LATERAL VIEW explode(desc_arr)  t AS sentence
  UNION ALL
  SELECT unique_id, 'specialties' AS field, sentence FROM completeness LATERAL VIEW explode(spec_arr)  t AS sentence
),

matches AS (
  SELECT DISTINCT s.unique_id, k.capability_key, s.field, s.sentence
  FROM sent s
  JOIN kw k ON lower(s.sentence) LIKE concat('%', k.keyword, '%')
),

agg AS (
  SELECT
    unique_id,
    capability_key,
    count(DISTINCT CASE WHEN field IN ('capability','procedure','equipment','description') THEN field END) AS n_fields_corroborating,
    to_json(
      slice(
        array_distinct(collect_list(named_struct('field', field, 'sentence', left(sentence, 300)))),
        1, 8
      )
    ) AS evidence_json,
    max(CASE WHEN field = 'equipment' AND (sentence RLIKE '[0-9]' OR length(sentence) > 60) THEN 1 ELSE 0 END) AS equip_specific
  FROM matches
  GROUP BY unique_id, capability_key
),

scored AS (
  SELECT
    c.unique_id,
    c.name,
    c.address_city            AS city,
    c.address_stateOrRegion   AS state,
    c.address_zipOrPostcode   AS pincode,
    c.latitude,
    c.longitude,
    a.capability_key,
    a.n_fields_corroborating,
    a.evidence_json,
    c.record_completeness,
    c.numberDoctors           AS number_doctors,
    c.capacity,
    c.source_urls,
    -- contradiction: surgery-level claim without anesthesia/OT evidence
    CASE WHEN a.capability_key IN ('surgery','trauma','oncology') AND c.has_anes = 0 THEN 1 ELSE 0 END AS contradiction,
    greatest(0.0,
      least(1.0, a.n_fields_corroborating / 3.0) * 0.7
      + (CASE WHEN a.equip_specific = 1 THEN 1.0 ELSE 0.4 END) * 0.3
      - (CASE WHEN a.capability_key IN ('surgery','trauma','oncology') AND c.has_anes = 0 THEN 0.25 ELSE 0.0 END)
    ) AS trust_score,
    c.equip_arr, c.desc_arr, c.ok_doctors, c.ok_capacity, c.ok_coords
  FROM agg a
  JOIN completeness c USING (unique_id)
)

SELECT
  unique_id,
  name,
  city,
  state,
  pincode,
  latitude,
  longitude,
  capability_key,
  CASE
    WHEN record_completeness < 0.35 THEN 'UNKNOWN'
    WHEN n_fields_corroborating >= 2 AND trust_score >= 0.6 THEN 'CORROBORATED'
    ELSE 'CLAIMED_ONLY'
  END AS trust_state,
  round(trust_score, 3) AS trust_score,
  cast(n_fields_corroborating AS int) AS n_fields_corroborating,
  evidence_json,
  to_json(filter(array(
    CASE WHEN contradiction = 1        THEN 'surgery-level claim but no anesthesia/OT evidence' END,
    CASE WHEN size(equip_arr) = 0      THEN 'no equipment data'   END,
    CASE WHEN ok_doctors  = 0          THEN 'no doctor count'     END,
    CASE WHEN ok_capacity = 0          THEN 'no capacity data'    END,
    CASE WHEN size(desc_arr) = 0       THEN 'no description'      END,
    CASE WHEN ok_coords   = 0          THEN 'no coordinates'      END
  ), x -> x IS NOT NULL)) AS gaps_json,
  round(record_completeness, 3) AS record_completeness,
  number_doctors,
  capacity,
  source_urls
FROM scored;
