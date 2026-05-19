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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    [data-testid="stAppViewContainer"],
    [data-testid="stSidebar"],
    .stMarkdown, .stDataFrame, h1, h2, h3, p, label {
        font-family: 'Inter', sans-serif !important;
    }

    /* ── KPI cards ─────────────────────────────────────────── */
    .kpi-card {
        background: linear-gradient(145deg, #161c2d 0%, #1c2340 100%);
        border-radius: 14px;
        padding: 18px 20px 16px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.06);
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04);
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: var(--kpi-accent, #5b9bd5);
        border-radius: 14px 14px 0 0;
    }
    .kpi-card::after {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse at 50% -10%, rgba(255,255,255,0.05) 0%, transparent 65%);
        pointer-events: none;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.06);
    }
    .kpi-icon  { font-size: 1.25em; line-height: 1; margin-bottom: 4px; }
    .kpi-label {
        font-size: 0.63em;
        color: #7a8899;
        text-transform: uppercase;
        letter-spacing: 0.13em;
        margin-bottom: 5px;
        font-weight: 600;
    }
    .kpi-value {
        font-size: 2.1em;
        font-weight: 800;
        color: var(--kpi-accent, #f0f4f8);
        line-height: 1.05;
        font-variant-numeric: tabular-nums;
    }
    .kpi-sub { font-size: 0.66em; color: #4d5c70; margin-top: 5px; }

    /* ── Insight cards ────────────────────────────────────── */
    .insight-card {
        background: linear-gradient(145deg, #161c2d 0%, #1c2340 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-left: 3px solid var(--ins-accent, #5b9bd5);
        border-radius: 12px;
        padding: 18px 22px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.35);
        height: 100%;
    }
    .insight-eyebrow {
        font-size: 0.62em;
        color: #7a8899;
        text-transform: uppercase;
        letter-spacing: 0.13em;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .insight-val {
        font-size: 1.9em;
        font-weight: 800;
        color: var(--ins-accent, #5b9bd5);
        line-height: 1.1;
        margin-bottom: 8px;
        font-variant-numeric: tabular-nums;
    }
    .insight-body {
        font-size: 0.75em;
        color: #5a6e82;
        line-height: 1.6;
    }
    .insight-body b { color: #8a9ab0; }

    /* ── Section headers ──────────────────────────────────── */
    .sec-header {
        border-bottom: 1px solid rgba(255,255,255,0.07);
        padding-bottom: 10px;
        margin: 28px 0 14px;
    }
    .sec-header h3 {
        font-size: 1.0em;
        font-weight: 700;
        color: #c8d3e0;
        letter-spacing: 0.03em;
        margin: 0 0 2px;
    }
    .sec-header p {
        font-size: 0.75em;
        color: #4d5c70;
        margin: 0;
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


def _kpi(label: str, value: str, sub: str = "", icon: str = "", accent: str = "#5b9bd5") -> None:
    icon_html = f'<div class="kpi-icon">{icon}</div>' if icon else ""
    st.markdown(
        f"""<div class="kpi-card" style="--kpi-accent:{accent}">
              {icon_html}
              <div class="kpi-label">{label}</div>
              <div class="kpi-value">{value}</div>
              <div class="kpi-sub">{sub}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def _insight(eyebrow: str, value: str, body: str, accent: str = "#5b9bd5") -> None:
    st.markdown(
        f"""<div class="insight-card" style="--ins-accent:{accent}">
              <div class="insight-eyebrow">{eyebrow}</div>
              <div class="insight-val">{value}</div>
              <div class="insight-body">{body}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def _sec(title: str, subtitle: str = "") -> None:
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="sec-header"><h3>{title}</h3>{sub_html}</div>',
        unsafe_allow_html=True,
    )


# ── app ───────────────────────────────────────────────────────────────────────
def main() -> None:
    # ── header ────────────────────────────────────────────────────────────────
    st.title("🏥 SEP-1 Sepsis Hospital Quality Tracker")
    st.markdown(
        """
        **SEP-1** (Early Management Bundle for Severe Sepsis/Septic Shock) tracks whether hospitals
        deliver antibiotics, blood cultures, and IV fluids **within 3 hours** of sepsis onset.
        CMS incorporates SEP-1 compliance into its Value-Based Purchasing program — hospitals scoring
        below benchmarks face Medicare reimbursement penalties.
        *Source: [CMS Care Compare – Timely and Effective Care](https://data.cms.gov/provider-data/dataset/f31ab9d1-e7fb-4ea8-aff2-e00bdfa7cef3)*
        """
    )

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

        st.markdown("---")
        reporting_pct = (
            round(stats["reporting_hospitals"] / stats["total_hospitals"] * 100, 1)
            if stats["total_hospitals"] > 0
            else 0.0
        )
        st.caption(
            f"**{stats['reporting_hospitals']:,}** of **{stats['total_hospitals']:,}** hospitals "
            f"reporting ({reporting_pct}%)"
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
    _sec("National Overview")
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
    _sec("Performance Distribution")
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
    _sec("Hospital Rankings")
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
    st.markdown("---")
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
