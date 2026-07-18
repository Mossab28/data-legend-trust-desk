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
    "CORROBORATED": "Backed by 2+ independent evidence sources (structured "
                    "equipment, procedures, self-reported narrative).",
    "CLAIMED_ONLY": "The facility claims this, but no independent source "
                    "corroborates it — same text copied across fields counts once.",
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
            note STRING,
            scenario STRING
        )
        """
    )
    # Older deployments may lack the scenario column.
    try:
        run_statement(f"ALTER TABLE {ACTIONS_TABLE} ADD COLUMNS (scenario STRING)")
    except Exception:
        pass  # column already exists
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
               action_type, new_state, note, scenario
        FROM {ACTIONS_TABLE}
        ORDER BY ts DESC
        """
    )
    if unique_ids is not None and not df.empty:
        df = df[df["unique_id"].isin(unique_ids)]
    return df


def insert_action(planner: str, unique_id: str, capability_key: str,
                  action_type: str, new_state: str | None, note: str,
                  scenario: str | None = None) -> None:
    run_statement(
        f"""
        INSERT INTO {ACTIONS_TABLE}
            (action_id, ts, planner, unique_id, capability_key,
             action_type, new_state, note, scenario)
        VALUES (:action_id, current_timestamp(), :planner, :unique_id,
                :capability_key, :action_type, :new_state, :note, :scenario)
        """,
        {
            "action_id": str(uuid.uuid4()),
            "planner": planner,
            "unique_id": unique_id,
            "capability_key": capability_key,
            "action_type": action_type,
            "new_state": new_state,
            "note": note,
            "scenario": scenario,
        },
    )


# ---------------------------------------------------------------------------
# Identity & access — who you are comes from Databricks SSO, not a text box
# ---------------------------------------------------------------------------

ROLES_TABLE = "workspace.default.app_roles"


def get_authenticated_email() -> str:
    """Real identity of the signed-in user, forwarded by Databricks Apps.

    Cannot be spoofed from the browser: the platform injects the header after
    OAuth. Empty string when running outside Apps (local dev).
    """
    try:
        headers = st.context.headers
        return (headers.get("X-Forwarded-Email")
                or headers.get("x-forwarded-email") or "").strip().lower()
    except Exception:
        return ""


@st.cache_data(ttl=120)
def load_role(email: str) -> str:
    """viewer (default) < planner (can act) < admin (can also grant)."""
    if not email:
        return "viewer"
    try:
        df = run_query(
            f"SELECT role FROM {ROLES_TABLE} WHERE lower(email) = :email "
            f"ORDER BY ts DESC LIMIT 1", {"email": email})
        return df.iloc[0]["role"] if not df.empty else "viewer"
    except Exception:
        return "viewer"


def render_sidebar() -> tuple[str, str, str]:
    """Authenticated identity + role + active scenario."""
    email = get_authenticated_email()
    role = load_role(email)
    with st.sidebar:
        st.markdown("**Planner**")
        if email:
            st.markdown(f'<div class="ftd-meta">Signed in as<br>'
                        f'<b style="color:#C9D1D9">{email}</b></div>',
                        unsafe_allow_html=True)
        else:
            st.caption("Not signed in (local dev mode).")
        st.markdown(
            f'<div class="ftd-meta" style="margin-top:4px">Role: '
            f'<b style="color:#C9D1D9">{role}</b></div>',
            unsafe_allow_html=True)
        if role == "viewer":
            st.caption("You can explore everything. Overrides and shortlists "
                       "are reserved for approved planners — ask an admin to "
                       "add you.")
        scenario = st.text_input(
            "Active scenario", key="scenario_name",
            value=st.session_state.get("scenario_name", ""),
            placeholder="e.g. Maternity push — Rajasthan Q3",
            help="Shortlists are grouped under this scenario name.",
        ).strip() or "Unnamed scenario"

        if role == "admin":
            with st.expander("Admin — grant access"):
                new_email = st.text_input("Email", key="grant_email")
                new_role = st.selectbox("Role", ["planner", "admin"],
                                        key="grant_role")
                if st.button("Grant", key="grant_btn") and new_email.strip():
                    try:
                        run_statement(
                            f"INSERT INTO {ROLES_TABLE} VALUES "
                            f"(:email, :role, :by, current_timestamp())",
                            {"email": new_email.strip().lower(),
                             "role": new_role, "by": email})
                        load_role.clear()
                        st.success(f"{new_email} → {new_role}")
                    except Exception:
                        st.error("Could not grant access.")

        st.divider()
        st.markdown(
            '<div class="ftd-meta">How it works<br>'
            '1&nbsp;&nbsp;Pick a need and a region<br>'
            '2&nbsp;&nbsp;Inspect the evidence behind each facility<br>'
            '3&nbsp;&nbsp;Save decisions your team can defend</div>',
            unsafe_allow_html=True,
        )
    planner = email if role in ("planner", "admin") else ""
    return planner, scenario, role


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
        f'{pill("CORROBORATED")}<span class="ftd-meta">backed by 2+ independent sources</span>'
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
        c1, c2 = st.columns([1, 5])
        with c1:
            st.button("Recenter map", key="recenter_facilities",
                      help="Reset the map to its initial view.")
        with c2:
            st.caption("Map shows only facilities with usable coordinates — "
                       "absence from the map does not mean absence on the ground.")
    except Exception:
        # Map is a bonus; never let it break the page.
        pass


