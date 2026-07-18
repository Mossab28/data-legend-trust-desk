-- =============================================================================
-- build_planner_actions.sql  ·  A6 · Delta fallback for planner actions
-- The primary store for planner actions is Lakebase (managed Postgres OLTP,
-- instance `trust-desk-oltp`) — see scripts/persistence.py. This Delta table is
-- the fallback used when the Lakebase endpoint is unreachable (e.g. local dev:
-- Lakebase endpoints are only reachable from within the Databricks network).
-- Schema matches docs/CONTRACT.md · planner_actions.
-- =============================================================================

CREATE TABLE IF NOT EXISTS workspace.default.planner_actions (
  action_id      STRING,
  ts             TIMESTAMP,
  planner        STRING,
  unique_id      STRING,
  capability_key STRING,
  action_type    STRING,
  new_state      STRING,
  note           STRING
) USING DELTA;
