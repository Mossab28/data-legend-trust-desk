"""Facility Trust Desk — India.

Databricks App (Streamlit) for non-technical NGO planners.
Reads  workspace.default.facility_trust   (built by the scoring pipeline)
Writes workspace.default.planner_actions  (overrides / notes / shortlist)

Every capability field in the source data is treated as a *claim*, not a fact.
This app shows how much corroborating evidence backs each claim, cites the
exact sentences, and lets the planner override the assessment with a note.
"""

import json
import os
import uuid

import pandas as pd
import streamlit as st
from databricks import sql
from databricks.sdk.core import Config

# ---------------------------------------------------------------------------
# Constants (kept in sync with docs/CONTRACT.md)
# ---------------------------------------------------------------------------

FACILITY_TABLE = "workspace.default.facility_trust"
ACTIONS_TABLE = "workspace.default.planner_actions"

CAPABILITIES = {
    "icu": "ICU (Intensive Care)",
    "nicu": "NICU (Newborn Intensive Care)",
    "maternity": "Maternity",
    "emergency": "Emergency",
    "oncology": "Oncology (Cancer Care)",
    "trauma": "Trauma",
    "dialysis": "Dialysis",
    "surgery": "Surgery",
}

TRUST_STATES = ["CORROBORATED", "CLAIMED_ONLY", "UNKNOWN"]

BADGE = {
    "CORROBORATED": "🟢 CORROBORATED",
    "CLAIMED_ONLY": "🟡 CLAIMED ONLY",
    "UNKNOWN": "⚪ UNKNOWN (data-sparse)",
}

BADGE_HELP = {
    "CORROBORATED": "The claim is backed by evidence in 2 or more independent fields.",
    "CLAIMED_ONLY": "The facility claims this, but we found no independent corroboration.",
    "UNKNOWN": "Not enough data to judge — this does NOT mean the facility is bad.",
}

# RGB colors for the map, keyed by trust_state.
MAP_COLORS = {
    "CORROBORATED": [46, 160, 67],
    "CLAIMED_ONLY": [212, 167, 44],
    "UNKNOWN": [150, 150, 150],
}

FIELD_LABELS = {
    "capability": "Capability field",
    "procedure": "Procedure field",
    "equipment": "Equipment field",
    "description": "Description field",
}


# ---------------------------------------------------------------------------
# SQL connection helpers
# ---------------------------------------------------------------------------

def _warehouse_http_path() -> str:
    return f"/sql/1.0/warehouses/{os.getenv('DATABRICKS_WAREHOUSE_ID', 'af2489ada308a769')}"


@st.cache_resource
def get_connection():
    """Open a SQL connection.

    In Databricks Apps, Config() authenticates via the app's service
    principal; locally it uses ~/.databrickscfg.
    """
    cfg = Config()
    return sql.connect(
        server_hostname=cfg.host,
        http_path=_warehouse_http_path(),
        credentials_provider=lambda: cfg.authenticate,
    )


def run_query(query: str, params: dict | None = None) -> pd.DataFrame:
    """Run a parameterized SELECT and return a DataFrame."""
    with get_connection().cursor() as cur:
        cur.execute(query, params or {})
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    return pd.DataFrame([list(r) for r in rows], columns=cols)


def run_statement(query: str, params: dict | None = None) -> None:
    """Run a DDL/DML statement (no result)."""
    with get_connection().cursor() as cur:
        cur.execute(query, params or {})


@st.cache_resource
def ensure_actions_table() -> bool:
    """Create the planner_actions table if it does not exist (once per session)."""
    run_statement(
        f"""
        CREATE TABLE IF NOT EXISTS {ACTIONS_TABLE} (
            action_id STRING,
            ts TIMESTAMP,
            planner STRING,
            unique_id STRING,
            capability_key STRING,
            action_type STRING,
            new_state STRING,
            note STRING
        )
        """
    )
    return True


# ---------------------------------------------------------------------------
# Cached reads
# ---------------------------------------------------------------------------

GEO_TABLE = "workspace.default.facility_geo"
DESERT_TABLE = "workspace.default.district_coverage"
ALL_STATES = "All states"


@st.cache_data(ttl=300)
def load_states() -> list[str]:
    """Clean state names normalized via the India Post pincode directory."""
    df = run_query(
        f"""
        SELECT state_clean, count(*) AS n FROM {GEO_TABLE}
        WHERE state_clean IS NOT NULL AND trim(state_clean) <> ''
        GROUP BY state_clean ORDER BY n DESC
        """
    )
    return [ALL_STATES] + df["state_clean"].tolist()


