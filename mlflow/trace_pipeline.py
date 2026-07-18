"""A4 · MLflow 3 tracing for the Trust Engine (workstream A).

Replays the trust pipeline as an MLflow **trace** — one span per reasoning step
(extract claims -> score trust -> rank by capability -> self-validate) — plus an
MLflow run holding the scoring parameters and headline metrics. This is the
"show your receipts" layer: the jury (and the app's "How was this computed?"
button) can open the trace and watch the evidence engine think.

Auth: uses the `hackathon` Databricks profile from ~/.databrickscfg. Traces and
the run are logged to an MLflow experiment in your Databricks workspace.

Usage (from repo root, venv active):
    python mlflow/trace_pipeline.py            # read-only: trace current tables
    python mlflow/trace_pipeline.py --rebuild  # execute the SQL builds inside spans (traced rebuild)
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import mlflow
from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

PROFILE = os.getenv("DATABRICKS_CONFIG_PROFILE", "hackathon")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "04ab03ef1a2d183f")
REPO_ROOT = Path(__file__).resolve().parent.parent

CAPABILITIES = ["icu", "nicu", "maternity", "emergency", "oncology", "trauma", "dialysis", "surgery"]

# Scoring parameters (kept in sync with pipeline/build_facility_trust.sql) — logged
# so every trace records exactly which policy produced these numbers.
SCORING_PARAMS = {
    "weight_field_breadth": 0.60,
    "weight_best_source": 0.20,
    "weight_volume": 0.20,
    "penalty_contradiction": 0.25,
    "penalty_aspirational": 0.15,
    "corroborated_min_buckets": 2,
    "corroborated_min_score": 0.60,
    "unknown_completeness_below": 0.35,
    "ci_z": 1.645,
    "independence_buckets": "narrative(capability+description+specialties) | procedure | equipment",
}


def get_config() -> Config:
    return Config(profile=PROFILE)


def connect(cfg: Config):
    return sql.connect(
        server_hostname=cfg.host.replace("https://", "").rstrip("/"),
        http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
        access_token=cfg.token,
    )


def q_all(cur, query: str):
    cur.execute(query)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def q_one(cur, query: str):
    rows = q_all(cur, query)
    return rows[0] if rows else {}


# ---------------------------------------------------------------------------
# Traced stages
# ---------------------------------------------------------------------------

def span_extract(cur) -> dict:
    with mlflow.start_span(name="1_extract_claims") as s:
        s.set_inputs({
            "source": "databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities",
            "claim_fields": ["capability", "procedure", "equipment", "description", "specialties"],
        })
        row = q_one(cur, """
            SELECT
              (SELECT count(*) FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities) AS n_facilities,
              (SELECT count(*) FROM workspace.default.facility_trust)                                                    AS n_capability_claims,
              (SELECT count(DISTINCT unique_id) FROM workspace.default.facility_trust)                                   AS n_facilities_with_claims
        """)
        out = {k: int(v) for k, v in row.items()}
        s.set_outputs(out)
        return out


def span_score(cur) -> dict:
    with mlflow.start_span(name="2_score_trust") as s:
        s.set_inputs({"policy": SCORING_PARAMS})
        dist = q_all(cur, """
            SELECT trust_state,
                   count(*)                                   AS n,
                   round(avg(trust_score), 3)                 AS avg_score,
                   round(avg(trust_score - trust_score_low), 3) AS avg_band_width
            FROM workspace.default.facility_trust
            GROUP BY trust_state ORDER BY n DESC
        """)
        out = {r["trust_state"]: {"n": int(r["n"]), "avg_score": float(r["avg_score"]),
                                  "avg_band_width": float(r["avg_band_width"])} for r in dist}
        s.set_outputs(out)
        return out


def span_rank(cur) -> dict:
    top_by_cap = {}
    with mlflow.start_span(name="3_rank_by_capability") as parent:
        parent.set_inputs({"capabilities": CAPABILITIES})
        for cap in CAPABILITIES:
            with mlflow.start_span(name=f"rank_{cap}") as cs:
                cs.set_inputs({"capability": cap})
                cs.set_attribute("capability", cap)
                top = q_one(cur, f"""
                    SELECT name, city, trust_state,
                           round(trust_score,3)      AS trust_score,
                           round(trust_score_low,3)  AS trust_score_low,
                           round(trust_score_high,3) AS trust_score_high,
                           n_fields_corroborating,
                           left(evidence_json, 400)  AS evidence
                    FROM workspace.default.facility_trust
                    WHERE capability_key = '{cap}'
                    ORDER BY CASE trust_state WHEN 'CORROBORATED' THEN 0 WHEN 'CLAIMED_ONLY' THEN 1 ELSE 2 END,
                             trust_score DESC, name
                    LIMIT 1
                """)
                cs.set_outputs(top)
                top_by_cap[cap] = top.get("name")
        parent.set_outputs(top_by_cap)
    return top_by_cap


def span_validate(cur) -> dict:
    with mlflow.start_span(name="4_self_validate") as s:
        rows = q_all(cur, """
            SELECT code, count(*) AS n,
                   sum(CASE WHEN disagrees_with_score THEN 1 ELSE 0 END) AS n_disagreeing
            FROM workspace.default.trust_validations GROUP BY code ORDER BY n DESC
        """)
        total = q_one(cur, """
            SELECT count(*) AS total,
                   sum(CASE WHEN disagrees_with_score THEN 1 ELSE 0 END) AS disagreeing,
                   count(DISTINCT unique_id) AS facilities
            FROM workspace.default.trust_validations
        """)
        out = {
            "by_code": {r["code"]: {"n": int(r["n"]), "disagreeing": int(r["n_disagreeing"] or 0)} for r in rows},
            "total_findings": int(total.get("total", 0) or 0),
            "findings_disagreeing_with_score": int(total.get("disagreeing", 0) or 0),
            "facilities_flagged": int(total.get("facilities", 0) or 0),
        }
        s.set_outputs(out)
        return out


def maybe_rebuild(cur, do_rebuild: bool):
    """Optionally execute the SQL builds inside spans, so the trace covers a real rebuild."""
    if not do_rebuild:
        return
    for step, rel in [("build_facility_trust", "pipeline/build_facility_trust.sql"),
                      ("build_trust_validations", "pipeline/build_trust_validations.sql")]:
        stmt = (REPO_ROOT / rel).read_text()
        with mlflow.start_span(name=f"rebuild_{step}") as s:
            s.set_inputs({"sql_file": rel})
            t0 = time.time()
            cur.execute(stmt)
            s.set_outputs({"elapsed_s": round(time.time() - t0, 1)})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="execute the SQL builds inside the trace")
    args = ap.parse_args()

    cfg = get_config()
    # Point MLflow at the Databricks workspace tracking server.
    os.environ["DATABRICKS_HOST"] = cfg.host
    os.environ["DATABRICKS_TOKEN"] = cfg.token
    mlflow.set_tracking_uri("databricks")

    me = WorkspaceClient(config=cfg).current_user.me().user_name
    experiment_path = f"/Users/{me}/trust-engine"
    mlflow.set_experiment(experiment_path)

    with connect(cfg) as conn, conn.cursor() as cur:
        with mlflow.start_run(run_name=f"trust-rebuild-{time.strftime('%Y%m%d-%H%M%S')}") as run:
            mlflow.log_params(SCORING_PARAMS)
            with mlflow.start_span(name="trust_engine") as root:
                root.set_inputs({"warehouse_id": WAREHOUSE_ID, "rebuild": args.rebuild})
                maybe_rebuild(cur, args.rebuild)
                extracted = span_extract(cur)
                scored = span_score(cur)
                ranked = span_rank(cur)
                validated = span_validate(cur)
                root.set_outputs({
                    "extracted": extracted,
                    "trust_states": {k: v["n"] for k, v in scored.items()},
                    "top_facilities": ranked,
                    "validator": {"total": validated["total_findings"],
                                  "disagreeing": validated["findings_disagreeing_with_score"]},
                })

            # Headline numeric metrics on the run.
            for state, v in scored.items():
                mlflow.log_metric(f"n_{state}", v["n"])
                mlflow.log_metric(f"avg_score_{state}", v["avg_score"])
                mlflow.log_metric(f"avg_band_width_{state}", v["avg_band_width"])
            mlflow.log_metric("validator_findings", validated["total_findings"])
            mlflow.log_metric("validator_disagreements", validated["findings_disagreeing_with_score"])
            mlflow.log_metric("facilities_with_claims", extracted["n_facilities_with_claims"])

            run_id = run.info.run_id
            exp_id = run.info.experiment_id

    print("\n=== MLflow trace logged ===")
    print(f"experiment: {experiment_path}  (id={exp_id})")
    print(f"run_id:     {run_id}")
    print(f"Traces UI:  {cfg.host}/ml/experiments/{exp_id}/traces")
    print(f"Run UI:     {cfg.host}/ml/experiments/{exp_id}/runs/{run_id}")


if __name__ == "__main__":
    main()
