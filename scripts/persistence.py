"""A6 · Planner-actions persistence — Lakebase (primary) with Delta fallback.

The app records planner actions (override / note / shortlist). This module gives
it ONE interface (`PlannerActionsStore`) backed by two stores:

  1. **Lakebase** (managed Postgres OLTP, instance `trust-desk-oltp`) — the right
     tool for small, frequent, transactional writes with row-level upserts. Auth
     uses a short-lived Databricks OAuth credential (`generate_database_credential`)
     as the Postgres password; no static secret is stored.
  2. **Delta** (`workspace.default.planner_actions` via the SQL warehouse) — the
     fallback, used automatically when the Lakebase endpoint is unreachable.

Why a fallback: Lakebase instance endpoints are only reachable from inside the
Databricks network (a Databricks App can reach them; a local laptop cannot). The
store probes Lakebase with a short timeout and transparently falls back to Delta,
so the app works everywhere. `store.backend` reports which one is live.

Interface (stable — see docs/CONTRACT.md):
    store = PlannerActionsStore()
    store.write_action(unique_id, action_type, capability_key=..., planner=..., new_state=..., note=...)
    store.list_actions(unique_id=None) -> list[dict]
"""

from __future__ import annotations

import datetime as dt
import os
import uuid

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

PROFILE = os.getenv("DATABRICKS_CONFIG_PROFILE", "hackathon")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "04ab03ef1a2d183f")
LAKEBASE_INSTANCE = os.getenv("LAKEBASE_INSTANCE", "trust-desk-oltp")
LAKEBASE_DB = os.getenv("LAKEBASE_DB", "databricks_postgres")
LAKEBASE_CONNECT_TIMEOUT = int(os.getenv("LAKEBASE_CONNECT_TIMEOUT", "8"))
DELTA_TABLE = "workspace.default.planner_actions"

FIELDS = ["action_id", "ts", "planner", "unique_id", "capability_key",
          "action_type", "new_state", "note"]


class PlannerActionsStore:
    def __init__(self, prefer_lakebase: bool = True):
        self._cfg = Config(profile=PROFILE)
        self._w = WorkspaceClient(config=self._cfg)
        self.backend = None
        self._pg = None
        if prefer_lakebase:
            self._pg = self._try_lakebase()
            self.backend = "lakebase" if self._pg else None
        if self.backend is None:
            self._ensure_delta()
            self.backend = "delta"

    # ---- Lakebase -------------------------------------------------------
    def _try_lakebase(self):
        try:
            import psycopg
            inst = self._w.database.get_database_instance(name=LAKEBASE_INSTANCE)
            cred = self._w.database.generate_database_credential(
                request_id=str(uuid.uuid4()), instance_names=[LAKEBASE_INSTANCE])
            conn = psycopg.connect(
                host=inst.read_write_dns, port=5432, dbname=LAKEBASE_DB,
                user=self._w.current_user.me().user_name, password=cred.token,
                sslmode="require", connect_timeout=LAKEBASE_CONNECT_TIMEOUT,
            )
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS planner_actions (
                        action_id TEXT PRIMARY KEY,
                        ts TIMESTAMPTZ DEFAULT now(),
                        planner TEXT,
                        unique_id TEXT NOT NULL,
                        capability_key TEXT,
                        action_type TEXT NOT NULL,
                        new_state TEXT,
                        note TEXT
                    )
                """)
            conn.commit()
            return conn
        except Exception:
            return None  # unreachable / not provisioned → caller falls back to Delta

    # ---- Delta ----------------------------------------------------------
    def _sql_conn(self):
        from databricks import sql
        return sql.connect(
            server_hostname=self._cfg.host.replace("https://", "").rstrip("/"),
            http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
            access_token=self._cfg.token,
        )

    def _ensure_delta(self):
        with self._sql_conn() as c, c.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {DELTA_TABLE} (
                  action_id STRING, ts TIMESTAMP, planner STRING, unique_id STRING,
                  capability_key STRING, action_type STRING, new_state STRING, note STRING
                ) USING DELTA
            """)

    # ---- Public API -----------------------------------------------------
    def write_action(self, unique_id, action_type, capability_key=None,
                     planner=None, new_state=None, note=None) -> dict:
        rec = {
            "action_id": str(uuid.uuid4()),
            "ts": dt.datetime.now(dt.timezone.utc),
            "planner": planner, "unique_id": unique_id,
            "capability_key": capability_key, "action_type": action_type,
            "new_state": new_state, "note": note,
        }
        if self.backend == "lakebase":
            with self._pg.cursor() as cur:
                cur.execute("""
                    INSERT INTO planner_actions
                      (action_id, ts, planner, unique_id, capability_key, action_type, new_state, note)
                    VALUES (%(action_id)s,%(ts)s,%(planner)s,%(unique_id)s,%(capability_key)s,
                            %(action_type)s,%(new_state)s,%(note)s)
                    ON CONFLICT (action_id) DO NOTHING
                """, rec)
            self._pg.commit()
        else:
            with self._sql_conn() as c, c.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {DELTA_TABLE}
                      (action_id, ts, planner, unique_id, capability_key, action_type, new_state, note)
                    VALUES (%(action_id)s, current_timestamp(), %(planner)s, %(unique_id)s,
                            %(capability_key)s, %(action_type)s, %(new_state)s, %(note)s)
                """, {k: rec[k] for k in rec if k != "ts"})
        return rec

    def list_actions(self, unique_id=None) -> list[dict]:
        if self.backend == "lakebase":
            where = "WHERE unique_id = %(uid)s" if unique_id else ""
            with self._pg.cursor() as cur:
                cur.execute(f"SELECT {', '.join(FIELDS)} FROM planner_actions {where} ORDER BY ts",
                            {"uid": unique_id})
                rows = cur.fetchall()
                return [dict(zip(FIELDS, r)) for r in rows]
        else:
            where = "WHERE unique_id = %(uid)s" if unique_id else ""
            with self._sql_conn() as c, c.cursor() as cur:
                cur.execute(f"SELECT {', '.join(FIELDS)} FROM {DELTA_TABLE} {where} ORDER BY ts",
                            {"uid": unique_id} if unique_id else {})
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, r)) for r in cur.fetchall()]


if __name__ == "__main__":
    store = PlannerActionsStore()
    print(f"[persistence] active backend: {store.backend}")
    rec = store.write_action(
        unique_id="06bdf654-fc15-49eb-89c5-e3c14010ebe1", action_type="shortlist",
        capability_key="icu", planner="Léo", note="persistence smoke test")
    print("wrote:", rec["action_id"])
    acts = store.list_actions(unique_id="06bdf654-fc15-49eb-89c5-e3c14010ebe1")
    print(f"read {len(acts)} action(s) for facility; latest: {acts[-1]['action_type']} by {acts[-1]['planner']}")