@st.cache_data(ttl=300)
def load_facilities(capability_key: str, state: str) -> pd.DataFrame:
    """Facilities for one capability + state, ranked by trust.

    CORROBORATED first, then CLAIMED_ONLY, then UNKNOWN; trust_score desc
    inside each group.
    """
    state_filter = "" if state == ALL_STATES else "AND g.state_clean = :state"
    params = {"capability_key": capability_key}
    if state != ALL_STATES:
        params["state"] = state
    return run_query(
        f"""
        SELECT t.unique_id, t.name, t.city,
               coalesce(g.state_clean, t.state) AS state, g.district,
               t.pincode, t.latitude, t.longitude,
               t.capability_key, t.trust_state, t.trust_score,
               t.n_fields_corroborating, t.evidence_json, t.gaps_json,
               t.record_completeness, t.number_doctors, t.capacity, t.source_urls
        FROM {FACILITY_TABLE} t
        LEFT JOIN {GEO_TABLE} g ON t.unique_id = g.unique_id
        WHERE t.capability_key = :capability_key {state_filter}
        ORDER BY
          CASE trust_state
            WHEN 'CORROBORATED' THEN 0
            WHEN 'CLAIMED_ONLY' THEN 1
            ELSE 2
          END,
          trust_score DESC,
          name
        """,
        params,
    )


def load_actions(unique_ids: list[str] | None = None) -> pd.DataFrame:
    """Planner actions — always fresh (never cached)."""
    df = run_query(
        f"""
        SELECT action_id, ts, planner, unique_id, capability_key,
               action_type, new_state, note
        FROM {ACTIONS_TABLE}
        ORDER BY ts DESC
        """
    )
    if unique_ids is not None and not df.empty:
        df = df[df["unique_id"].isin(unique_ids)]
    return df


def insert_action(planner: str, unique_id: str, capability_key: str,
                  action_type: str, new_state: str | None, note: str) -> None:
    run_statement(
        f"""
        INSERT INTO {ACTIONS_TABLE}
            (action_id, ts, planner, unique_id, capability_key,
             action_type, new_state, note)
        VALUES (:action_id, current_timestamp(), :planner, :unique_id,
                :capability_key, :action_type, :new_state, :note)
        """,
        {
            "action_id": str(uuid.uuid4()),
            "planner": planner,
            "unique_id": unique_id,
            "capability_key": capability_key,
            "action_type": action_type,
            "new_state": new_state,
            "note": note,
        },
    )


# ---------------------------------------------------------------------------
# Small display helpers
# ---------------------------------------------------------------------------

def parse_json_list(raw) -> list:
    """Safely parse a JSON-array string; never raise."""
    if raw is None or not isinstance(raw, str) or not raw.strip():
        return []
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else []
    except (ValueError, TypeError):
        return []


def is_real_value(v) -> bool:
    """Placeholders ('', '[]', '[\"\"]', 'nan', '0') are NOT content."""
    if v is None:
        return False
    s = str(v).strip()
    return s not in ("", "[]", '[""]', "nan", "None", "0")


def render_legend() -> None:
    st.markdown(
        "**Legend:**&nbsp;&nbsp; 🟢 **Corroborated** — backed by 2+ independent fields"
        " &nbsp;·&nbsp; 🟡 **Claimed only** — stated but not independently confirmed"
        " &nbsp;·&nbsp; ⚪ **Unknown** — *not enough data to judge* (not a bad sign)"
    )


def render_map(df: pd.DataFrame) -> None:
    """Optional map of filtered facilities, colored by trust state.

    Silently skipped whenever geo columns are missing or dirty — the app must
    never crash on bad coordinates.
    """
    try:
        import pydeck as pdk

        geo = df.copy()
        geo["latitude"] = pd.to_numeric(geo["latitude"], errors="coerce")
        geo["longitude"] = pd.to_numeric(geo["longitude"], errors="coerce")
        geo = geo.dropna(subset=["latitude", "longitude"])
        geo = geo[(geo["latitude"] != 0) & (geo["longitude"] != 0)]
        geo = geo[geo["latitude"].between(-90, 90) & geo["longitude"].between(-180, 180)]
        if geo.empty:
            return
        geo["color"] = geo["trust_state"].map(
            lambda s: MAP_COLORS.get(s, MAP_COLORS["UNKNOWN"])
        )
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=geo[["name", "city", "trust_state", "latitude", "longitude", "color"]],
            get_position="[longitude, latitude]",
            get_fill_color="color",
            get_radius=4000,
            radius_min_pixels=4,
            radius_max_pixels=12,
            pickable=True,
        )
        view = pdk.ViewState(
            latitude=float(geo["latitude"].mean()),
            longitude=float(geo["longitude"].mean()),
            zoom=6,
        )
        st.pydeck_chart(
            pdk.Deck(
                layers=[layer],
                initial_view_state=view,
                tooltip={"text": "{name}\n{city} — {trust_state}"},
                map_style=None,
            )
        )
        st.caption("Map shows only facilities with usable coordinates — "
                   "absence from the map does not mean absence on the ground.")
    except Exception:
        # Map is a bonus; never let it break the page.
        pass


