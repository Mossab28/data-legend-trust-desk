-- build_facility_geo.sql · clean state/district mapping per facility
-- (was built ad-hoc during the run; versioned here per docs/JURY_REVIEW.md §1)
-- One row per facility that has a parseable 6-digit PIN found in the India
-- Post directory. state_clean/district are Initcap-normalized. The app's
-- main screen (state dropdown) reads this table — build it right after
-- facility_trust on a fresh workspace.
CREATE OR REPLACE TABLE workspace.default.facility_geo AS
WITH pins AS (
  SELECT pincode,
         max(named_struct(
           's', initcap(lower(trim(statename))),
           'd', initcap(lower(trim(district))))) AS sd
  FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.india_post_pincode_directory
  GROUP BY pincode
),
fac AS (
  SELECT unique_id,
         regexp_extract(trim(address_zipOrPostcode), '([1-9][0-9]{5})', 1) AS pin6
  FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
)
SELECT f.unique_id, p.sd.s AS state_clean, p.sd.d AS district
FROM fac f
JOIN pins p ON try_cast(f.pin6 AS BIGINT) = try_cast(p.pincode AS BIGINT)
WHERE f.pin6 <> '';
