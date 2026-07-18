-- =============================================================================
-- build_trust_validations.sql  ·  Self-Correction Validator (workstream A · feat/a-validator)
--
-- An INDEPENDENT audit pass. It reads the finished workspace.default.facility_trust
-- (the scorer's output) plus the raw source, and emits one row per finding into
-- workspace.default.trust_validations. Some findings deliberately DISAGREE with the
-- scorer ("we said CORROBORATED, but this is internally inconsistent") — that is the
-- point: the app double-checks its own work (Evidence & Trust, 35%).
--
-- Rules:
--   SHARED_EVIDENCE        the "proof" for this capability is duplicated verbatim across
--                          many other facilities (extraction/boilerplate contamination) —
--                          low-specificity, should not count as facility-specific corroboration.
--   UNSUPPORTED_SURGERY    surgery/trauma/oncology scored CORROBORATED, yet the record has
--                          zero anesthesia / operating-theatre evidence anywhere.
--   CAPACITY_WITHOUT_STAFF a large declared bed capacity with no doctors listed — capacity
--                          may be unstaffed or a data-entry error.
--
-- Idempotent: CREATE OR REPLACE. Read-only w.r.t. the source and facility_trust.
-- =============================================================================

CREATE OR REPLACE TABLE workspace.default.trust_validations AS
WITH
-- Per-facility structured facts from the raw source ---------------------------
facts AS (
  SELECT
    unique_id,
    name,
    try_cast(regexp_extract(regexp_replace(coalesce(capacity,''), ',', ''),      '([0-9]{1,6})', 1) AS int) AS cap_num,
    try_cast(regexp_extract(regexp_replace(coalesce(numberDoctors,''), ',', ''), '([0-9]{1,6})', 1) AS int) AS doc_num,
    lower(concat_ws(' ', coalesce(equipment,''), coalesce(`procedure`,''), coalesce(description,''))) AS surg_blob
  FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
),

-- Global corpus of evidence sentences, to detect verbatim boilerplate ----------
corpus AS (
  SELECT
    unique_id,
    regexp_replace(lower(trim(left(s, 300))), '[^a-z0-9]', '') AS nk
  FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
  LATERAL VIEW explode(
    concat(
      coalesce(from_json(capability, 'array<string>'), array()),
      coalesce(from_json(`procedure`, 'array<string>'), array()),
      coalesce(from_json(equipment,  'array<string>'), array())
    )
  ) t AS s
  WHERE length(trim(s)) >= 45   -- only long, specific sentences can be "plagiarised"
),
shared AS (
  SELECT nk, count(DISTINCT unique_id) AS mult
  FROM corpus
  GROUP BY nk
  HAVING count(DISTINCT unique_id) >= 4   -- same long sentence on >= 4 facilities = boilerplate
),

-- The evidence that actually drove each (facility, capability) trust score ------
ft_ev AS (
  SELECT
    t.unique_id,
    t.capability_key,
    t.trust_state,
    regexp_replace(lower(trim(ev.sentence)), '[^a-z0-9]', '') AS nk
  FROM workspace.default.facility_trust t
  LATERAL VIEW explode(
    from_json(t.evidence_json, 'array<struct<field:string,sentence:string>>')
  ) e AS ev
),
ev_shared AS (
  SELECT
    f.unique_id,
    f.capability_key,
    f.trust_state,
    count(*)                                        AS n_ev,
    sum(CASE WHEN s.nk IS NOT NULL THEN 1 ELSE 0 END) AS n_shared,
    max(s.mult)                                     AS max_mult
  FROM ft_ev f
  LEFT JOIN shared s ON f.nk = s.nk
  GROUP BY f.unique_id, f.capability_key, f.trust_state
)

-- ============================ FINDINGS ======================================
-- SHARED_EVIDENCE ------------------------------------------------------------
SELECT
  unique_id,
  capability_key,
  'SHARED_EVIDENCE' AS code,
  CASE WHEN n_shared * 2 >= n_ev THEN 'warning' ELSE 'info' END AS severity,
  concat(cast(n_shared AS string), ' of ', cast(n_ev AS string),
         ' evidence sentences are duplicated across other facilities (one appears on up to ',
         cast(max_mult AS string),
         ' facilities) — likely boilerplate, not facility-specific proof.') AS message,
  (trust_state = 'CORROBORATED' AND n_shared * 2 >= n_ev) AS disagrees_with_score,
  to_json(named_struct('n_shared', n_shared, 'n_evidence', n_ev, 'max_facilities', max_mult)) AS detail_json
FROM ev_shared
WHERE n_shared >= 1

UNION ALL
-- UNSUPPORTED_SURGERY --------------------------------------------------------
SELECT
  t.unique_id,
  t.capability_key,
  'UNSUPPORTED_SURGERY' AS code,
  'warning' AS severity,
  concat('Scored ', t.trust_state, ' for ', t.capability_key,
         ', but no anesthesia / operating-theatre evidence appears anywhere in the record.') AS message,
  (t.trust_state = 'CORROBORATED') AS disagrees_with_score,
  to_json(named_struct('capability', t.capability_key, 'trust_state', t.trust_state)) AS detail_json
FROM workspace.default.facility_trust t
JOIN facts f ON t.unique_id = f.unique_id
WHERE t.capability_key IN ('surgery', 'trauma', 'oncology')
  AND t.trust_state = 'CORROBORATED'
  AND f.surg_blob NOT RLIKE 'anesthes|anaesthes|operating theat|operation theat|ot complex'

UNION ALL
-- CAPACITY_WITHOUT_STAFF (facility-level: capability_key = NULL) --------------
SELECT
  f.unique_id,
  CAST(NULL AS string) AS capability_key,
  'CAPACITY_WITHOUT_STAFF' AS code,
  CASE WHEN f.cap_num > 2000 THEN 'warning' ELSE 'info' END AS severity,
  concat('Declares a ', cast(f.cap_num AS string),
         '-bed capacity but lists no doctors — capacity may be unstaffed or a data-entry error.') AS message,
  false AS disagrees_with_score,
  to_json(named_struct('capacity', f.cap_num, 'doctors', coalesce(f.doc_num, 0))) AS detail_json
FROM facts f
WHERE f.cap_num > 1000 AND (f.doc_num IS NULL OR f.doc_num = 0);
