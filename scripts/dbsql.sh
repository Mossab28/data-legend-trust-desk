#!/usr/bin/env bash
# Run a SQL statement against the Databricks SQL warehouse and print results as JSON.
# Usage: ./dbsql.sh "SELECT 1"
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
WID="${DB_WAREHOUSE_ID:-af2489ada308a769}"
SQL="$1"
databricks api post /api/2.0/sql/statements --json "{
  \"warehouse_id\": \"$WID\",
  \"statement\": $(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$SQL"),
  \"wait_timeout\": \"30s\",
  \"format\": \"JSON_ARRAY\"
}"
