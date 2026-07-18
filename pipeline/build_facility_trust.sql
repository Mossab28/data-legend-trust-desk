-- =============================================================================
-- build_facility_trust.sql  ·  Trust Scorer v2
-- Builds workspace.default.facility_trust from the read-only Virtue Foundation
-- facilities share. Pure SQL, replayable (CREATE OR REPLACE). See docs/CONTRACT.md.
--
-- v2 changes (workstream A · feat/a-scoring-v2):
--   1. Negation / aspirational detection — "proposed ICU", "under construction",
--      "plans to establish NICU", "not available" no longer corroborate a claim.
--      Detection is PROXIMITY-based (trigger right before the matched keyword) so
--      that legitimate "planned surgeries" (elective care) is NOT penalised.
--   2. Source weighting — an equipment line with a model number/detail outweighs a
--      vague description sentence.
--   3. Cross-field de-duplication — the same sentence copied into capability AND
--      description counts as ONE piece of evidence, not two (no fake corroboration).
--
-- Output schema is unchanged (see docs/CONTRACT.md) so the app keeps working.
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

-- keyword hits, with per-hit metadata used by the v2 scorer
matches_raw AS (
  SELECT
    s.unique_id,
    k.capability_key,
    s.field,
    s.sentence,
    -- normalised key for cross-field de-duplication
    regexp_replace(lower(trim(s.sentence)), '[^a-z0-9]', '') AS norm_key,
    -- source weight: specific equipment (has a number or is long/detailed) is strongest
    CASE
      WHEN s.field = 'equipment'   AND (s.sentence RLIKE '[0-9]' OR length(s.sentence) > 60) THEN 1.0
      WHEN s.field = 'equipment'   THEN 0.7
      WHEN s.field = 'procedure'   THEN 0.7
      WHEN s.field = 'capability'  THEN 0.6
      WHEN s.field = 'description' THEN 0.5
      ELSE 0.4  -- specialties
    END AS weight,
    -- ASPIRATIONAL / NEGATED detection ------------------------------------
    -- (a) unambiguous phrases, position-independent
    -- (b) a "future intent" trigger appearing in the ~28 chars just BEFORE the
    --     matched keyword (so "plans to establish NICU" is caught, but a real
    --     "performs planned surgeries" is NOT — "planned" alone is not a trigger).
    CASE WHEN
         lower(s.sentence) RLIKE '(under construction|not available|no longer|non-?functional|not functional|unavailable|yet to be|to be operational|expected to be operational|not yet operational|\\(future\\)|proposed )'
      OR substr(lower(s.sentence),
                greatest(1, instr(lower(s.sentence), k.keyword) - 28), 28)
           RLIKE '(plans? to|planned to|upcoming|will be|to be establish|to be set up|being set up|being established|coming soon|opening shortly|sanctioned|to open|set to )'
      THEN 1 ELSE 0 END AS is_aspirational
  FROM sent s
  JOIN kw k ON lower(s.sentence) LIKE concat('%', k.keyword, '%')
),

-- positive (operational) evidence, de-duplicated across fields by norm_key
pos_ranked AS (
  SELECT *,
         row_number() OVER (
           PARTITION BY unique_id, capability_key, norm_key
           ORDER BY weight DESC, field
         ) AS rn
  FROM matches_raw
  WHERE is_aspirational = 0
),
pos_dedup AS (
  SELECT unique_id, capability_key, field, sentence, weight,
    -- Independence buckets: capability/description/specialties are self-reported
    -- narrative (routinely the SAME source text, often verbatim/paraphrased), so
    -- they collapse into ONE bucket. procedure and equipment are structurally
    -- distinct sources. Corroboration = agreement across independent buckets.
    CASE WHEN field IN ('capability','description','specialties') THEN 'narrative' ELSE field END AS bucket
  FROM pos_ranked WHERE rn = 1
),

-- aspirational-only signal, kept aside to annotate gaps / dampen the score
asp_agg AS (
  SELECT unique_id, capability_key,
         count(*) AS n_aspirational,
         max(left(sentence, 200)) AS asp_sample
  FROM matches_raw
  WHERE is_aspirational = 1
  GROUP BY unique_id, capability_key
),