# ---------------------------------------------------------------------------
# Facility card
# ---------------------------------------------------------------------------

def render_facility(row: pd.Series, capability_key: str,
                    facility_actions: pd.DataFrame) -> None:
    """One expandable facility card with citations, gaps and override form."""
    trust_state = row["trust_state"] if row["trust_state"] in BADGE else "UNKNOWN"
    city = row["city"] if is_real_value(row["city"]) else "city unknown"
    title = f"{BADGE[trust_state]} — {row['name']} · {city}"

    # Overrides recorded for this facility+capability (freshest first).
    overrides = facility_actions[
        (facility_actions["unique_id"] == row["unique_id"])
        & (facility_actions["capability_key"] == capability_key)
        & (facility_actions["action_type"] == "override")
    ]
    if not overrides.empty:
        title += "  ✏️ overridden"

    with st.expander(title):
        # --- override banner -------------------------------------------------
        for _, ov in overrides.iterrows():
            st.warning(
                f"✏️ **Overridden by {ov['planner']}** → "
                f"{BADGE.get(ov['new_state'], ov['new_state'])} — “{ov['note']}”"
            )

        # --- headline numbers -------------------------------------------------
        st.caption(BADGE_HELP[trust_state])
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            score = row["trust_score"]
            try:
                score = max(0.0, min(1.0, float(score)))
            except (TypeError, ValueError):
                score = 0.0
            st.progress(score, text=f"Trust score: {score:.2f}")
            n_fields = row["n_fields_corroborating"]
            n_fields = int(n_fields) if pd.notna(n_fields) else 0
            st.caption(f"Evidence found in **{n_fields}** independent field(s)")
        with c2:
            if is_real_value(row["number_doctors"]):
                st.metric("Doctors (claimed)", str(row["number_doctors"]))
        with c3:
            if is_real_value(row["capacity"]):
                st.metric("Capacity (claimed)", str(row["capacity"]))

        # --- citations --------------------------------------------------------
        evidence = parse_json_list(row["evidence_json"])
        st.markdown("**Why we say this — exact sentences from the record:**")
        if evidence:
            for ev in evidence:
                field = FIELD_LABELS.get(str(ev.get("field", "")).lower(),
                                         str(ev.get("field", "source")))
                sentence = str(ev.get("sentence", "")).strip()
                if sentence:
                    st.markdown(f"> “{sentence}”\n>\n> — *{field}*")
        else:
            st.caption("No supporting sentences were found in this record.")

        # --- gaps -------------------------------------------------------------
        gaps = parse_json_list(row["gaps_json"])
        if gaps:
            st.info("**What we don't know:**\n\n" +
                    "\n".join(f"- {g}" for g in gaps if str(g).strip()))

        # --- sources ----------------------------------------------------------
        if is_real_value(row["source_urls"]):
            st.caption(f"Sources: {row['source_urls']}")

        st.divider()

        # --- actions: override + shortlist -----------------------------------
        left, right = st.columns([3, 1])
        key_base = f"{row['unique_id']}_{capability_key}"

        with left:
            with st.form(f"override_{key_base}", clear_on_submit=True):
                st.markdown("**Disagree with this assessment? Override it:**")
                new_state = st.selectbox(
                    "New status",
                    TRUST_STATES,
                    format_func=lambda s: BADGE[s],
                    key=f"state_{key_base}",
                )
                note = st.text_input(
                    "Why? (required)",
                    placeholder="e.g. I visited this facility in May — the ICU is real.",
                    key=f"note_{key_base}",
                )
                planner = st.text_input("Your name (required)", key=f"planner_{key_base}")
                if st.form_submit_button("Save override"):
                    if not note.strip() or not planner.strip():
                        st.error("Both a note and your name are required.")
                    else:
                        insert_action(planner.strip(), row["unique_id"],
                                      capability_key, "override",
                                      new_state, note.strip())
                        st.success("Override saved.")
                        st.rerun()

        with right:
            st.markdown("**Shortlist**")
            with st.form(f"shortlist_{key_base}", clear_on_submit=True):
                sl_planner = st.text_input("Your name", key=f"sl_planner_{key_base}")
                if st.form_submit_button("➕ Add to shortlist"):
                    if not sl_planner.strip():
                        st.error("Please enter your name.")
                    else:
                        insert_action(sl_planner.strip(), row["unique_id"],
                                      capability_key, "shortlist", None,
                                      f"Shortlisted {row['name']}")
                        st.success("Added to shortlist.")
                        st.rerun()


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

