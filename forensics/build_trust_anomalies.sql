-- build_trust_anomalies.sql · Workstream B "Trust Forensics"
-- Two data-quality alarms (duplicate-text detection lives in trust_validations) the trust score alone cannot see. One row per
-- (facility, anomaly_type). Planner-facing wording lives in the app; this
-- table only carries facts. Replayable (CREATE OR REPLACE). Scope anchors:
--   * "flags suspicious or incomplete data" (brief, Trust Scorer core req.)
--   * "Claims vs Evidence" + "Data Desert" research areas
-- =============================================================================
CREATE OR REPLACE TABLE workspace.default.trust_anomalies AS
WITH fac AS (
  SELECT unique_id, name,
         latitude, longitude,
         regexp_extract(trim(address_zipOrPostcode), '([1-9][0-9]{5})', 1) AS pin6,
         equipment, procedure,
         recency_of_page_update,
         post_metrics_most_recent_social_media_post_date,
         engagement_metrics_n_followers,
         distinct_social_media_presence_count
  FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
),
pin_centroids AS (
  SELECT pincode,
         avg(try_cast(latitude  AS DOUBLE)) AS plat,
         avg(try_cast(longitude AS DOUBLE)) AS plon
  FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.india_post_pincode_directory
  WHERE try_cast(latitude AS DOUBLE)  BETWEEN 6 AND 37.5
    AND try_cast(longitude AS DOUBLE) BETWEEN 68 AND 97.5
  GROUP BY pincode
),

-- 1) GEO_MISMATCH: stated pincode and GPS disagree by > 100 km,
--    or GPS falls outside any plausible India bounding box.
geo AS (
  SELECT f.unique_id, f.name,
         'GEO_MISMATCH' AS anomaly_type,
         CASE
           WHEN f.latitude NOT BETWEEN 6 AND 37.5
             OR f.longitude NOT BETWEEN 68 AND 97.5
           THEN concat('GPS (', round(f.latitude,3), ', ', round(f.longitude,3),
                       ') falls outside India entirely')
           ELSE concat('GPS is ',
                       cast(round(2*6371*asin(sqrt(
                         pow(sin(radians(f.latitude - p.plat)/2),2)
                         + cos(radians(p.plat))*cos(radians(f.latitude))
                         * pow(sin(radians(f.longitude - p.plon)/2),2)))) AS INT),
                       ' km from the PIN code it declares (', f.pin6, ')')
         END AS detail
  FROM fac f
  JOIN pin_centroids p
    ON try_cast(f.pin6 AS BIGINT) = try_cast(p.pincode AS BIGINT)
   AND f.pin6 <> ''
  WHERE f.latitude IS NOT NULL AND f.longitude IS NOT NULL
    AND f.latitude <> 0 AND f.longitude <> 0
    AND (
      f.latitude NOT BETWEEN 6 AND 37.5
      OR f.longitude NOT BETWEEN 68 AND 97.5
      OR 2*6371*asin(sqrt(
           pow(sin(radians(f.latitude - p.plat)/2),2)
           + cos(radians(p.plat))*cos(radians(f.latitude))
           * pow(sin(radians(f.longitude - p.plon)/2),2))) > 100
    )
),


-- 2) DIGITALLY_SILENT: claims a critical capability but shows no digital
--    sign of life (no social presence, page not updated since 2024).
silent AS (
  SELECT DISTINCT f.unique_id, f.name,
         'DIGITALLY_SILENT' AS anomaly_type,
         concat('Claims ', t.capability_key,
                ' but no social presence and page last updated ',
                coalesce(nullif(nullif(f.recency_of_page_update,''),'nan'),
                         'unknown')) AS detail
  FROM fac f
  JOIN workspace.default.facility_trust t ON f.unique_id = t.unique_id
  WHERE t.capability_key IN ('icu','nicu','emergency','trauma')
    AND coalesce(nullif(nullif(f.distinct_social_media_presence_count,''),'nan'),'0')
        IN ('0','null')
    AND (f.recency_of_page_update IS NULL
         OR f.recency_of_page_update IN ('','nan','null')
         OR try_cast(f.recency_of_page_update AS DATE) < DATE'2024-01-01')
)

SELECT * FROM geo
UNION ALL SELECT * FROM silent;
