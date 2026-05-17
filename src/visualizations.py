"""Plotly chart builders for the SEP-1 Sepsis Hospital Quality Dashboard."""
from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── colour palette ────────────────────────────────────────────────────────────
_C = {
    "excellent": "#2ecc71",
    "moderate": "#f39c12",
    "poor": "#e74c3c",
    "no_data": "#7f8c8d",
    "ref_line": "#3498db",
    "bar": "#5b9bd5",
}

CATEGORY_COLORS: dict[str, str] = {
    "Excellent (≥80%)": _C["excellent"],
    "Moderate (50–79%)": _C["moderate"],
    "Poor (<50%)": _C["poor"],
    "No Data": _C["no_data"],
}

_TEMPLATE = "plotly_dark"
_TRANSPARENT = "rgba(0,0,0,0)"


# ── helpers ───────────────────────────────────────────────────────────────────

def _hover_text(df: pd.DataFrame) -> list[str]:
    """Build HTML hover strings for each row in *df*."""
    names = df.get("facility_name", pd.Series(["Unknown"] * len(df), index=df.index)).fillna("Unknown")
    cities = df.get("city", pd.Series([""] * len(df), index=df.index)).fillna("").astype(str)
    states = df.get("state", pd.Series([""] * len(df), index=df.index)).fillna("").astype(str)

    scores = (
        df["score"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "Not Reported")
        if "score" in df.columns
        else pd.Series(["N/A"] * len(df), index=df.index)
    )
    samples = (
        df["denominator"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")
        if "denominator" in df.columns
        else pd.Series(["N/A"] * len(df), index=df.index)
    )
    approx = (
        df["coords_approximated"].apply(lambda x: " ⚠ approx location" if x else "")
        if "coords_approximated" in df.columns
        else pd.Series([""] * len(df), index=df.index)
    )

    return (
        "<b>" + names + "</b><br>"
        + cities + ", " + states + approx + "<br>"
        + "SEP-1 Score: " + scores + "<br>"
        + "Sample Size: " + samples
    ).tolist()


# ── public chart functions ────────────────────────────────────────────────────

def create_hospital_map(
    df: pd.DataFrame,
    state_df: pd.DataFrame,
    selected_states: Optional[list[str]] = None,
    min_sample: int = 0,
) -> go.Figure:
    """Scatter geo map — one dot per hospital, colour-coded by SEP-1 tier.

    Args:
        df: Hospital-level SEP_1 DataFrame with lat/lng columns.
        state_df: State-level aggregates (not currently plotted but reserved for choropleth overlay).
        selected_states: When provided, only these states are displayed.
        min_sample: Hospitals with denominator below this value are excluded.

    Returns:
        Plotly Figure.
    """
    plot_df = df.copy()
    if selected_states:
        plot_df = plot_df[plot_df["state"].isin(selected_states)]
    if min_sample > 0 and "denominator" in plot_df.columns:
        plot_df = plot_df[plot_df["denominator"].fillna(0) >= min_sample]

    scored = plot_df[plot_df["score"].notna()]
    unscored = plot_df[plot_df["score"].isna()]

    fig = go.Figure()

    if not unscored.empty:
        fig.add_trace(go.Scattergeo(
            lat=unscored["lat"],
            lon=unscored["lng"],
            mode="markers",
            marker=dict(size=4, color=_C["no_data"], opacity=0.35),
            text=_hover_text(unscored),
            hoverinfo="text",
            name="No Data",
        ))

    for category in ["Poor (<50%)", "Moderate (50–79%)", "Excellent (≥80%)"]:
        cat_df = scored[scored.get("score_category", pd.Series(dtype=str)) == category]
        if cat_df.empty:
            continue
        fig.add_trace(go.Scattergeo(
            lat=cat_df["lat"],
            lon=cat_df["lng"],
            mode="markers",
            marker=dict(
                size=7,
                color=CATEGORY_COLORS[category],
                opacity=0.78,
                line=dict(width=0.5, color="white"),
            ),
            text=_hover_text(cat_df),
            hoverinfo="text",
            name=category,
        ))

    fig.update_layout(
        title=dict(text="Hospital SEP-1 Compliance — United States", font=dict(size=15)),
        geo=dict(
            scope="usa",
            projection_type="albers usa",
            showland=True,
            landcolor="#1a2035",
            showlakes=True,
            lakecolor="#0d1b2a",
            showframe=False,
            bgcolor=_TRANSPARENT,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=0.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=45, b=0),
        template=_TEMPLATE,
        height=520,
        paper_bgcolor=_TRANSPARENT,
        plot_bgcolor=_TRANSPARENT,
    )
    return fig


def create_state_bar_chart(state_df: pd.DataFrame, national_avg: float) -> go.Figure:
    """Horizontal bar chart of state SEP-1 averages ranked against the national mean.

    Args:
        state_df: State-level DataFrame with columns state, avg_score.
        national_avg: National average score (percentage, 0–100).

    Returns:
        Plotly Figure.
    """
    df = state_df.copy().sort_values("avg_score")

    colors = [
        _C["excellent"] if s >= 80 else (_C["moderate"] if s >= 50 else _C["poor"])
        for s in df["avg_score"]
    ]

    fig = go.Figure(go.Bar(
        x=df["avg_score"],
        y=df["state"],
        orientation="h",
        marker_color=colors,
        text=df["avg_score"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Avg SEP-1: %{x:.1f}%<extra></extra>",
    ))

    fig.add_vline(
        x=national_avg,
        line_dash="dash",
        line_color=_C["ref_line"],
        annotation_text=f"National avg: {national_avg:.1f}%",
        annotation_position="top right",
        annotation_font_color=_C["ref_line"],
    )

    chart_height = min(max(380, len(df) * 22), 1400)
    fig.update_layout(
        title=dict(text="State SEP-1 Average Compliance Rates", font=dict(size=14)),
        xaxis=dict(title="Average SEP-1 Score (%)", range=[0, 108]),
        yaxis_title=None,
        template=_TEMPLATE,
        height=chart_height,
        margin=dict(l=20, r=70, t=50, b=40),
        paper_bgcolor=_TRANSPARENT,
        plot_bgcolor=_TRANSPARENT,
        showlegend=False,
    )
    return fig


def create_score_histogram(df: pd.DataFrame) -> go.Figure:
    """Histogram of SEP-1 score distribution across all hospitals.

    Args:
        df: Hospital-level DataFrame with 'score' column.

    Returns:
        Plotly Figure.
    """
    scored = df.loc[df["score"].notna(), "score"]

    fig = px.histogram(
        scored,
        nbins=30,
        color_discrete_sequence=[_C["bar"]],
        labels={"value": "SEP-1 Score (%)", "count": "Hospitals"},
        title="Distribution of Hospital SEP-1 Scores",
    )
    fig.update_traces(hovertemplate="Score: %{x:.0f}%<br>Hospitals: %{y}<extra></extra>")

    for threshold, color, label in [
        (50, _C["poor"], "50%"),
        (80, _C["excellent"], "80%"),
    ]:
        fig.add_vline(
            x=threshold,
            line_dash="dash",
            line_color=color,
            annotation_text=label,
            annotation_position="top",
            annotation_font_color=color,
        )

    fig.update_layout(
        template=_TEMPLATE,
        height=360,
        margin=dict(l=20, r=20, t=50, b=40),
        paper_bgcolor=_TRANSPARENT,
        plot_bgcolor=_TRANSPARENT,
        showlegend=False,
        xaxis_title="SEP-1 Score (%)",
        yaxis_title="Number of Hospitals",
    )
    return fig


def create_top_bottom_table(
    df: pd.DataFrame, n: int = 10
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return the top-N and bottom-N hospitals by SEP-1 score.

    Args:
        df: Hospital-level DataFrame.
        n: Number of hospitals to include in each list.

    Returns:
        (top_df, bottom_df) formatted for Streamlit display.
    """
    scored = df[df["score"].notna()].copy()

    col_map = {
        "facility_name": "Hospital",
        "city": "City",
        "state": "State",
        "score": "SEP-1 Score (%)",
        "denominator": "Sample Size",
    }
    keep = [c for c in col_map if c in scored.columns]

    def _format(sub: pd.DataFrame) -> pd.DataFrame:
        out = sub[keep].rename(columns=col_map).reset_index(drop=True)
        out.index += 1
        if "SEP-1 Score (%)" in out.columns:
            out["SEP-1 Score (%)"] = out["SEP-1 Score (%)"].apply(lambda x: f"{x:.1f}%")
        if "Sample Size" in out.columns:
            out["Sample Size"] = out["Sample Size"].apply(
                lambda x: f"{int(x):,}" if pd.notna(x) else "N/A"
            )
        return out

    return _format(scored.nlargest(n, "score")), _format(scored.nsmallest(n, "score"))