# ---------------------------------------------------------------------------
# Facility card
# ---------------------------------------------------------------------------

def render_facility(row: pd.Series, capability_key: str,
                    facility_actions: pd.DataFrame,
                    planner: str = "", scenario: str = "") -> None:
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
        f'<span class="ftd-fields">score {score:.2f} · {n_fields} independent '
        f'source(s)</span>{"".join(nums)}{overridden}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Evidence, gaps & review"):
        # --- self-correction: our own validator may disagree -----------------
        try:
            vals = validations_for(row["unique_id"], capability_key,
                                   load_validations())
        except Exception:
            vals = pd.DataFrame()
        if not vals.empty:
            disagree = vals[vals["disagrees_with_score"] == True]  # noqa: E712
            for _, v in disagree.iterrows():
                st.error(f"**Our own validator disagrees with this rating.** "
                         f"{v['message']}")
            for _, v in vals[vals["disagrees_with_score"] != True].iterrows():  # noqa: E712
                st.caption(f"Validator note: {v['message']}")

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

        # --- data-quality alarms ---------------------------------------------
        try:
            flags = anomaly_flags_for(row["unique_id"], load_anomalies())
        except Exception:
            flags = pd.DataFrame()
        for _, fl in flags.iterrows():
            label, explain = ANOMALY_LABELS.get(
                fl["anomaly_type"], (fl["anomaly_type"], ""))
            st.error(f"**{label}.** {fl['detail']}\n\n{explain}")

        # --- sources ----------------------------------------------------------
        if is_real_value(row["source_urls"]):
            st.caption(f"Sources: {row['source_urls']}")

        st.divider()

        # --- actions: override + shortlist -----------------------------------
        key_base = f"{row['unique_id']}_{capability_key}"

        if not planner:
            st.caption("Overrides and shortlists are reserved for approved "
                       "planners — your decisions must be attributable.")
            return

        left, right = st.columns([3, 1])
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
                if st.form_submit_button("Save override"):
                    if not note.strip():
                        st.error("A note is required — your team needs the why.")
                    else:
                        insert_action(planner, row["unique_id"],
                                      capability_key, "override",
                                      new_state, note.strip(), scenario)
                        st.success("Override saved.")
                        st.rerun()

        with right:
            st.markdown("**Shortlist**")
            st.caption(f"Scenario: {scenario}")
            if st.button("Add to shortlist", key=f"sl_{key_base}"):
                insert_action(planner, row["unique_id"],
                              capability_key, "shortlist", None,
                              f"Shortlisted {row['name']}", scenario)
                st.success("Added to shortlist.")
                st.rerun()


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

def render_browse_tab(planner: str = "", scenario: str = "") -> None:
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

    # --- refine toolbar ---------------------------------------------------
    t1, t2, t3 = st.columns([1.2, 1.6, 3.2])
    with t1:
        only_cor = st.toggle("Corroborated only", value=False)
    with t2:
        sort_by = st.selectbox(
            "Sort by", ["Trust ranking", "Trust score", "Record completeness"],
            label_visibility="collapsed",
        )
    with t3:
        if not df.empty:
            comp = pd.to_numeric(df["record_completeness"], errors="coerce")
            sparse_pct = int(round(100 * ((comp < 0.5) | comp.isna()).mean()))
            st.markdown(
                f'<div class="ftd-meta" style="margin-top:6px">'
                f'{sparse_pct}% of records in this selection are data-sparse — '
                f'absence of evidence is not evidence of absence.</div>',
                unsafe_allow_html=True,
            )

    if only_cor:
        df = df[df["trust_state"] == "CORROBORATED"]
    if sort_by == "Trust score":
        df = df.sort_values("trust_score", ascending=False)
    elif sort_by == "Record completeness":
        df = df.sort_values("record_completeness", ascending=False)

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

    page_size = 50
    shown = df.head(page_size)
    for _, row in shown.iterrows():
        render_facility(row, capability_key, actions, planner, scenario)
    if len(df) > page_size:
        st.caption(f"Showing the top {page_size} of {len(df)} facilities — "
                   "narrow the region or city filter to see the rest.")


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