def render_browse_tab() -> None:
    """Main workflow: pick capability + region → ranked facilities → citations."""
    f1, f2, f3 = st.columns([2, 2, 2])
    with f1:
        capability_key = st.selectbox(
            "What capability do you need?",
            list(CAPABILITIES),
            format_func=lambda k: CAPABILITIES[k],
        )
    with f2:
        try:
            states = load_states()
        except Exception:
            states = []
        if not states:
            st.error(
                "The facility data isn't available yet — the scoring pipeline "
                "hasn't been run. Please check back shortly."
            )
            return
        state = st.selectbox("State / region", states)
    with f3:
        city_filter = st.text_input("City contains (optional)",
                                    placeholder="e.g. Chennai")

    df = load_facilities(capability_key, state)
    if city_filter.strip():
        df = df[df["city"].fillna("").str.contains(city_filter.strip(),
                                                   case=False, regex=False)]

    counts = df["trust_state"].value_counts() if not df.empty else {}
    n_cor = int(counts.get("CORROBORATED", 0))
    n_claim = int(counts.get("CLAIMED_ONLY", 0))
    n_unk = int(counts.get("UNKNOWN", 0))
    st.markdown(
        f"### {len(df)} facilities · 🟢 {n_cor} corroborated · "
        f"🟡 {n_claim} claimed-only · ⚪ {n_unk} unknown (data-sparse)"
    )

    if df.empty:
        st.info(
            "No facility in this selection claims this capability. Remember: "
            "**a data desert is not a medical desert** — facilities may exist "
            "here that simply aren't in our records."
        )
        return

    render_map(df)

    try:
        actions = load_actions(df["unique_id"].tolist())
    except Exception:
        actions = pd.DataFrame(columns=["action_id", "ts", "planner", "unique_id",
                                        "capability_key", "action_type",
                                        "new_state", "note"])

    for _, row in df.iterrows():
        render_facility(row, capability_key, actions)


DESERT_LABELS = {
    "LIKELY_UNDERSERVED": "🔴 Likely underserved — few/no facilities AND official NFHS-5 indicators show need",
    "DATA_DESERT": "🟠 Data desert — facilities exist but their records are too sparse to trust",
    "NO_DATA_NO_FACILITIES": "⚪ No data — zero facilities in our records; NOT proof the area is empty",
    "COVERED": "🟢 Covered — facilities present with reasonably rich records",
}


@st.cache_data(ttl=300)
def load_districts() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {DESERT_TABLE}")


