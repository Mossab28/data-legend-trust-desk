"""A5 · Semantic capability search (workstream A) — CLI / demo wrapper.

Free-text search over facility capability profiles that goes BEYOND the 8 fixed
capability keys (e.g. "cardiac cath lab", "burns unit", "IVF"). Uses the
in-warehouse semantic index (workspace.default.facility_semantic) and the
foundation embedding model `databricks-gte-large-en` via ai_query — no Vector
Search endpoint required (none exists on Free Edition).

Primary interface for the app is the SQL function:
    SELECT * FROM workspace.default.semantic_facilities('cardiac cath lab');

This wrapper adds an optional trust overlay (join facility_trust for one of the
8 scored capabilities) for demo and CLI use.

Usage (venv active):
    python scripts/semantic_search.py "cardiac catheterization lab" --k 8
    python scripts/semantic_search.py "neonatal intensive care" --capability nicu --k 8
"""

from __future__ import annotations

import argparse
import os

from databricks import sql
from databricks.sdk.core import Config

PROFILE = os.getenv("DATABRICKS_CONFIG_PROFILE", "hackathon")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "04ab03ef1a2d183f")


def connect():
    cfg = Config(profile=PROFILE)
    return sql.connect(
        server_hostname=cfg.host.replace("https://", "").rstrip("/"),
        http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
        access_token=cfg.token,
    )


def search(query: str, k: int = 10, capability: str | None = None):
    """Return top-k semantically matching facilities, optionally with trust for `capability`."""
    with connect() as conn, conn.cursor() as cur:
        if capability:
            cur.execute("""
                SELECT s.name, s.city, s.state, round(s.similarity, 3) AS similarity,
                       t.trust_state, round(t.trust_score, 3) AS trust_score,
                       s.profile_snippet
                FROM workspace.default.semantic_facilities(%(q)s) s
                LEFT JOIN workspace.default.facility_trust t
                       ON t.unique_id = s.unique_id AND t.capability_key = %(cap)s
                ORDER BY s.similarity DESC
                LIMIT %(k)s
            """, {"q": query, "cap": capability, "k": k})
        else:
            cur.execute("""
                SELECT name, city, state, round(similarity, 3) AS similarity, profile_snippet
                FROM workspace.default.semantic_facilities(%(q)s)
                ORDER BY similarity DESC
                LIMIT %(k)s
            """, {"q": query, "k": k})
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="free-text capability query")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--capability", help="overlay trust for one of the 8 scored capabilities")
    args = ap.parse_args()

    rows = search(args.query, k=args.k, capability=args.capability)
    print(f"\nTop {len(rows)} for: “{args.query}”" + (f"  ·  trust for {args.capability}" if args.capability else ""))
    print("-" * 72)
    for r in rows:
        line = f"{r['similarity']:.3f}  {r['name']} — {r['city']}, {r['state']}"
        if args.capability and r.get("trust_state"):
            line += f"  [{r['trust_state']} {r.get('trust_score')}]"
        print(line)
        print(f"        {r['profile_snippet'][:120]}…")


if __name__ == "__main__":
    main()
