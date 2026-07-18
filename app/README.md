# Facility Trust Desk — Databricks App (Streamlit)

Streamlit app for the Facility Trust Desk track. Reads
`workspace.default.facility_trust`, writes `workspace.default.planner_actions`
(see `../docs/CONTRACT.md`).

## Run locally

Requires a Databricks profile in `~/.databrickscfg` (the app authenticates via
`databricks.sdk.core.Config`, so locally it picks up your default profile).

```bash
cd app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABRICKS_WAREHOUSE_ID=af2489ada308a769   # optional, this is the default
streamlit run app.py
```

## Deploy as a Databricks App

```bash
# from the repo root
databricks apps create facility-trust-desk            # first time only
databricks sync ./app /Workspace/Users/<you>/facility-trust-desk
databricks apps deploy facility-trust-desk \
  --source-code-path /Workspace/Users/<you>/facility-trust-desk
```

Then in the App's UI (Compute → Apps → facility-trust-desk):

1. Add a **SQL warehouse** resource pointing at warehouse `af2489ada308a769`
   (or edit `DATABRICKS_WAREHOUSE_ID` in `app.yaml`).
2. Grant the app's **service principal**:
   - `SELECT` on `workspace.default.facility_trust`
   - `ALL PRIVILEGES` (or `SELECT` + `MODIFY` + `CREATE TABLE` on the schema)
     for `workspace.default.planner_actions` — the app creates this table on
     first launch if it doesn't exist.

The app degrades gracefully if `facility_trust` doesn't exist yet
("pipeline not run yet" message) — safe to deploy before the pipeline runs.

## Files

- `app.py` — the whole app (single file)
- `app.yaml` — Databricks Apps config (command + env)
- `requirements.txt` — Python deps
