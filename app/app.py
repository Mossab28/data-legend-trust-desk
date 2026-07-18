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

TRUST_LABEL = {
    "CORROBORATED": "Corroborated",
    "CLAIMED_ONLY": "Claimed only",
    "UNKNOWN": "Unknown · data-sparse",
}

BADGE_HELP = {
    "CORROBORATED": "The claim is backed by evidence in 2 or more independent fields.",
    "CLAIMED_ONLY": "The facility claims this, but we found no independent corroboration.",
    "UNKNOWN": "Not enough data to judge — this does NOT mean the facility is bad.",
}

# Hex colors for trust states — single source of truth for pills, bars, map.
TRUST_HEX = {
    "CORROBORATED": "#3FB950",
    "CLAIMED_ONLY": "#D29922",
    "UNKNOWN": "#8B949E",
}

# RGB colors for the map, keyed by trust_state (derived from TRUST_HEX).
MAP_COLORS = {
    "CORROBORATED": [63, 185, 80],
    "CLAIMED_ONLY": [210, 153, 34],
    "UNKNOWN": [139, 148, 158],
}

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stMarkdown, .stButton, .stSelectbox, .stTextInput {
    font-family: 'Inter', -apple-system, system-ui, sans-serif !important;
}
.block-container { padding-top: 2.2rem; max-width: 1180px; }
#MainMenu, footer { visibility: hidden; }

