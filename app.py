"""SEP-1 Sepsis Hospital Quality Tracker — Streamlit application entry point."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import get_advanced_stats, get_national_stats, load_sep1_data
from src.visualizations import (
    create_hospital_map,
    create_score_histogram,
    create_state_bar_chart,
    create_state_disparity_chart,
    create_top_bottom_table,
    create_volume_score_scatter,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

st.set_page_config(
    page_title="SEP-1 Sepsis Hospital Quality Tracker",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── styling ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    * { box-sizing: border-box; }
    [data-testid="stAppViewContainer"],
    [data-testid="stSidebar"],
    .stMarkdown, .stDataFrame, h1, h2, h3, p, label, div {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* ── Custom scrollbar ─── */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #2a3347; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #3a4560; }

    /* ── Sidebar ─── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0c1322 0%, #0e1528 100%) !important;
        border-right: 1px solid rgba(91,155,213,0.12) !important;
    }

    /* ── Hero ─── */
    .hero {
        background: linear-gradient(135deg, #0e1828 0%, #131e36 45%, #0f1c2e 100%);
        border: 1px solid rgba(91,155,213,0.13);
        border-radius: 20px;
        padding: 28px 32px 22px;
        margin-bottom: 6px;
        position: relative;
        overflow: hidden;
    }
    .hero::before {
        content: '';
        position: absolute;
        inset: 0;
        background:
            radial-gradient(ellipse at 15% 50%, rgba(91,155,213,0.07) 0%, transparent 55%),
            radial-gradient(ellipse at 80% 20%, rgba(46,204,113,0.05) 0%, transparent 50%);
        pointer-events: none;
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        background: rgba(46,204,113,0.09);
        border: 1px solid rgba(46,204,113,0.22);
        border-radius: 100px;
        padding: 4px 12px 4px 8px;
        font-size: 0.68em;
        color: #2ecc71;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 14px;
    }
    .hero-badge-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        background: #2ecc71;
        box-shadow: 0 0 8px rgba(46,204,113,0.65);
        animation: live-pulse 2.2s ease-in-out infinite;
        flex-shrink: 0;
    }
    @keyframes live-pulse {
        0%, 100% { opacity: 1; box-shadow: 0 0 8px rgba(46,204,113,0.65); }
        50%       { opacity: 0.45; box-shadow: 0 0 3px rgba(46,204,113,0.25); }
    }
    .hero-title {
        font-size: 2.2em;
        font-weight: 900;
        background: linear-gradient(130deg, #e8f0fa 0%, #c4d5ea 55%, #94b5d0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0 0 11px;
        line-height: 1.15;
        letter-spacing: -0.025em;
    }
    .hero-desc {
        font-size: 0.82em;
        color: #5e7288;
        line-height: 1.68;
        max-width: 780px;
        margin: 0 0 16px;
    }
    .hero-desc b { color: #8097ae; font-weight: 600; }
    .hero-desc a { color: #5b9bd5; text-decoration: none; }
    .hero-desc a:hover { text-decoration: underline; }
    .hero-tags {
        display: flex;
        gap: 7px;
        flex-wrap: wrap;
    }
    .hero-tag {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 0.67em;
        color: #445565;
        font-weight: 500;
        letter-spacing: 0.03em;
    }

    /* ── KPI cards ─── */
    .kpi-card {
        background: linear-gradient(145deg, #111827 0%, #162035 100%);
        border-radius: 16px;
        padding: 20px 20px 16px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.07);
        min-height: 128px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 28px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.05);
        transition: transform 0.22s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.22s ease;
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: var(--kpi-accent, #5b9bd5);
        border-radius: 16px 16px 0 0;
    }
    .kpi-card::after {
        content: '';
        position: absolute;
        top: -80px; left: 50%;
        transform: translateX(-50%);
        width: 180px; height: 180px;
        border-radius: 50%;
        background: var(--kpi-glow, radial-gradient(circle, rgba(91,155,213,0.09) 0%, transparent 70%));
        pointer-events: none;
    }
    .kpi-card:hover {
        transform: translateY(-4px) scale(1.01);
        box-shadow: 0 16px 44px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.08);
        border-color: rgba(255,255,255,0.11);
    }
    .kpi-icon  { font-size: 1.25em; line-height: 1; margin-bottom: 5px; }
    .kpi-label {
        font-size: 0.61em;
        color: #637585;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        margin-bottom: 5px;
        font-weight: 600;
    }
    .kpi-value {
        font-size: 2.15em;
        font-weight: 800;
        color: var(--kpi-accent, #f0f4f8);
        line-height: 1.05;
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.025em;
    }
    .kpi-sub { font-size: 0.64em; color: #394d5e; margin-top: 6px; font-weight: 500; }

    /* ── Insight cards ─── */
    .insight-card {
        background: linear-gradient(145deg, #111827 0%, #16203a 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-left: 3px solid var(--ins-accent, #5b9bd5);
        border-radius: 14px;
        padding: 20px 22px 18px;
        box-shadow: 0 4px 22px rgba(0,0,0,0.35);
        height: 100%;
        position: relative;
        overflow: hidden;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .insight-card::before {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse at 0% 60%, var(--ins-glow, rgba(91,155,213,0.05)) 0%, transparent 55%);
        pointer-events: none;
    }
    .insight-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.42);
    }
    .insight-eyebrow {
        font-size: 0.60em;
        color: #637585;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        font-weight: 600;
        margin-bottom: 9px;
    }
    .insight-val {
        font-size: 1.85em;
        font-weight: 800;
        color: var(--ins-accent, #5b9bd5);
        line-height: 1.1;
        margin-bottom: 9px;
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.025em;
    }
    .insight-body { font-size: 0.73em; color: #4a6070; line-height: 1.65; }
    .insight-body b { color: #728898; font-weight: 600; }

    /* ── Section headers ─── */
    .sec-header {
        display: flex;
        align-items: flex-start;
        gap: 13px;
        padding: 14px 0 12px;
        margin: 28px 0 15px;
        border-bottom: 1px solid rgba(255,255,255,0.055);
    }
    .sec-icon {
        width: 32px; height: 32px;
        border-radius: 9px;
        background: rgba(91,155,213,0.09);
        border: 1px solid rgba(91,155,213,0.16);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1em;
        flex-shrink: 0;
        margin-top: 2px;
    }
    .sec-body h3 {
        font-size: 1.02em;
        font-weight: 700;
        color: #cdd8e8;
        letter-spacing: 0.01em;
        margin: 0 0 3px;
    }
    .sec-body p { font-size: 0.72em; color: #42536a; margin: 0; line-height: 1.55; }

    /* ── Sidebar branding ─── */
    .sidebar-brand {
        text-align: center;
        padding: 2px 0 20px;
        border-bottom: 1px solid rgba(255,255,255,0.055);
        margin-bottom: 20px;
    }
    .sidebar-brand-icon {
        font-size: 2.8em;
        display: block;
        margin-bottom: 6px;
        filter: drop-shadow(0 0 14px rgba(46,204,113,0.32));
    }
    .sidebar-brand-name {
        font-size: 0.78em;
        font-weight: 800;
        color: #bccad8;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 2px;
    }
    .sidebar-brand-sub { font-size: 0.60em; color: #374d5e; font-weight: 500; }
    .sidebar-stat-box {
        background: rgba(91,155,213,0.055);
        border: 1px solid rgba(91,155,213,0.10);
        border-radius: 10px;
        padding: 12px 14px;
    }
    .sidebar-stat-label {
        font-size: 0.60em;
        color: #374d5e;
        text-transform: uppercase;
        letter-spacing: 0.10em;
        font-weight: 600;
        margin-bottom: 3px;
    }
    .sidebar-stat-value { font-size: 0.84em; font-weight: 700; color: #6a9fc0; }

    /* ── Fancy divider ─── */
    hr.fancy-divider {
        height: 1px !important;
        background: linear-gradient(90deg, transparent, rgba(91,155,213,0.22), rgba(46,204,113,0.16), transparent) !important;
        border: none !important;
        margin: 22px 0 18px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── data ──────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Fetching CMS Care Compare data…", ttl=86400)
def _load() -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_sep1_data()


# ── UI helpers ────────────────────────────────────────────────────────────────
def _score_color(score: float) -> str:
    if score >= 70:
        return "#2ecc71"
    if score >= 50:
        return "#f39c12"
    return "#e74c3c"


_GLOW_MAP = {
    "#2ecc71": "radial-gradient(circle, rgba(46,204,113,0.12) 0%, transparent 70%)",
    "#27ae60": "radial-gradient(circle, rgba(39,174,96,0.12) 0%, transparent 70%)",
    "#e74c3c": "radial-gradient(circle, rgba(231,76,60,0.12) 0%, transparent 70%)",
    "#f39c12": "radial-gradient(circle, rgba(243,156,18,0.11) 0%, transparent 70%)",
    "#e67e22": "radial-gradient(circle, rgba(230,126,34,0.11) 0%, transparent 70%)",
    "#5b9bd5": "radial-gradient(circle, rgba(91,155,213,0.10) 0%, transparent 70%)",
}
_INS_GLOW_MAP = {
    "#2ecc71": "rgba(46,204,113,0.06)",
    "#27ae60": "rgba(39,174,96,0.06)",
    "#e74c3c": "rgba(231,76,60,0.06)",
    "#f39c12": "rgba(243,156,18,0.06)",
    "#e67e22": "rgba(230,126,34,0.06)",
    "#5b9bd5": "rgba(91,155,213,0.06)",
}


def _hero() -> None:
    st.markdown(
        """<div class="hero">
             <div class="hero-badge">
               <span class="hero-badge-dot"></span>
               CMS Care Compare &nbsp;·&nbsp; Updated Quarterly
             </div>
             <h1 class="hero-title">SEP-1 Sepsis Quality Tracker</h1>
             <p class="hero-desc">
               <b>SEP-1</b> (Early Management Bundle for Severe Sepsis/Septic Shock) tracks whether hospitals
               deliver antibiotics, blood cultures, and IV fluids <b>within 3 hours</b> of sepsis onset.
               CMS incorporates SEP-1 compliance into its Value-Based Purchasing program — hospitals scoring
               below benchmarks face Medicare reimbursement penalties.
               &nbsp;<a href="https://data.cms.gov/provider-data/dataset/f31ab9d1-e7fb-4ea8-aff2-e00bdfa7cef3" target="_blank">Source: CMS Care Compare →</a>
             </p>
             <div class="hero-tags">
               <span class="hero-tag">⚕️ Healthcare Quality</span>
               <span class="hero-tag">🏛️ CMS Value-Based Purchasing</span>
               <span class="hero-tag">🩺 Sepsis Protocol</span>
               <span class="hero-tag">📡 Live Data</span>
             </div>
           </div>""",
        unsafe_allow_html=True,
    )


def _kpi(label: str, value: str, sub: str = "", icon: str = "", accent: str = "#5b9bd5") -> None:
    glow = _GLOW_MAP.get(accent, _GLOW_MAP["#5b9bd5"])
    icon_html = f'<div class="kpi-icon">{icon}</div>' if icon else ""
    st.markdown(
        f"""<div class="kpi-card" style="--kpi-accent:{accent};--kpi-glow:{glow}">
              {icon_html}
              <div class="kpi-label">{label}</div>
              <div class="kpi-value">{value}</div>
              <div class="kpi-sub">{sub}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def _insight(eyebrow: str, value: str, body: str, accent: str = "#5b9bd5") -> None:
    glow = _INS_GLOW_MAP.get(accent, _INS_GLOW_MAP["#5b9bd5"])
    st.markdown(
        f"""<div class="insight-card" style="--ins-accent:{accent};--ins-glow:{glow}">
              <div class="insight-eyebrow">{eyebrow}</div>
              <div class="insight-val">{value}</div>
              <div class="insight-body">{body}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def _sec(title: str, subtitle: str = "", icon: str = "") -> None:
    icon_html = f'<div class="sec-icon">{icon}</div>' if icon else ""
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="sec-header">{icon_html}<div class="sec-body"><h3>{title}</h3>{sub_html}</div></div>',
        unsafe_allow_html=True,
    )


# ── app ───────────────────────────────────────────────────────────────────────
def main() -> None:
    # ── header ────────────────────────────────────────────────────────────────
    _hero()

    # ── load data ─────────────────────────────────────────────────────────────
    try:
        hospital_df, state_df = _load()
    except Exception as exc:
        st.error(f"**Data loading failed:** {exc}")
        st.info(
            "Check your internet connection. Alternatively, download the dataset manually "
            "from the CMS link above and save it to `data/Timely_and_Effective_Care-Hospital.csv`."
        )
        st.stop()
        return

    stats = get_national_stats(hospital_df)
    adv = get_advanced_stats(hospital_df)
    all_states = sorted(hospital_df["state"].dropna().unique())

    # ── session state init ────────────────────────────────────────────────────
    if "state_filter" not in st.session_state:
        st.session_state["state_filter"] = []

    # ── sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            """<div class="sidebar-brand">
                 <span class="sidebar-brand-icon">🏥</span>
                 <div class="sidebar-brand-name">SEP-1 Tracker</div>
                 <div class="sidebar-brand-sub">CMS Care Compare Data</div>
               </div>""",
            unsafe_allow_html=True,
        )
        st.header("Filters")

        selected_states: list[str] = st.multiselect(
            "State(s)",
            options=all_states,
            key="state_filter",
            placeholder="All states — or click a state on the map",
        )

        if selected_states:
            if st.button("✕ Clear state filter", use_container_width=True):
                st.session_state["state_filter"] = []
                st.rerun()

        score_range: tuple[int, int] = st.slider(
            "SEP-1 Score Range (%)",
            min_value=0,
            max_value=100,
            value=(0, 100),
            step=1,
        )

        min_sample: int = st.slider(
            "Minimum Sample Size",
            min_value=0,
            max_value=500,
            value=0,
            step=10,
            help="Exclude hospitals with fewer sepsis cases than this threshold.",
        )

        st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:8px 0 14px"/>', unsafe_allow_html=True)
        reporting_pct = (
            round(stats["reporting_hospitals"] / stats["total_hospitals"] * 100, 1)
            if stats["total_hospitals"] > 0
            else 0.0
        )
        st.markdown(
            f"""<div class="sidebar-stat-box">
                  <div class="sidebar-stat-label">Dataset Coverage</div>
                  <div class="sidebar-stat-value">{stats['reporting_hospitals']:,} / {stats['total_hospitals']:,}</div>
                  <div class="sidebar-stat-label" style="margin-top:8px">Reporting Rate</div>
                  <div class="sidebar-stat-value">{reporting_pct}%</div>
                </div>""",
            unsafe_allow_html=True,
        )

    # ── apply filters ─────────────────────────────────────────────────────────
    filt = hospital_df.copy()
    if selected_states:
        filt = filt[filt["state"].isin(selected_states)]

    scored_mask = filt["score"].notna()
    in_range = (filt["score"] >= score_range[0]) & (filt["score"] <= score_range[1])
    filt = filt[~scored_mask | in_range]

    if min_sample > 0 and "denominator" in filt.columns:
        has_sample = filt["denominator"].notna()
        above_min = filt["denominator"] >= min_sample
        filt = filt[~has_sample | above_min]

    filt_states = state_df[state_df["state"].isin(filt["state"].unique())]

    # ── KPI row 1 ─────────────────────────────────────────────────────────────
    _sec("National Overview", icon="📊")
    r1c1, r1c2, r1c3 = st.columns(3)
    natl_color = _score_color(stats["national_avg"])
    with r1c1:
        _kpi(
            "National Average",
            f"{stats['national_avg']}%",
            "Simple avg — equal weight per hospital",
            accent=natl_color,
        )
    with r1c2:
        w_avg = adv["weighted_national_avg"]
        delta = w_avg - stats["national_avg"]
        delta_str = f"{'▲' if delta > 0 else '▼'} {abs(delta):.1f}pp vs simple avg" if delta != 0 else "same as simple avg"
        _kpi(
            "Volume-Weighted Avg",
            f"{w_avg}%",
            delta_str,
            accent=_score_color(w_avg),
        )
    with r1c3:
        _kpi(
            "Hospitals Reporting",
            f"{stats['reporting_hospitals']:,}",
            f"of {stats['total_hospitals']:,} in dataset",
            accent="#5b9bd5",
        )

    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

    # ── KPI row 2 ─────────────────────────────────────────────────────────────
    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        _kpi(
            "Top State",
            stats["best_state"],
            f"{stats['best_score']}% avg",
            accent="#2ecc71",
        )
    with r2c2:
        _kpi(
            "Lowest State",
            stats["worst_state"],
            f"{stats['worst_score']}% avg",
            accent="#e74c3c",
        )
    with r2c3:
        missed = adv["estimated_missed_bundles"]
        _kpi(
            "Est. Incomplete Bundles",
            f"~{missed:,}",
            "patient-episodes without full SEP-1",
            accent="#e67e22",
        )

    # ── map ───────────────────────────────────────────────────────────────────
    map_header_left, map_header_right = st.columns([5, 1])
    with map_header_left:
        _sec(
            "Hospital Compliance Map",
            "State shading = avg SEP-1 score · Dots = individual hospitals · Click a state to filter · Click again to reset",
            icon="🗺️",
        )
    with map_header_right:
        if selected_states:
            st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
            if st.button("Reset map", use_container_width=True):
                st.session_state["state_filter"] = []
                st.rerun()

    map_fig = create_hospital_map(filt, state_df, selected_states or None, min_sample)
    map_event = st.plotly_chart(
        map_fig,
        use_container_width=True,
        key="hospital_map",
        on_select="rerun",
    )

    # Handle map click: clicking a new state filters to it; clicking the active state clears it
    try:
        pts = (map_event.selection or {}).get("points", [])
        for pt in pts:
            clicked = pt.get("location")
            if not clicked:
                cd = pt.get("customdata")
                clicked = cd if isinstance(cd, str) else (cd[0] if isinstance(cd, (list, tuple)) and cd else None)
            if clicked and clicked in all_states:
                if st.session_state["state_filter"] == [clicked]:
                    st.session_state["state_filter"] = []
                else:
                    st.session_state["state_filter"] = [clicked]
                st.rerun()
                break
    except Exception:
        pass

    # ── performance charts ────────────────────────────────────────────────────
    _sec("Performance Distribution", icon="📈")
    chart_col, hist_col = st.columns([3, 2])
    with chart_col:
        st.plotly_chart(
            create_state_bar_chart(filt_states, stats["national_avg"]),
            use_container_width=True,
        )
    with hist_col:
        st.plotly_chart(create_score_histogram(filt), use_container_width=True)

    # ── deep dive ────────────────────────────────────────────────────────────
    _sec(
        "Deep Dive",
        "Volume vs performance · Within-state inequality",
        icon="🔬",
    )
    dd_left, dd_right = st.columns(2)
    with dd_left:
        st.plotly_chart(
            create_volume_score_scatter(filt, stats["national_avg"]),
            use_container_width=True,
        )
    with dd_right:
        st.plotly_chart(
            create_state_disparity_chart(filt),
            use_container_width=True,
        )

    # ── clinical insights ─────────────────────────────────────────────────────
    _sec(
        "Clinical Insights",
        "Non-obvious findings derived from the data",
        icon="💡",
    )
    ins1, ins2, ins3 = st.columns(3)

    # Insight 1: volume-performance correlation
    r = adv["volume_score_corr"]
    if r is None:
        corr_val_str = "N/A"
        corr_body = "Insufficient data to compute correlation."
        corr_color = "#5b9bd5"
    else:
        corr_val_str = f"r = {r:+.2f}"
        if r > 0.25:
            corr_body = (
                "Larger-volume hospitals score <b>moderately higher</b>. "
                "Seeing more sepsis cases appears to reinforce protocol adherence — "
                "a volume–outcome effect. Still, volume explains only a fraction of the variance."
            )
            corr_color = "#2ecc71"
        elif r > 0.08:
            corr_body = (
                "A <b>weak positive</b> relationship: high-volume hospitals have a slight performance edge. "
                "But most of the variance is unexplained by case volume — "
                "institutional culture and protocols matter more than throughput."
            )
            corr_color = "#27ae60"
        elif r > -0.08:
            corr_body = (
                "Volume is a <b>near-zero predictor</b> of SEP-1 compliance. "
                "A hospital seeing 20 sepsis cases and one seeing 2,000 are roughly equally likely to complete the bundle — "
                "protocol culture, not caseload, drives compliance."
            )
            corr_color = "#5b9bd5"
        else:
            corr_body = (
                "Counterintuitively, higher-volume hospitals score <b>slightly lower</b>. "
                "This may reflect more complex patient populations, resource strain at busy centers, "
                "or documentation challenges at high-throughput facilities."
            )
            corr_color = "#e67e22"

    with ins1:
        _insight(
            "Volume–Performance Correlation",
            corr_val_str,
            corr_body,
            accent=corr_color,
        )

    # Insight 2: widest within-state gap
    state_name = adv["most_disparate_state"]
    spread_pp = adv["max_intrastate_spread"]
    with ins2:
        _insight(
            "Widest Within-State Gap",
            f"{state_name}: {spread_pp:.0f} pp",
            (
                f"Within <b>{state_name}</b>, the gap between the best and worst hospital's SEP-1 scores "
                f"is <b>{spread_pp:.0f} percentage points</b>. Patients face dramatically unequal care "
                "depending on which hospital they reach — even within the same state."
            ),
            accent="#e74c3c",
        )

    # Insight 3: high-impact underperformers
    n_hi = adv["high_impact_underperformer_count"]
    with ins3:
        _insight(
            "High-Impact Underperformers",
            f"{n_hi} hospitals",
            (
                f"<b>{n_hi}</b> hospitals score below 50% while treating an above-median patient volume. "
                "These facilities combine the worst compliance with the highest exposure — "
                "the highest-priority targets for quality improvement intervention."
            ),
            accent="#e67e22",
        )

    # ── rankings ──────────────────────────────────────────────────────────────
    _sec("Hospital Rankings", icon="🏆")
    tab_top, tab_bottom, tab_method = st.tabs(
        ["🏆 Top 10", "⚠️ Bottom 10", "📋 Methodology"]
    )
    top_df, bottom_df = create_top_bottom_table(filt, n=10)

    with tab_top:
        st.success("Highest SEP-1 compliance among hospitals with reported scores.")
        st.dataframe(top_df, use_container_width=True)

    with tab_bottom:
        st.error(
            "Lowest SEP-1 compliance — these facilities may face CMS value-based purchasing penalties."
        )
        st.dataframe(bottom_df, use_container_width=True)

    with tab_method:
        st.markdown(
            """
            ### What is SEP-1?
            The **Early Management Bundle for Severe Sepsis/Septic Shock (SEP-1)** is a CMS
            quality measure that tracks whether hospitals complete **all** of the following
            within 3 hours of severe sepsis or septic shock recognition:

            | Step | Requirement |
            |------|-------------|
            | 1 | Measure lactate level |
            | 2 | Obtain blood cultures **before** antibiotics |
            | 3 | Administer broad-spectrum antibiotics |
            | 4 | Administer 30 mL/kg crystalloid fluid for hypotension or lactate ≥4 mmol/L |

            ### Score Interpretation
            - **≥80%** — Excellent compliance; hospital consistently meets the bundle
            - **50–79%** — Moderate; room for improvement
            - **<50%** — Poor; significant protocol gaps; heightened CMS scrutiny

            ### Volume-Weighted Average
            Unlike the simple national average (equal weight per hospital), the **volume-weighted
            average** weights each hospital by its denominator — the number of eligible sepsis
            cases. This answers: *"If you were a random sepsis patient, what is the probability
            your hospital completes the full bundle?"*

            ### Estimated Incomplete Bundles
            Computed as **Σ (denominator × (1 − score / 100))** across all reporting hospitals.
            This converts abstract compliance percentages into an estimated count of patient-episodes
            where the complete bundle was not delivered.

            ### Data Limitations
            - Hospitals with **fewer than 25 eligible cases** per quarter may have suppressed
              scores to protect statistical reliability.
            - Scores represent **all-or-nothing** bundle compliance: partial completion counts
              as a failure.
            - State averages weight each reporting hospital equally (not by volume).
            - Hospital map coordinates: when exact lat/lng are unavailable, hospitals are
              plotted near their state centroid with random jitter (⚠ in hover).

            ### Source
            Centers for Medicare & Medicaid Services (CMS) — *Care Compare:
            Timely and Effective Care* dataset, updated quarterly.
            """
        )

    # ── export ────────────────────────────────────────────────────────────────
    st.markdown('<hr class="fancy-divider"/>', unsafe_allow_html=True)
    export_cols = [
        c for c in
        ["facility_id", "facility_name", "city", "state", "zip_code",
         "score", "denominator", "score_category"]
        if c in filt.columns
    ]
    csv_data = filt[filt["score"].notna()][export_cols].to_csv(index=False)
    st.download_button(
        "⬇️ Download Filtered Data (CSV)",
        data=csv_data,
        file_name="sep1_filtered_hospitals.csv",
        mime="text/csv",
    )

    st.caption(
        "Data: CMS Care Compare (Timely and Effective Care). "
        "SEP-1 scores are the percentage of eligible patients receiving the complete bundle. "
        "Hospitals with <25 cases may have suppressed scores."
    )


main()