agg AS (
  SELECT
    unique_id,
    capability_key,
    -- corroboration = number of INDEPENDENT evidence buckets (narrative/procedure/equipment), max 3
    count(DISTINCT bucket) AS n_fields_corroborating,
    count(*)      AS n_evidence,       -- distinct de-duplicated sentences
    sum(weight)   AS sum_weight,       -- total evidence mass → effective sample size for the CI
    max(weight)   AS max_weight,
    max(CASE WHEN field = 'equipment' AND weight >= 1.0 THEN 1 ELSE 0 END) AS equip_specific,
    to_json(
      transform(
        slice(
          sort_array(collect_list(named_struct('sortkey', -weight, 'field', field, 'sentence', left(sentence, 300)))),
          1, 8
        ),
        x -> named_struct('field', x.field, 'sentence', x.sentence)
      )
    ) AS evidence_json
  FROM pos_dedup
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
    a.n_evidence,
    a.sum_weight,
    a.max_weight,
    a.equip_specific,
    a.evidence_json,
    c.record_completeness,
    c.numberDoctors           AS number_doctors,
    c.capacity,
    c.source_urls,
    coalesce(asp.n_aspirational, 0) AS n_aspirational,
    asp.asp_sample,
    -- contradiction: surgery-level claim without any anesthesia/OT evidence
    CASE WHEN a.capability_key IN ('surgery','trauma','oncology') AND c.has_anes = 0 THEN 1 ELSE 0 END AS contradiction,
    -- Breadth across independent fields is the dominant driver (a single field can
    -- never be "corroborated"); evidence quality and volume are modest bonuses only.
    greatest(0.0, least(1.0,
        0.60 * least(1.0, a.n_fields_corroborating / 3.0)      -- 1 field=.20, 2=.40, 3+=.60
      + 0.20 * a.max_weight                                    -- best-source quality (.40..1.0)
      + 0.20 * least(1.0, (a.n_evidence - 1) / 4.0)            -- small bonus for extra distinct evidence
      - (CASE WHEN a.capability_key IN ('surgery','trauma','oncology') AND c.has_anes = 0 THEN 0.25 ELSE 0.0 END)
      - (CASE WHEN asp.n_aspirational IS NOT NULL THEN 0.15 ELSE 0.0 END)  -- also has planned/under-construction mentions
    )) AS trust_score,
    c.equip_arr, c.desc_arr, c.ok_doctors, c.ok_capacity, c.ok_coords
  FROM agg a
  JOIN completeness c USING (unique_id)
  LEFT JOIN asp_agg asp USING (unique_id, capability_key)
),

-- ---------------------------------------------------------------------------
-- Uncertainty band (A3). There is no ground truth, so we treat trust_score as a
-- proportion estimate and put a Wilson score interval around it (z = 1.645,
-- ~90%). The effective sample size is the total evidence mass (sum of source
-- weights): a rating built on many high-quality, independent sources gets a
-- TIGHT band (solid); one resting on a single vague claim gets a WIDE band
-- (speculative). This answers the brief's open question — prediction intervals
-- with no ground truth — so a planner can tell solid from speculative.
-- ---------------------------------------------------------------------------
ci AS (
  SELECT s.*,
    greatest(1.0, s.sum_weight) AS n_eff,   -- effective sample size (>=1)
    2.706 AS z2,                             -- z^2 for z = 1.645
    1.645 AS z
  FROM scored s
),
ci2 AS (
  SELECT c.*,
    (1.0 + z2 / n_eff)                                                       AS denom,
    (trust_score + z2 / (2.0 * n_eff))                                       AS num_center,
    sqrt(trust_score * (1.0 - trust_score) / n_eff + z2 / (4.0 * n_eff * n_eff)) AS root
  FROM ci c
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
    CASE WHEN n_aspirational > 0       THEN concat('record also has planned/under-construction wording: "', asp_sample, '"') END,
    CASE WHEN size(equip_arr) = 0      THEN 'no equipment data'   END,
    CASE WHEN ok_doctors  = 0          THEN 'no doctor count'     END,
    CASE WHEN ok_capacity = 0          THEN 'no capacity data'    END,
    CASE WHEN size(desc_arr) = 0       THEN 'no description'      END,
    CASE WHEN ok_coords   = 0          THEN 'no coordinates'      END
  ), x -> x IS NOT NULL)) AS gaps_json,
  round(record_completeness, 3) AS record_completeness,
  round(greatest(0.0, least(trust_score, (num_center - z * root) / denom)), 3) AS trust_score_low,
  round(least(1.0, greatest(trust_score, (num_center + z * root) / denom)), 3) AS trust_score_high,
  number_doctors,
  capacity,
  source_urls
FROM ci2;