CENTROIDS_TABLE = "workspace.default.district_centroids"
ANOMALY_TABLE = "workspace.default.trust_anomalies"

VALIDATIONS_TABLE = "workspace.default.trust_validations"

ANOMALY_LABELS = {
    "GEO_MISMATCH": ("Location doesn't add up",
                     "The GPS position and the declared PIN code disagree by "
                     "over 100 km — one of them is wrong."),
    "DIGITALLY_SILENT": ("No sign of life",
                         "Claims critical care (ICU, emergency, trauma) but has "
                         "no social presence and no page update since 2024. "
                         "The facility may have closed or changed."),
}


@st.cache_data(ttl=300)
def load_validations() -> pd.DataFrame:
    """Independent self-correction audit of our own scores."""
    return run_query(
        f"""
        SELECT unique_id, capability_key, code, severity, message,
               disagrees_with_score
        FROM {VALIDATIONS_TABLE}
        """
    )


def validations_for(unique_id: str, capability_key: str,
                    validations: pd.DataFrame) -> pd.DataFrame:
    if validations.empty:
        return validations
    return validations[
        (validations["unique_id"] == unique_id)
        & (validations["capability_key"].isna()
           | (validations["capability_key"] == capability_key))
    ]


def load_humility_count() -> int:
    """How many times a human corrected this app — worn as a badge, not hidden."""
    try:
        df = run_query(
            f"SELECT count(*) AS n FROM {ACTIONS_TABLE} "
            f"WHERE action_type = 'override'")
        return int(df.iloc[0]["n"])
    except Exception:
        return 0


@st.cache_data(ttl=300)
def load_anomalies() -> pd.DataFrame:
    return run_query(
        f"SELECT unique_id, name, anomaly_type, detail FROM {ANOMALY_TABLE}")


def anomaly_flags_for(unique_id: str, anomalies: pd.DataFrame) -> pd.DataFrame:
    if anomalies.empty:
        return anomalies
    return anomalies[anomalies["unique_id"] == unique_id]


@st.cache_data(ttl=300)
def load_districts() -> pd.DataFrame:
    return run_query(
        f"""
        SELECT d.*, c.lat, c.lon
        FROM {DESERT_TABLE} d
        LEFT JOIN {CENTROIDS_TABLE} c
          ON d.statename = c.statename AND d.district = c.district
        """
    )


def render_desert_map(df: pd.DataFrame) -> None:
    """District dots colored by desert class. 'No hospitals here' (red) must
    never look like 'we don't know what's here' (hollow gray)."""
    try:
        import pydeck as pdk

        geo = df.copy()
        geo["lat"] = pd.to_numeric(geo["lat"], errors="coerce")
        geo["lon"] = pd.to_numeric(geo["lon"], errors="coerce")
        geo = geo.dropna(subset=["lat", "lon"])
        if geo.empty:
            return

        def rgba(k, alpha):
            h = DESERT_HEX.get(k, "#8B949E").lstrip("#")
            return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [alpha]

        # Solid fill for classes we assert; hollow (stroke-only) for no-data.
        geo["fill"] = geo["desert_class"].map(
            lambda k: rgba(k, 30 if k == "NO_DATA_NO_FACILITIES" else 170))
        geo["line"] = geo["desert_class"].map(lambda k: rgba(k, 220))
        geo["radius"] = geo["desert_class"].map(
            lambda k: 14000 if k == "LIKELY_UNDERSERVED" else 9000)
        geo["n_fac"] = pd.to_numeric(geo["n_facilities"], errors="coerce").fillna(0)
        geo["class_label"] = geo["desert_class"].map(
            lambda k: DESERT_LABELS.get(k, k).split(" — ")[0])
        geo["district_label"] = (geo["district"].astype(str).str.title()
                                 + " · " + geo["statename"].astype(str).str.title())

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=geo[["district_label", "class_label", "n_fac",
                      "lat", "lon", "fill", "line", "radius"]],
            get_position="[lon, lat]",
            get_fill_color="fill",
            get_line_color="line",
            get_radius="radius",
            radius_min_pixels=3,
            radius_max_pixels=18,
            stroked=True,
            line_width_min_pixels=1,
            pickable=True,
        )
        view = pdk.ViewState(latitude=22.5, longitude=80.0, zoom=3.8)
        st.pydeck_chart(pdk.Deck(
            layers=[layer], initial_view_state=view,
            tooltip={"text": "{district_label}\n{class_label} — "
                             "{n_fac} facilities in our records"},
            map_style=None,
        ))
        c1, c2 = st.columns([1, 5])
        with c1:
            st.button("Recenter map", key="recenter_districts",
                      help="Reset the map to the all-India view.")
        with c2:
            st.caption(
                "Solid red: official health indicators point to real unmet "
                "need. Hollow gray: our records are simply empty there — an "
                "unknown, not a verdict."
            )
    except Exception:
        pass


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

    render_desert_map(df)

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

    # --- turn the unknown into a to-do list --------------------------------
    if pick in ("LIKELY_UNDERSERVED", "DATA_DESERT"):
        st.markdown("**Who to call first** — verifying these records would "
                    "improve this map more than any algorithm:")
        try:
            todo = load_call_first(pick)
            st.dataframe(
                todo.rename(columns={
                    "name": "Facility", "district": "District",
                    "state": "State", "completeness": "Record completeness",
                    "inst_birth_pct": "Institutional births % (NFHS-5)"}),
                use_container_width=True, hide_index=True,
            )
            st.caption("Sparse record + high-need district = one phone call "
                       "turns a data desert into information.")
        except Exception:
            st.caption("Call-first list unavailable.")


