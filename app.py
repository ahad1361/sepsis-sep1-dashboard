"""SEP-1 Sepsis Hospital Quality Tracker — Streamlit application entry point."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import get_national_stats, load_sep1_data
from src.visualizations import (
    create_hospital_map,
    create_score_histogram,
    create_state_bar_chart,
    create_top_bottom_table,
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
    .kpi-card {
        background: #1e2329;
        border-radius: 10px;
        padding: 20px 24px;
        text-align: center;
        border: 1px solid #2d3748;
        height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .kpi-label { font-size: 0.75em; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 6px; }
    .kpi-value { font-size: 2.1em; font-weight: 700; color: #f7fafc; line-height: 1.1; }
    .kpi-sub   { font-size: 0.73em; color: #718096; margin-top: 4px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── data ──────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Fetching CMS Care Compare data…")
def _load() -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_sep1_data()


def _kpi(label: str, value: str, sub: str = "") -> None:
    st.markdown(
        f"""<div class="kpi-card">
              <div class="kpi-label">{label}</div>
              <div class="kpi-value">{value}</div>
              <div class="kpi-sub">{sub}</div>
            </div>""",
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

    # ── sidebar filters ───────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Filters")

        all_states = sorted(hospital_df["state"].dropna().unique())
        selected_states: list[str] = st.multiselect(
            "State(s)",
            options=all_states,
            default=[],
            placeholder="All states",
        )

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
        st.caption(
            f"**{stats['reporting_hospitals']:,}** hospitals reporting  \n"
            f"**{stats['total_hospitals']:,}** total in dataset"
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

    # ── KPI cards ─────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        _kpi("National Average", f"{stats['national_avg']}%", "SEP-1 compliance")
    with k2:
        _kpi(
            "Hospitals Reporting",
            f"{stats['reporting_hospitals']:,}",
            f"of {stats['total_hospitals']:,} total",
        )
    with k3:
        _kpi("Top State", stats["best_state"], f"{stats['best_score']}% avg")
    with k4:
        _kpi("Lowest State", stats["worst_state"], f"{stats['worst_score']}% avg")

    st.markdown("---")

    # ── map ───────────────────────────────────────────────────────────────────
    st.subheader("Hospital Compliance Map")
    st.caption(
        "Each dot represents one hospital. "
        "🟢 ≥80% (Excellent) · 🟡 50–79% (Moderate) · 🔴 <50% (Poor) · ⚫ Not Reported. "
        "Hospitals without exact coordinates are plotted near their state centroid."
    )
    st.plotly_chart(
        create_hospital_map(filt, filt_states, selected_states or None, min_sample),
        use_container_width=True,
    )

    # ── charts ────────────────────────────────────────────────────────────────
    chart_col, hist_col = st.columns([3, 2])
    with chart_col:
        st.plotly_chart(
            create_state_bar_chart(filt_states, stats["national_avg"]),
            use_container_width=True,
        )
    with hist_col:
        st.plotly_chart(create_score_histogram(filt), use_container_width=True)

    # ── rankings ──────────────────────────────────────────────────────────────
    st.subheader("Hospital Rankings")
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

            ### Data Limitations
            - Hospitals with **fewer than 25 eligible cases** per quarter may have suppressed
              scores ("Not Available") to protect statistical reliability.
            - Scores represent **all-or-nothing** bundle compliance: partial completion counts
              as a failure.
            - State averages weight each reporting hospital equally (not by volume).
            - Hospital map coordinates: when exact lat/lng are unavailable, hospitals are
              plotted near their state centroid with random jitter (indicated by ⚠ in hover).

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