/* ---- product header ---- */
.ftd-title { font-size: 26px; font-weight: 700; letter-spacing: -0.02em;
             color: #E6EDF3; margin: 0; }
.ftd-sub   { font-size: 14px; color: #8B949E; margin: 4px 0 0 0; max-width: 72ch; }
.ftd-band  { display: flex; gap: 26px; margin-top: 14px; padding: 10px 14px;
             border: 1px solid #262D37; border-radius: 8px; background: #11161D;
             font-variant-numeric: tabular-nums; }
.ftd-band .item { font-size: 12.5px; color: #8B949E; }
.ftd-band .item b { color: #E6EDF3; font-weight: 600; font-size: 13px; }

/* ---- trust pills ---- */
.ftd-pill { display: inline-flex; align-items: center; gap: 6px;
            padding: 2px 10px; border-radius: 999px; font-size: 11px;
            font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
            border: 1px solid; white-space: nowrap; }
.ftd-pill .dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }

/* ---- facility card ---- */
.ftd-card { border: 1px solid #262D37; border-radius: 8px; background: #11161D;
            padding: 13px 16px 12px 16px; margin: 10px 0 0 0; }
.ftd-row1 { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.ftd-name { font-size: 15px; font-weight: 600; color: #E6EDF3; }
.ftd-meta { font-size: 12.5px; color: #8B949E; margin-top: 2px; }
.ftd-row2 { display: flex; align-items: center; gap: 14px; margin-top: 10px; }
.ftd-scorebar { flex: 0 0 160px; height: 4px; border-radius: 2px; background: #21262D; }
.ftd-scorebar .fill { height: 100%; border-radius: 2px; }
.ftd-fields { font-size: 12px; color: #8B949E; font-variant-numeric: tabular-nums; }
.ftd-num { font-size: 12px; color: #8B949E; font-variant-numeric: tabular-nums; }
.ftd-num b { color: #C9D1D9; font-weight: 600; }

/* ---- evidence quotes ---- */
.ftd-quote { border-left: 2px solid #2F81F7; padding: 6px 12px; margin: 8px 0;
             background: #0E1420; border-radius: 0 6px 6px 0; }
.ftd-quote .q { font-size: 13.5px; color: #C9D1D9; }
.ftd-quote .src { font-size: 11px; color: #8B949E; text-transform: uppercase;
                  letter-spacing: 0.06em; margin-top: 3px; }

/* ---- stat tiles ---- */
.ftd-stats { display: flex; gap: 12px; margin: 14px 0 4px 0; }
.ftd-stat  { flex: 1; border: 1px solid #262D37; border-radius: 8px;
             background: #11161D; padding: 10px 14px; }
.ftd-stat .v { font-size: 22px; font-weight: 700; color: #E6EDF3;
               font-variant-numeric: tabular-nums; line-height: 1.1; }
.ftd-stat .l { font-size: 11.5px; color: #8B949E; margin-top: 2px;
               text-transform: uppercase; letter-spacing: 0.05em; }

/* streamlit widget touch-ups */
div[data-testid="stExpander"] details { border: 1px solid #21262D; border-radius: 0 0 8px 8px;
                                        background: #0D1117; }
div[data-baseweb="tab-list"] { gap: 4px; }
button[data-baseweb="tab"] { font-size: 14px !important; }
</style>
"""


def pill(state: str) -> str:
    """HTML trust pill for a state."""
    hexc = TRUST_HEX.get(state, TRUST_HEX["UNKNOWN"])
    label = TRUST_LABEL.get(state, state)
    return (
        f'<span class="ftd-pill" style="color:{hexc};border-color:{hexc}55;'
        f'background:{hexc}14"><span class="dot" style="background:{hexc}"></span>'
        f'{label}</span>'
    )


def scorebar(score: float, state: str) -> str:
    hexc = TRUST_HEX.get(state, TRUST_HEX["UNKNOWN"])
    pct = max(0, min(100, int(round(score * 100))))
    return (f'<div class="ftd-scorebar"><div class="fill" '
            f'style="width:{pct}%;background:{hexc}"></div></div>')

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
        f'<div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap;'
        f'margin-top:6px">'
        f'{pill("CORROBORATED")}<span class="ftd-meta">backed by 2+ independent fields</span>'
        f'{pill("CLAIMED_ONLY")}<span class="ftd-meta">stated, not independently confirmed</span>'
        f'{pill("UNKNOWN")}<span class="ftd-meta">not enough data to judge — not a bad sign</span>'
        f'</div>',
        unsafe_allow_html=True,
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
    """One facility: compact card (name, pill, score bar) + details expander."""
    trust_state = row["trust_state"] if row["trust_state"] in TRUST_LABEL else "UNKNOWN"
    city = row["city"] if is_real_value(row["city"]) else "city unknown"
    district = row.get("district")
    place = city if not is_real_value(district) or str(district) == str(city) \
        else f"{city} · {district}"

    try:
        score = max(0.0, min(1.0, float(row["trust_score"])))
    except (TypeError, ValueError):
        score = 0.0
    n_fields = row["n_fields_corroborating"]
    n_fields = int(n_fields) if pd.notna(n_fields) else 0

    # Overrides recorded for this facility+capability (freshest first).
    overrides = facility_actions[
        (facility_actions["unique_id"] == row["unique_id"])
        & (facility_actions["capability_key"] == capability_key)
        & (facility_actions["action_type"] == "override")
    ]

    nums = []
    if is_real_value(row["number_doctors"]):
        nums.append(f'<span class="ftd-num">doctors <b>{row["number_doctors"]}</b></span>')
    if is_real_value(row["capacity"]):
        nums.append(f'<span class="ftd-num">beds <b>{row["capacity"]}</b></span>')
    overridden = ('<span class="ftd-num" style="color:#D29922">reviewed by '
                  f'{overrides.iloc[0]["planner"]}</span>') if not overrides.empty else ""

    st.markdown(
        f'<div class="ftd-card">'
        f'<div class="ftd-row1"><div><div class="ftd-name">{row["name"]}</div>'
        f'<div class="ftd-meta">{place}</div></div>{pill(trust_state)}</div>'
        f'<div class="ftd-row2">{scorebar(score, trust_state)}'
        f'<span class="ftd-fields">score {score:.2f} · evidence in {n_fields} '
        f'field(s)</span>{"".join(nums)}{overridden}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Evidence, gaps & review"):
        # --- override banner -------------------------------------------------
        for _, ov in overrides.iterrows():
            st.warning(
                f"Assessment overridden by **{ov['planner']}** → "
                f"{TRUST_LABEL.get(ov['new_state'], ov['new_state'])} — “{ov['note']}”"
            )

        st.caption(BADGE_HELP[trust_state])

        # --- citations --------------------------------------------------------
        evidence = parse_json_list(row["evidence_json"])
        st.markdown("**Why we say this — exact sentences from the record:**")
        if evidence:
            quotes = []
            for ev in evidence:
                field = FIELD_LABELS.get(str(ev.get("field", "")).lower(),
                                         str(ev.get("field", "source")))
                sentence = str(ev.get("sentence", "")).strip()
                if sentence:
                    quotes.append(
                        f'<div class="ftd-quote"><div class="q">“{sentence}”</div>'
                        f'<div class="src">{field}</div></div>'
                    )
            st.markdown("".join(quotes), unsafe_allow_html=True)
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
                    format_func=lambda s: TRUST_LABEL[s],
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
                if st.form_submit_button("Add to shortlist"):
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
    tiles = [
        ("Facilities", len(df), "#E6EDF3"),
        ("Corroborated", n_cor, TRUST_HEX["CORROBORATED"]),
        ("Claimed only", n_claim, TRUST_HEX["CLAIMED_ONLY"]),
        ("Unknown · data-sparse", n_unk, TRUST_HEX["UNKNOWN"]),
    ]
    st.markdown(
        '<div class="ftd-stats">' + "".join(
            f'<div class="ftd-stat"><div class="v" style="color:{c}">{v}</div>'
            f'<div class="l">{label}</div></div>'
            for label, v, c in tiles
        ) + "</div>",
        unsafe_allow_html=True,
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
    "LIKELY_UNDERSERVED": "Likely underserved — few/no facilities AND official NFHS-5 indicators show need",
    "DATA_DESERT": "Data desert — facilities exist but their records are too sparse to trust",
    "NO_DATA_NO_FACILITIES": "No data — zero facilities in our records; NOT proof the area is empty",
    "COVERED": "Covered — facilities present with reasonably rich records",
}

DESERT_HEX = {
    "LIKELY_UNDERSERVED": "#F85149",
    "DATA_DESERT": "#D29922",
    "NO_DATA_NO_FACILITIES": "#8B949E",
    "COVERED": "#3FB950",
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
    order = ["LIKELY_UNDERSERVED", "DATA_DESERT", "NO_DATA_NO_FACILITIES", "COVERED"]
    st.markdown(
        '<div class="ftd-stats">' + "".join(
            f'<div class="ftd-stat"><div class="v" style="color:{DESERT_HEX[k]}">'
            f'{int(counts.get(k, 0))}</div>'
            f'<div class="l">{DESERT_LABELS[k].split(" — ")[0]}</div></div>'
            for k in order
        ) + "</div>",
        unsafe_allow_html=True,
    )
    for key in order:
        head, _, tail = DESERT_LABELS[key].partition(" — ")
        st.markdown(
            f'<div class="ftd-meta" style="margin:2px 0">'
            f'<span style="color:{DESERT_HEX[key]}">●</span> '
            f'<b style="color:#C9D1D9">{head}</b> — {tail}</div>',
            unsafe_allow_html=True,
        )

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

    st.markdown(f"**Shortlist ({len(shortlist)})**")
    if shortlist.empty:
        st.caption("No facilities shortlisted yet.")
    else:
        for _, a in shortlist.iterrows():
            st.markdown(
                f"- **{a['note']}** — {CAPABILITIES.get(a['capability_key'], a['capability_key'])}"
                f" · by {a['planner']} · {a['ts']}"
            )

    st.markdown(f"**Overrides & notes ({len(decisions)})**")
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

@st.cache_data(ttl=3600)
def load_headline_stats() -> dict:
    """Small header numbers; static fallbacks if the tables are unreachable."""
    try:
        df = run_query(
            f"""
            SELECT count(distinct unique_id) AS facilities,
                   count(*) AS assessments,
                   sum(CASE WHEN trust_state = 'CORROBORATED' THEN 1 ELSE 0 END)
                       AS corroborated
            FROM {FACILITY_TABLE}
            """
        )
        r = df.iloc[0]
        return {"facilities": int(r["facilities"]),
                "assessments": int(r["assessments"]),
                "corroborated": int(r["corroborated"])}
    except Exception:
        return {"facilities": 10088, "assessments": 29054, "corroborated": 3555}


def main() -> None:
    st.set_page_config(page_title="Facility Trust Desk — India",
                       page_icon="▣", layout="wide")
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    stats = load_headline_stats()
    st.markdown(
        f'<p class="ftd-title">Facility Trust Desk <span style="color:#8B949E;'
        f'font-weight:400">— India</span></p>'
        f'<p class="ftd-sub">Every capability in this data is a claim, not a '
        f'verified fact. This desk shows how much evidence backs each claim — '
        f'so you can decide, and defend, where help goes.</p>'
        f'<div class="ftd-band">'
        f'<span class="item"><b>{stats["facilities"]:,}</b> facilities</span>'
        f'<span class="item"><b>{stats["assessments"]:,}</b> capability claims '
        f'assessed</span>'
        f'<span class="item"><b>{stats["corroborated"]:,}</b> independently '
        f'corroborated</span>'
        f'<span class="item"><b>35</b> states &amp; territories</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    render_legend()
    st.divider()

    try:
        ensure_actions_table()
    except Exception:
        st.warning("Could not prepare the decisions table — overrides and "
                   "shortlists may not save right now.")

    tab_browse, tab_deserts, tab_decisions = st.tabs(
        ["Find facilities", "Medical deserts", "Shortlist & decisions"])
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