def render_quality_tab() -> None:
    """Data-quality alarms + the validator's audit of our own scores.

    Planner language only — this is 'what to double-check before trusting',
    not a technical forensics lab.
    """
    st.subheader("Before you trust the data — what we flagged ourselves")
    st.markdown(
        "This app audits its **own** work. Below: records where something "
        "doesn't add up, and cases where our independent validator "
        "**overturned our own rating**."
    )

    try:
        vals = load_validations()
        n_disagree = int((vals["disagrees_with_score"] == True).sum())  # noqa: E712
    except Exception:
        vals, n_disagree = pd.DataFrame(), 0
    try:
        anoms = load_anomalies()
    except Exception:
        anoms = pd.DataFrame()

    n_geo = int((anoms["anomaly_type"] == "GEO_MISMATCH").sum()) if not anoms.empty else 0
    n_silent = int((anoms["anomaly_type"] == "DIGITALLY_SILENT").sum()) if not anoms.empty else 0
    tiles = [
        ("Ratings we overturned ourselves", n_disagree, "#F85149"),
        ("Locations that don't add up", n_geo, "#D29922"),
        ("Critical-care claims, no sign of life", n_silent, "#D29922"),
        ("Validator findings in total", len(vals), "#E6EDF3"),
    ]
    st.markdown(
        '<div class="ftd-stats">' + "".join(
            f'<div class="ftd-stat"><div class="v" style="color:{c}">{v}</div>'
            f'<div class="l">{label}</div></div>'
            for label, v, c in tiles) + "</div>",
        unsafe_allow_html=True,
    )

    if not vals.empty:
        st.markdown("**Cases where our validator overturned our own rating** "
                    "— honesty first:")
        show = vals[vals["disagrees_with_score"] == True].copy()  # noqa: E712
        st.dataframe(
            show[["unique_id", "capability_key", "message"]].rename(columns={
                "unique_id": "Facility ID", "capability_key": "Capability",
                "message": "Why we no longer stand by the rating"}),
            use_container_width=True, hide_index=True, height=260,
        )

    if not anoms.empty:
        for key, (label, explain) in ANOMALY_LABELS.items():
            sub = anoms[anoms["anomaly_type"] == key]
            if sub.empty:
                continue
            with st.expander(f"{label} — {len(sub)} facilities"):
                st.caption(explain)
                st.dataframe(
                    sub[["name", "detail"]].rename(columns={
                        "name": "Facility", "detail": "What we found"}),
                    use_container_width=True, hide_index=True, height=300,
                )


