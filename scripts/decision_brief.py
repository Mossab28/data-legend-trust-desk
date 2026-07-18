"""A7 · Decision Brief generator (workstream A).

Turns a shortlist of facilities into an exportable, evidence-cited **Decision
Brief** — the literal artifact the brief asks for: "a decision I'm saving for my
team". For each shortlisted (facility × capability) it assembles:

  - the trust verdict with its uncertainty band (conservative floor → ceiling),
  - the exact evidence sentences that justify it (verbatim, with source field),
  - the gaps / missing evidence,
  - the self-validator's findings (esp. any that DISAGREE with the score),
  - any human overrides / notes the planner recorded (from planner_actions),

and renders a clean Markdown report the app can display and offer as a download.

Auth: `hackathon` Databricks profile from ~/.databrickscfg.

Usage (from repo root, venv active):
    # explicit shortlist, one capability
    python scripts/decision_brief.py --ids id1,id2,id3 --capability icu --planner "Léo"

    # pull the current shortlist from planner_actions (action_type='shortlist')
    python scripts/decision_brief.py --from-shortlist --planner "Léo"

The app (workstream B) can also `from scripts.decision_brief import build_brief`
and call `build_brief(ids, capability=..., planner=...)` to get the Markdown string.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path

from databricks import sql
from databricks.sdk.core import Config

PROFILE = os.getenv("DATABRICKS_CONFIG_PROFILE", "hackathon")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "04ab03ef1a2d183f")

TRUST_LABEL = {
    "CORROBORATED": "Corroborated",
    "CLAIMED_ONLY": "Claimed only (not independently corroborated)",
    "UNKNOWN": "Not enough data",
}


def connect():
    cfg = Config(profile=PROFILE)
    return sql.connect(
        server_hostname=cfg.host.replace("https://", "").rstrip("/"),
        http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
        access_token=cfg.token,
    )


def _rows(cur, query, params=None):
    cur.execute(query, params or {})
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _table_exists(cur, fqname) -> bool:
    try:
        cur.execute(f"SELECT 1 FROM {fqname} LIMIT 1")
        cur.fetchall()
        return True
    except Exception:
        return False


def _in_clause(ids):
    # ids are UUIDs from our own dataset; quote-escape defensively anyway.
    return ", ".join("'" + i.replace("'", "''") + "'" for i in ids)


def _loads(s):
    try:
        return json.loads(s) if s else []
    except Exception:
        return []


def _fmt_pct(x):
    return f"{round(float(x) * 100)}%" if x is not None else "—"


def _summarize_sources(raw):
    """Turn the raw source_urls JSON array into '<n> sources (domain1, domain2, …)'."""
    urls = _loads(raw)
    if not isinstance(urls, list) or not urls:
        return ""
    domains = []
    for u in urls:
        if not isinstance(u, str):
            continue
        d = u.split("//")[-1].split("/")[0].removeprefix("www.")
        if d and d not in domains:
            domains.append(d)
    if not domains:
        return ""
    shown = ", ".join(domains[:3])
    more = f", +{len(domains) - 3} more" if len(domains) > 3 else ""
    return f"{len(urls)} source links across {len(domains)} domains ({shown}{more})"


def fetch_data(ids, capability=None):
    with connect() as conn, conn.cursor() as cur:
        cap_filter = f"AND capability_key = '{capability}'" if capability else ""
        facilities = _rows(cur, f"""
            SELECT unique_id, name, city, state, capability_key, trust_state,
                   trust_score, trust_score_low, trust_score_high,
                   n_fields_corroborating, evidence_json, gaps_json,
                   record_completeness, number_doctors, capacity, source_urls
            FROM workspace.default.facility_trust
            WHERE unique_id IN ({_in_clause(ids)}) {cap_filter}
            ORDER BY CASE trust_state WHEN 'CORROBORATED' THEN 0 WHEN 'CLAIMED_ONLY' THEN 1 ELSE 2 END,
                     trust_score DESC, name
        """)

        validations = _rows(cur, f"""
            SELECT unique_id, capability_key, code, severity, message, disagrees_with_score
            FROM workspace.default.trust_validations
            WHERE unique_id IN ({_in_clause(ids)})
        """) if _table_exists(cur, "workspace.default.trust_validations") else []

        actions = []
        if _table_exists(cur, "workspace.default.planner_actions"):
            actions = _rows(cur, f"""
                SELECT unique_id, capability_key, action_type, new_state, note, planner, ts
                FROM workspace.default.planner_actions
                WHERE unique_id IN ({_in_clause(ids)})
                ORDER BY ts
            """)
    return facilities, validations, actions


def fetch_shortlist_ids():
    with connect() as conn, conn.cursor() as cur:
        if not _table_exists(cur, "workspace.default.planner_actions"):
            return []
        rows = _rows(cur, """
            SELECT DISTINCT unique_id
            FROM workspace.default.planner_actions
            WHERE action_type = 'shortlist'
        """)
    return [r["unique_id"] for r in rows]


def build_brief(ids, capability=None, planner=None, host=None) -> str:
    facilities, validations, actions = fetch_data(ids, capability)

    val_by = {}
    for v in validations:
        val_by.setdefault(v["unique_id"], []).append(v)
    act_by = {}
    for a in actions:
        act_by.setdefault(a["unique_id"], []).append(a)

    today = dt.date.today().isoformat()
    cap_txt = capability.upper() if capability else "all capabilities"
    n_corr = sum(1 for f in facilities if f["trust_state"] == "CORROBORATED")

    L = []
    L.append(f"# Decision Brief — {cap_txt}")
    L.append("")
    L.append(f"- **Date:** {today}")
    if planner:
        L.append(f"- **Prepared by:** {planner}")
    L.append(f"- **Facilities in shortlist:** {len(facilities)}  ·  **Corroborated:** {n_corr}")
    L.append(f"- **Source:** Virtue Foundation facilities dataset (DAIS 2026)")
    L.append("")
    L.append("Every rating below is backed by verbatim evidence sentences and an "
             "uncertainty band. Where our own validator disagrees with a rating, it is "
             "flagged explicitly. This document is a snapshot for team review, not a "
             "guarantee of service availability.")
    L.append("")
    L.append("---")

    if not facilities:
        L.append("")
        L.append("_No matching facilities found for the requested shortlist._")
        return "\n".join(L)

    for i, f in enumerate(facilities, 1):
        uid = f["unique_id"]
        band = f"{_fmt_pct(f['trust_score_low'])} → {_fmt_pct(f['trust_score_high'])}"
        L.append("")
        L.append(f"## {i}. {f['name']} — {f['city']}, {f['state']}")
        L.append(f"**Capability:** `{f['capability_key']}`  ·  "
                 f"**Verdict:** {TRUST_LABEL.get(f['trust_state'], f['trust_state'])}")
        L.append(f"**Trust score:** {_fmt_pct(f['trust_score'])} "
                 f"(confidence band {band}) · "
                 f"**independent evidence buckets:** {f['n_fields_corroborating']}/3 · "
                 f"**record completeness:** {_fmt_pct(f['record_completeness'])}")

        evidence = _loads(f["evidence_json"])
        if evidence:
            L.append("")
            L.append("**Evidence (verbatim):**")
            for e in evidence[:6]:
                fld = e.get("field", "?")
                sent = (e.get("sentence", "") or "").strip()
                L.append(f"- _{fld}_ — “{sent}”")

        gaps = _loads(f["gaps_json"])
        if gaps:
            L.append("")
            L.append("**Gaps / caveats:**")
            for g in gaps:
                L.append(f"- {g}")

        vs = val_by.get(uid, [])
        vs = [v for v in vs if v["capability_key"] in (None, f["capability_key"])]
        if vs:
            L.append("")
            L.append("**Validator findings:**")
            for v in vs:
                mark = "⚠ DISAGREES WITH SCORE — " if v["disagrees_with_score"] else ""
                L.append(f"- {mark}{v['message']}")

        acts = act_by.get(uid, [])
        acts = [a for a in acts if a["capability_key"] in (None, f["capability_key"])]
        if acts:
            L.append("")
            L.append("**Human overrides / notes:**")
            for a in acts:
                bits = [a["action_type"]]
                if a.get("new_state"):
                    bits.append(f"→ {a['new_state']}")
                if a.get("note"):
                    bits.append(f"“{a['note']}”")
                who = f" ({a['planner']})" if a.get("planner") else ""
                L.append(f"- {' '.join(bits)}{who}")

        meta = []
        docs = f.get("number_doctors")
        if docs and str(docs).lower() not in ("null", "none", "nan", "0", ""):
            meta.append(f"doctors: {docs}")
        cap = f.get("capacity")
        if cap and str(cap).lower() not in ("null", "none", "nan", "0", ""):
            meta.append(f"capacity: {cap}")
        src_summary = _summarize_sources(f.get("source_urls"))
        if src_summary:
            meta.append(src_summary)
        if meta:
            L.append("")
            L.append("_" + " · ".join(meta) + "_")

    L.append("")
    L.append("---")
    L.append("")
    L.append("### Methodology")
    L.append("Scores come from the Trust Engine: claim sentences are extracted from the "
             "facility record, matched to capabilities, and weighted by source specificity. "
             "A rating is **Corroborated** only when ≥2 *independent* evidence buckets agree; "
             "future/negated claims (\"proposed ICU\", \"under construction\") do not count. "
             "The confidence band is a Wilson interval over the effective evidence weight. "
             "A separate validator audits the scores for internal contradictions.")
    if host:
        L.append("")
        L.append(f"_Full reasoning trace: {host}/ml/experiments (experiment `trust-engine`)._")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", help="comma-separated unique_id list")
    ap.add_argument("--from-shortlist", action="store_true",
                    help="pull ids from planner_actions where action_type='shortlist'")
    ap.add_argument("--capability", help="restrict to one capability_key (e.g. icu)")
    ap.add_argument("--planner", help="name shown as 'Prepared by'")
    ap.add_argument("--out", default="decision_brief.md", help="output markdown path")
    args = ap.parse_args()

    if args.from_shortlist:
        ids = fetch_shortlist_ids()
        if not ids:
            raise SystemExit("No shortlist found in planner_actions (empty or table missing). "
                             "Pass --ids instead.")
    elif args.ids:
        ids = [x.strip() for x in args.ids.split(",") if x.strip()]
    else:
        raise SystemExit("Provide --ids id1,id2 or --from-shortlist.")

    host = Config(profile=PROFILE).host
    md = build_brief(ids, capability=args.capability, planner=args.planner, host=host)
    Path(args.out).write_text(md)
    print(f"Wrote {args.out} ({len(md)} chars, {len(ids)} facilities requested)")


if __name__ == "__main__":
    main()
