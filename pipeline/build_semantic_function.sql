-- =============================================================================
-- build_semantic_function.sql  ·  A5 · Semantic search SQL function
-- Table-valued UDF the app can call directly from SQL:
--     SELECT * FROM workspace.default.semantic_facilities('cardiac cath lab');
-- Embeds the query once (single-row CTE), then ranks all facilities by dot
-- product against the pre-normalised profile embeddings. Returns the top 50.
-- Requires workspace.default.facility_semantic (build_semantic_index.sql).
-- =============================================================================

CREATE OR REPLACE FUNCTION workspace.default.semantic_facilities(query STRING)
RETURNS TABLE(
  unique_id STRING, name STRING, city STRING, state STRING,
  latitude DOUBLE, longitude DOUBLE, profile_snippet STRING, similarity DOUBLE
)
RETURN
  WITH qraw AS (
    SELECT ai_query('databricks-gte-large-en', query) AS emb
  ),
  q AS (
    SELECT transform(
             emb,
             x -> x / sqrt(greatest(1e-12, aggregate(transform(emb, y -> y * y), CAST(0 AS DOUBLE), (a, b) -> a + b)))
           ) AS qv
    FROM qraw
  )
  SELECT
    f.unique_id, f.name, f.city, f.state, f.latitude, f.longitude,
    substr(f.profile_text, 1, 240) AS profile_snippet,
    aggregate(zip_with(f.embedding, q.qv, (a, b) -> a * b), CAST(0 AS DOUBLE), (acc, x) -> acc + x) AS similarity
  FROM workspace.default.facility_semantic f, q
  ORDER BY similarity DESC
  LIMIT 50;