@st.cache_data(ttl=300)
def load_call_first(desert_class: str) -> pd.DataFrame:
    """High-leverage records: verifying THESE first improves the map most."""
    return run_query(
        f"""
        SELECT DISTINCT t.name, initcap(g.district) AS district,
               g.state_clean AS state,
               round(t.record_completeness, 2) AS completeness,
               d.institutional_birth_5y_pct AS inst_birth_pct
        FROM {DESERT_TABLE} d
        JOIN {GEO_TABLE} g
          ON lower(g.district) = d.district AND lower(g.state_clean) = d.statename
        JOIN {FACILITY_TABLE} t ON t.unique_id = g.unique_id
        WHERE d.desert_class = :dc
        ORDER BY t.record_completeness ASC, inst_birth_pct ASC
        LIMIT 15
        """,
        {"dc": desert_class},
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

    shortlist = actions[actions["action_type"] == "shortlist"].copy()
    decisions = actions[actions["action_type"] != "shortlist"]

    st.markdown(f"**Planning scenarios ({len(shortlist)} shortlisted)**")
    if shortlist.empty:
        st.caption("No facilities shortlisted yet.")
    else:
        if "scenario" not in shortlist.columns:
            shortlist["scenario"] = None
        shortlist["scenario"] = shortlist["scenario"].fillna("Unnamed scenario")
        for scen, group in shortlist.groupby("scenario", sort=True):
            st.markdown(f'<div class="ftd-card"><div class="ftd-name">{scen}'
                        f'</div><div class="ftd-meta">{len(group)} facilities'
                        f'</div></div>', unsafe_allow_html=True)
            for _, a in group.iterrows():
                st.markdown(
                    f"- **{a['note']}** — "
                    f"{CAPABILITIES.get(a['capability_key'], a['capability_key'])}"
                    f" · by {a['planner']} · {a['ts']}"
                )

    st.markdown(f"**Overrides & notes ({len(decisions)})**")
    if decisions.empty:
        st.caption("No overrides recorded yet.")
    else:
        cols = ["ts", "planner", "unique_id", "capability_key",
                "action_type", "new_state", "note"]
        if "scenario" in decisions.columns:
            cols.append("scenario")
        show = decisions[cols].copy()
        show["capability_key"] = show["capability_key"].map(
            lambda k: CAPABILITIES.get(k, k))
        show.columns = ["When", "Planner", "Facility ID", "Capability",
                        "Action", "New status", "Note", "Scenario"][:len(cols)]
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
        f'<span class="item" style="margin-left:auto" title="Every human '
        f'correction is recorded, kept, and shown — that is the point.">'
        f'<b style="color:#D29922">{load_humility_count()}</b> times a human '
        f'corrected this app</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    render_legend()
    with st.expander("How the trust score works — no black box"):
        st.markdown(
            "Every capability in a record is treated as a **claim to verify**. "
            "The scorer is a transparent rule engine — every point is "
            "attributable to a sentence you can read below each facility.\n\n"
            "1. **Independent sources, not copies.** Self-reported narrative "
            "(capability, description, specialties) counts as *one* source, "
            "however many times it is repeated. Structured *procedures* and "
            "*equipment* are separate sources. Corroboration requires 2+ of "
            "these to independently agree.\n"
            "2. **Aspirational claims don't count.** \"Proposed ICU\", \"under "
            "construction\", \"not available\" are detected and excluded from "
            "positive evidence.\n"
            "3. **Specificity is rewarded.** An equipment line with a model "
            "number outweighs a vague sentence.\n"
            "4. **Contradictions are penalised.** A surgery-level claim with "
            "no anesthesia or operating-theatre evidence anywhere loses 0.25.\n"
            "5. **Sparse records are 'Unknown', not 'bad'.** If a record is "
            "too empty to judge, we say so instead of guessing.\n\n"
            "Humans stay in charge: any assessment can be overridden with a "
            "signed note, and the override is stored for the whole team."
        )
    st.divider()

    planner, scenario, role = render_sidebar()
    with st.sidebar:
        st.markdown(
            '<a href="https://dbc-2dfc8960-44d4.cloud.databricks.com/genie/rooms/'
            '01f182dda9201134996ca371766f40a5" target="_blank" '
            'style="color:#2F81F7;font-size:13px;text-decoration:none">'
            'Ask the data in plain English (Genie) &#8599;</a>',
            unsafe_allow_html=True,
        )

    try:
        ensure_actions_table()
    except Exception:
        st.warning("Could not prepare the decisions table — overrides and "
                   "shortlists may not save right now.")

    tab_browse, tab_deserts, tab_quality, tab_decisions = st.tabs(
        ["Find facilities", "Medical deserts", "Data quality",
         "Shortlist & decisions"])
    with tab_browse:
        try:
            render_browse_tab(planner, scenario)
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
    with tab_quality:
        try:
            render_quality_tab()
        except Exception:
            st.info("Quality-audit data isn't available yet.")
    with tab_decisions:
        render_decisions_tab()


if __name__ == "__main__":
    main()