def render_deserts_tab() -> None:
    """District-level view: separating medical deserts from data deserts."""
    st.subheader("Medical deserts vs data deserts")
    st.markdown(
        "**A blank spot in our data is not a blank spot on the ground.** "
        "This view joins our records with the India Post directory and the "
        "official **NFHS-5 district health survey** to say, honestly, which "
        "districts look underserved — and which we simply don't know about."
    )
    try:
        df = load_districts()
    except Exception:
        st.info("District coverage data isn't available yet.")
        return
    if df.empty:
        st.info("District coverage data isn't available yet.")
        return

    counts = df["desert_class"].value_counts()
    cols = st.columns(4)
    for col, key in zip(cols, ["LIKELY_UNDERSERVED", "DATA_DESERT",
                               "NO_DATA_NO_FACILITIES", "COVERED"]):
        with col:
            st.metric(key.replace("_", " ").title(), int(counts.get(key, 0)))
    for key in ["LIKELY_UNDERSERVED", "DATA_DESERT", "NO_DATA_NO_FACILITIES", "COVERED"]:
        st.caption(DESERT_LABELS[key])

    pick = st.selectbox(
        "Show districts classified as",
        ["LIKELY_UNDERSERVED", "DATA_DESERT", "NO_DATA_NO_FACILITIES", "COVERED"],
        format_func=lambda k: DESERT_LABELS[k].split(" — ")[0],
    )
    sub = df[df["desert_class"] == pick].copy()

    display_cols = [c for c in [
        "statename", "district", "n_facilities", "data_richness",
        "institutional_birth_5y_pct", "births_delivered_by_csection_5y_pct",
        "mothers_who_had_at_least_4_anc_visits_lb5y_pct",
        "hh_member_covered_health_insurance_pct",
    ] if c in sub.columns]
    nice = {
        "statename": "State", "district": "District",
        "n_facilities": "Facilities in our data",
        "data_richness": "Record richness (0-1)",
        "institutional_birth_5y_pct": "Institutional births %  (NFHS-5)",
        "births_delivered_by_csection_5y_pct": "C-section births % (NFHS-5)",
        "mothers_who_had_at_least_4_anc_visits_lb5y_pct": "4+ antenatal visits % (NFHS-5)",
        "hh_member_covered_health_insurance_pct": "Health-insurance coverage % (NFHS-5)",
    }
    sub = sub[display_cols].rename(columns=nice)
    sort_col = "Institutional births %  (NFHS-5)"
    if sort_col in sub.columns:
        sub = sub.sort_values(sort_col, na_position="last")
    st.dataframe(sub, use_container_width=True, hide_index=True)
    st.caption(
        "NFHS-5 columns come from the official district health survey — an "
        "external reference independent of our facility records. Where they are "
        "empty, the district could not be matched (post-2019 district splits)."
    )


def render_decisions_tab() -> None:
    """Shortlist and decision history, straight from planner_actions."""
    st.subheader("My shortlist & decisions")
    try:
        actions = load_actions()
    except Exception:
        st.info("No decisions recorded yet.")
        return
    if actions.empty:
        st.info("Nothing here yet — shortlist a facility or record an "
                "override from the Find facilities tab.")
        return

    shortlist = actions[actions["action_type"] == "shortlist"]
    decisions = actions[actions["action_type"] != "shortlist"]

    st.markdown(f"**📌 Shortlist ({len(shortlist)})**")
    if shortlist.empty:
        st.caption("No facilities shortlisted yet.")
    else:
        for _, a in shortlist.iterrows():
            st.markdown(
                f"- **{a['note']}** — {CAPABILITIES.get(a['capability_key'], a['capability_key'])}"
                f" · by {a['planner']} · {a['ts']}"
            )

    st.markdown(f"**✏️ Overrides & notes ({len(decisions)})**")
    if decisions.empty:
        st.caption("No overrides recorded yet.")
    else:
        show = decisions[["ts", "planner", "unique_id", "capability_key",
                          "action_type", "new_state", "note"]].copy()
        show["capability_key"] = show["capability_key"].map(
            lambda k: CAPABILITIES.get(k, k))
        show.columns = ["When", "Planner", "Facility ID", "Capability",
                        "Action", "New status", "Note"]
        st.dataframe(show, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Facility Trust Desk — India",
                       page_icon="🏥", layout="wide")

    st.title("🏥 Facility Trust Desk — India")
    st.markdown(
        "Every capability in this data is a **claim, not a verified fact** — "
        "this desk shows how much evidence backs each claim, so you can "
        "decide (and defend) where help goes."
    )
    render_legend()
    st.divider()

    try:
        ensure_actions_table()
    except Exception:
        st.warning("Could not prepare the decisions table — overrides and "
                   "shortlists may not save right now.")

    tab_browse, tab_deserts, tab_decisions = st.tabs(
        ["🔎 Find facilities", "🗺️ Medical deserts",
         "📌 My shortlist & decisions"])
    with tab_browse:
        try:
            render_browse_tab()
        except Exception as exc:
            if "TABLE_OR_VIEW_NOT_FOUND" in str(exc) or "does not exist" in str(exc).lower():
                st.error("The facility data isn't available yet — the scoring "
                         "pipeline hasn't been run. Please check back shortly.")
            else:
                st.error("Something went wrong loading the data. Please refresh "
                         "and try again.")
    with tab_deserts:
        try:
            render_deserts_tab()
        except Exception:
            st.info("District coverage data isn't available yet.")
    with tab_decisions:
        render_decisions_tab()


if __name__ == "__main__":
    main()
