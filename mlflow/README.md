# A4 · MLflow 3 Tracing — "Show your receipts"

The trust engine is not a black box. Every rebuild is replayed as an **MLflow 3
trace**: one span per reasoning step, so the jury (and the app's *"How was this
computed?"* button) can open a trace and watch the evidence engine think —
extraction → scoring → ranking → self-validation — with the inputs and outputs
of each step attached.

## What gets traced

A single trace (`trust_engine`) with nested spans:

| Span | Inputs | Outputs |
|------|--------|---------|
| `1_extract_claims` | source table, claim fields parsed | # facilities, # capability claims, # facilities with claims |
| `2_score_trust` | full scoring policy (weights, penalties, thresholds) | per-`trust_state` counts, avg score, avg uncertainty-band width |
| `3_rank_by_capability` | list of capabilities | top facility per capability |
| ↳ `rank_<capability>` (×8) | one capability | best facility + trust score + CI + evidence snippet |
| `4_self_validate` | — | validator findings by code, # disagreeing with the score |

The companion **MLflow run** logs the scoring parameters (`log_params`) and the
headline metrics (`log_metrics`: counts per trust state, avg score, band width,
validator findings/disagreements) so runs are comparable across policy changes.

## Why it matters (Hack-Nation scoring)

- **Agentic Traceability (stretch goal):** the trace *is* the audit trail of the
  reasoning steps, with receipts at each node.
- **Evidence & Trust:** parameters + metrics are versioned per rebuild, so any
  score is reproducible and every policy tweak is measurable.
- **Reliability:** compare two runs to see exactly how a threshold change moved
  the CORROBORATED/CLAIMED/UNKNOWN mix.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r mlflow/requirements.txt

# read-only: trace the current tables
DATABRICKS_CONFIG_PROFILE=hackathon python mlflow/trace_pipeline.py

# traced rebuild: execute the SQL builds inside spans
DATABRICKS_CONFIG_PROFILE=hackathon python mlflow/trace_pipeline.py --rebuild
```

Auth uses the `hackathon` profile in `~/.databrickscfg`. Override the warehouse
with `DATABRICKS_WAREHOUSE_ID` if needed. The script prints the **Traces UI** and
**Run UI** URLs at the end.

## App integration (for workstream B)

The *"How was this computed?"* button can:
1. Deep-link to the latest trace: `${host}/ml/experiments/${exp_id}/traces`, or
2. Query the same receipts the trace shows: `evidence_json` +
   `n_fields_corroborating` + `trust_score_low/high` from `facility_trust`, and
   the matching rows in `trust_validations`.

The script prints `experiment id` / `run id` on every run; store the latest to
drive the deep-link.
