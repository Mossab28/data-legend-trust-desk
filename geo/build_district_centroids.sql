-- build_district_centroids.sql · avg lat/lon per (state, district)
-- (was built ad-hoc during the run; versioned here per docs/JURY_REVIEW.md §1)
-- Keys are lowercase to join district_coverage. Feeds the deserts map.
CREATE OR REPLACE TABLE workspace.default.district_centroids AS
SELECT lower(trim(statename)) AS statename,
       lower(trim(district))  AS district,
       avg(try_cast(latitude  AS DOUBLE)) AS lat,
       avg(try_cast(longitude AS DOUBLE)) AS lon
FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.india_post_pincode_directory
WHERE try_cast(latitude  AS DOUBLE) BETWEEN 6 AND 37.5
  AND try_cast(longitude AS DOUBLE) BETWEEN 68 AND 97.5
GROUP BY 1, 2;
